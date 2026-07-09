from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Default pool_size=5/max_overflow=10 was too small: a single dashboard
# load fires 9 parallel DB-touching requests (Promise.all across endpoints),
# so any second concurrent page/tab pushed requests into a queue waiting up
# to pool_timeout (30s default) for a free connection — the actual cause of
# multi-second/10s+ page loads observed in dev, not per-query latency.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=20,
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
