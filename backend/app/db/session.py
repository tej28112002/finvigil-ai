from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# pool_size=20/max_overflow=20 (raised from an earlier too-small 5/10) was
# itself wrong in the opposite direction: this project's Supabase database
# runs in Session Pooler mode, which enforces a HARD SERVER-SIDE cap of 15
# concurrent connections regardless of what this app requests — confirmed
# directly via a real, reproduced failure:
#   psycopg2.OperationalError: ... FATAL: (EMAXCONNSESSION) max clients
#   reached in session mode - max clients are limited to pool_size: 15
# Configuring for 40 (20+20) meant any burst past 15 concurrent connections
# (the dashboard alone fires 9 parallel calls; a second tab or a couple of
# prefetched AY-tab requests trivially pushes past 15) threw this
# OperationalError from inside get_db()'s connection checkout — uncaught
# anywhere, it surfaced to the frontend as an unexplained 500 and, in one
# observed case, was severe enough to crash the whole uvicorn worker.
# Supabase's 15-connection cap is PROJECT-WIDE, not per-process — this
# app's own pool_size is only a per-process ceiling, so it has to leave
# real headroom for whatever ELSE might be drawing from the same shared
# budget at any moment (a second local dev process, a psql session, a
# migration script, later a Celery worker). A direct 20-thread concurrent
# stress test against pool_size=10+max_overflow=2 (12) still produced real
# OperationalErrors, because a second process (this app's own already-running
# server) was concurrently holding some of Supabase's 15 slots at the same
# time — 12 here plus a handful already held elsewhere exceeded 15.
# pool_size=5 + max_overflow=1 caps this app at 6, leaving real headroom
# under the 15 ceiling — a synthetic 20-thread simultaneous-connect test
# still produced occasional OperationalErrors even at pool_size=6+overflow=2
# (8), because Supabase's pooler doesn't reclaim a closed client's slot
# instantly, so external/leftover connection pressure can transiently eat
# into the shared 15-connection budget independent of this app's own
# configured ceiling. Real browser traffic (max ~9 near-simultaneous calls
# from the dashboard's Promise.all, naturally staggered by network/render
# timing) is far gentler than that synthetic test; pool_timeout (default
# 30s) makes any request that can't get a connection immediately wait for
# one rather than fail. If real traffic needs more concurrent DB work than
# 6, the fix is Supabase's Transaction Pooler (much higher effective limit,
# different connection semantics) or a paid tier's higher cap — NOT raising
# this past what Session Pooler actually allows.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=1,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
