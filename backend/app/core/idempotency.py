import hashlib
from uuid import UUID


def generate_trade_idempotency_hash(
    broker_connection_id: UUID,
    broker_trade_id: str,
) -> str:
    """
    Generate the deduplication hash for a trade.
    MUST be used by every trade insertion path so the
    same trade always produces the same hash.
    The ':' separator prevents ID-boundary collisions.
    """
    raw = f"{broker_connection_id}:{broker_trade_id}"
    return hashlib.sha256(raw.encode()).hexdigest()
