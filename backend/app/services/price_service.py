from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from kiteconnect import KiteConnect

from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.vault_repository import VaultRepository

# Module-level in-memory cache shared across all requests.
# Key: (user_id_str, symbol) → {"prices": {...}, "fetched_at": datetime}
# Deferred to DB-backed storage in Phase 8 (Replay).
_cache: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


class PriceService:
    def __init__(
        self,
        broker_connection_repository: BrokerConnectionRepository,
        vault_repository: VaultRepository,
    ):
        self.broker_connection_repository = broker_connection_repository
        self.vault_repository = vault_repository

    def _get_connection_and_access_token(
        self, user_id: UUID
    ) -> tuple[str, str] | None:
        """
        Retrieve the user's own Zerodha api_key plus their access token from
        Vault. Returns None (silently) if no active connection, no api_key
        (BYOK credentials never submitted), or no token stored.
        """
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection or not connection.api_key or not connection.access_token_kms_id:
            return None
        if connection.status != "active":
            return None
        token = self.vault_repository.get_secret(
            secret_id=UUID(connection.access_token_kms_id),
        )
        if not token:
            return None
        return connection.api_key, token

    def get_prices(
        self,
        user_id: UUID,
        symbols: list[str],
    ) -> dict[str, dict]:
        """
        Return live prices for a list of instrument symbols.

        Result shape per symbol:
            {"last_price": Decimal, "prev_close": Decimal}

        "last_price" = current LTP from kite.quote().
        "prev_close" = ohlc["close"] from kite.quote() = previous day's close.
            day_pnl   = (last_price - prev_close) × quantity_remaining
            unrealized = (last_price - buy_price)  × quantity_remaining

        Falls back silently (returns {}) if:
        - No symbols requested
        - No active Zerodha connection for this user
        - Zerodha API call fails for any reason
        Caller (dashboard_service) falls back to buy_price when symbol absent.
        """
        if not symbols:
            return {}

        now = datetime.now(timezone.utc)
        result: dict[str, dict] = {}
        stale_symbols: list[str] = []

        # Step 1 — serve fresh entries from cache
        for symbol in symbols:
            cache_key = (str(user_id), symbol)
            entry = _cache.get(cache_key)
            if entry and (now - entry["fetched_at"]).total_seconds() < _CACHE_TTL_SECONDS:
                result[symbol] = entry["prices"]
            else:
                stale_symbols.append(symbol)

        if not stale_symbols:
            return result

        # Step 2 — get the user's own Zerodha api_key + access token;
        # silent fallback if unavailable
        try:
            credentials = self._get_connection_and_access_token(user_id=user_id)
        except Exception:
            return result

        if not credentials:
            return result
        api_key, access_token = credentials

        # Step 3 — ONE batched kite.quote() call for all stale symbols
        instrument_keys = [f"NSE:{symbol}" for symbol in stale_symbols]

        try:
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            quotes = kite.quote(instrument_keys)
        except Exception:
            return result

        # Step 4 — parse response; Decimal(str(...)) always, never float
        fetched_at = datetime.now(timezone.utc)
        for symbol in stale_symbols:
            key = f"NSE:{symbol}"
            if key not in quotes:
                continue
            q = quotes[key]
            prices = {
                "last_price": Decimal(str(q["last_price"])),
                "prev_close": Decimal(str(q["ohlc"]["close"])),
            }
            _cache[(str(user_id), symbol)] = {
                "prices": prices,
                "fetched_at": fetched_at,
            }
            result[symbol] = prices

        return result
