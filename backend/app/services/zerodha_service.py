from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote
from uuid import UUID

from kiteconnect import KiteConnect
from kiteconnect.exceptions import NetworkException, TokenException

from app.core.idempotency import generate_trade_idempotency_hash
from app.core.oauth_state import sign_state, verify_state
from app.models.broker_connection import BrokerConnection
from app.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
)
from app.repositories.holding_lot_repository import HoldingLotRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.csv_import import CsvImportResponse
from app.services.trade_service import TradeService

# Kite Connect's own login_url() (pykiteconnect) doesn't expose a way to
# pass redirect_params, so the URL is built manually here. Endpoint + version
# per Zerodha's public docs (kite.trade/docs/connect/v3/user/), not an
# internal SDK attribute.
_KITE_LOGIN_URL = "https://kite.zerodha.com/connect/login"
_KITE_API_VERSION = "3"


class ZerodhaService:
    def __init__(
        self,
        broker_connection_repository: BrokerConnectionRepository,
        vault_repository: VaultRepository,
        trade_service: TradeService,
        instrument_repository: InstrumentRepository,
        holding_lot_repository: HoldingLotRepository | None = None,
    ):
        self.broker_connection_repository = broker_connection_repository
        self.vault_repository = vault_repository
        self.trade_service = trade_service
        self.instrument_repository = instrument_repository
        self.holding_lot_repository = holding_lot_repository

    def get_login_url(
        self,
        user_id: UUID,
    ) -> str:
        """
        BYOK: uses the user's own Kite Connect api_key, submitted beforehand
        via POST /brokers/zerodha/credentials. Does NOT auto-create a
        broker_connection -- one must already exist with credentials on it.

        Zerodha's redirect back to our callback can't carry an Authorization
        header, so instead of trusting a bare user_id query param (the prior
        approach, documented tech debt), a signed state token is embedded via
        Kite's redirect_params mechanism and verified in handle_callback().
        """
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection or not connection.api_key:
            raise ValueError(
                "No Zerodha API key on file. Submit your Kite Connect "
                "api_key and api_secret via POST /brokers/zerodha/credentials "
                "before connecting."
            )

        state = sign_state(user_id)
        redirect_params = quote(f"state={state}", safe="")
        return (
            f"{_KITE_LOGIN_URL}?v={_KITE_API_VERSION}"
            f"&api_key={connection.api_key}"
            f"&redirect_params={redirect_params}"
        )

    def handle_callback(
        self,
        state: str,
        request_token: str,
    ) -> BrokerConnection:
        try:
            user_id = verify_state(state)
        except ValueError as e:
            raise ValueError(f"Invalid or expired login session: {e}")

        # Step 1 — Fetch existing broker connection (must already have
        # credentials submitted -- see get_login_url).
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection or not connection.api_key or not connection.api_secret_kms_id:
            raise ValueError(
                "No Zerodha credentials found. Submit your api_key/api_secret "
                "via POST /brokers/zerodha/credentials, then call "
                "GET /brokers/zerodha/login."
            )

        api_secret = self.vault_repository.get_secret(
            secret_id=UUID(connection.api_secret_kms_id),
        )
        if not api_secret:
            raise ValueError(
                "Zerodha API secret not found in Vault. Please re-submit "
                "your credentials."
            )

        # Step 2 — Exchange request_token for access_token
        try:
            kite = KiteConnect(api_key=connection.api_key)
            data = kite.generate_session(
                request_token,
                api_secret=api_secret,
            )
            access_token = data["access_token"]
        except Exception as e:
            raise ValueError(
                f"Failed to exchange request token: {str(e)}"
            )

        # Step 3 — Store access token in Vault (create or update)
        vault_name = f"zerodha_token_{user_id}"
        if connection.access_token_kms_id:
            self.vault_repository.update_secret(
                secret_id=UUID(connection.access_token_kms_id),
                secret_value=access_token,
                name=vault_name,
                description="Zerodha daily access token",
            )
        else:
            secret_id = self.vault_repository.create_secret(
                secret_value=access_token,
                name=vault_name,
                description="Zerodha daily access token",
            )
            self.broker_connection_repository.update_access_token_kms_id(
                connection=connection,
                access_token_kms_id=str(secret_id),
            )

        # Step 4 — Ensure status is active and return
        if connection.status != "active":
            self.broker_connection_repository.update_status(
                connection=connection,
                status="active",
            )
        return connection

    def get_access_token(
        self,
        user_id: UUID,
    ) -> str:
        """
        Retrieve the stored access token for a user.
        Used by future sync methods that call Kite API.
        """
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection or not connection.access_token_kms_id:
            raise ValueError(
                "No Zerodha access token found. "
                "Please log in via GET /brokers/zerodha/login."
            )
        token = self.vault_repository.get_secret(
            secret_id=UUID(connection.access_token_kms_id),
        )
        if not token:
            raise ValueError(
                "Zerodha access token not found in Vault. "
                "Please log in again via GET /brokers/zerodha/login."
            )
        return token

    def _get_kite_client(self, user_id: UUID) -> KiteConnect:
        """
        Build an authenticated KiteConnect client for this user.
        Retrieves the api_key from the connection and the access token
        from Vault.
        """
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection or not connection.api_key:
            raise ValueError(
                "No Zerodha API key on file. Submit your credentials via "
                "POST /brokers/zerodha/credentials."
            )
        access_token = self.get_access_token(user_id=user_id)
        kite = KiteConnect(api_key=connection.api_key)
        kite.set_access_token(access_token)
        return kite

    def sync_today_trades(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
    ) -> CsvImportResponse:
        """
        Fetch today's executed trades from Zerodha and route
        them through the trade pipeline.
        Reuses the same idempotency hash as CSV import, so
        OAuth-synced trades and CSV-imported trades automatically
        deduplicate against each other.
        """
        kite = self._get_kite_client(user_id=user_id)

        try:
            trades = kite.trades()
        except Exception as e:
            raise ValueError(
                f"Failed to fetch trades from Zerodha: {str(e)}"
            )

        imported = 0
        skipped = 0
        errors = []

        for trade in trades:
            try:
                exchange = trade.get("exchange", "NSE")
                if exchange in ("NFO", "BFO"):
                    instrument_type = "fno"
                else:
                    instrument_type = "equity"

                # A duplicate idempotency_hash (re-syncing a trade already
                # imported) raises IntegrityError on flush -- without a
                # savepoint boundary, that leaves the whole request's shared
                # session in an aborted-transaction state, so every DB call
                # after it (later trades in this loop, sync_holdings'
                # follow-on trades, the dashboard projection update, even
                # get_db()'s own final commit) fails too, turning one
                # already-imported trade into a full 500 for the entire
                # sync. The savepoint scopes the rollback to just this trade.
                with self.instrument_repository.db.begin_nested():
                    instrument = self.instrument_repository.get_or_create(
                        symbol=trade["tradingsymbol"],
                        instrument_type=instrument_type,
                        name=trade["tradingsymbol"],
                        isin=None,
                    )

                    try:
                        execution_time = datetime.strptime(
                            trade["fill_timestamp"],
                            "%Y-%m-%d %H:%M:%S",
                        )
                    except (ValueError, TypeError):
                        execution_time = datetime.now()

                    idempotency_hash = generate_trade_idempotency_hash(
                        broker_connection_id=broker_connection_id,
                        broker_trade_id=str(trade["trade_id"]),
                    )

                    trade_type = trade["transaction_type"].lower()
                    quantity = Decimal(str(trade["quantity"]))
                    price = Decimal(str(trade["average_price"]))

                    if instrument_type == "fno":
                        if trade_type == "sell":
                            self.trade_service.process_fno_sell_trade(
                                user_id=user_id,
                                instrument_id=instrument.id,
                                broker_connection_id=broker_connection_id,
                                broker_trade_id=str(trade["trade_id"]),
                                quantity=quantity,
                                price=price,
                                execution_time=execution_time,
                                idempotency_hash=idempotency_hash,
                            )
                        else:
                            self.trade_service.process_fno_buy_trade(
                                user_id=user_id,
                                instrument_id=instrument.id,
                                broker_connection_id=broker_connection_id,
                                broker_trade_id=str(trade["trade_id"]),
                                quantity=quantity,
                                price=price,
                                execution_time=execution_time,
                                idempotency_hash=idempotency_hash,
                            )
                    else:
                        self.trade_service.process_trade(
                            trade_type=trade_type,
                            user_id=user_id,
                            instrument_id=instrument.id,
                            broker_connection_id=broker_connection_id,
                            broker_trade_id=str(trade["trade_id"]),
                            quantity=quantity,
                            price=price,
                            execution_time=execution_time,
                            idempotency_hash=idempotency_hash,
                        )
                imported += 1

            except Exception as e:
                error_msg = str(e)
                if (
                    "duplicate key" in error_msg.lower()
                    or "uniqueviolation" in error_msg.lower()
                    or "idempotency_hash" in error_msg.lower()
                ):
                    skipped += 1
                else:
                    errors.append(
                        f"Trade {trade.get('trade_id', '?')}: {error_msg}"
                    )

        return CsvImportResponse(
            total_rows=len(trades),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

    def sync_holdings(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
    ) -> dict:
        """
        Fetches the user's actual portfolio holdings via Kite's
        /portfolio/holdings and reflects them as HoldingLots. This is the
        piece sync_today_trades() was missing: Kite's /trades endpoint
        only returns orders placed TODAY, so an account with pre-existing
        holdings (bought before the app was ever connected) legitimately
        returns 0 trades there -- which is why "Sync now" was showing
        Rs 0.00 holdings even for a correctly-connected account.

        Holdings are a consolidated snapshot (one row per symbol, single
        average_price, no per-lot buy date), so each is treated as one
        lot. holding_lots.source_trade_id is NOT NULL, so a lot can't be
        inserted directly -- a synthetic buy Trade is created via the same
        trade_service.process_buy_trade() path used everywhere else,
        keyed by a stable per-symbol idempotency hash so re-syncing
        updates the existing lot's quantity instead of duplicating it.

        Returns a result dict rather than raising, so the router can
        surface a specific, actionable error_code to the frontend instead
        of a generic 400.
        """
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection or not connection.api_key or not connection.access_token_kms_id:
            return {
                "success": False,
                "error": (
                    "API key or access token missing. "
                    "Please reconnect your Zerodha account."
                ),
                "error_code": "MISSING_CREDENTIALS",
            }

        try:
            kite = self._get_kite_client(user_id=user_id)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "MISSING_CREDENTIALS",
            }

        try:
            holdings = kite.holdings()
        except TokenException:
            return {
                "success": False,
                "error": (
                    "Access token expired. Please reconnect your Zerodha "
                    "account to get a fresh token."
                ),
                "error_code": "TOKEN_EXPIRED",
            }
        except NetworkException as e:
            return {
                "success": False,
                "error": f"Could not reach Zerodha: {e}",
                "error_code": "NETWORK_ERROR",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Zerodha API error: {e}",
                "error_code": "API_ERROR",
            }

        synced_count = 0
        errors: list[str] = []

        for holding in holdings:
            symbol = holding.get("tradingsymbol", "")
            try:
                isin = holding.get("isin") or None
                quantity = Decimal(str(holding.get("quantity", 0)))
                avg_price = Decimal(str(holding.get("average_price", 0)))

                if quantity <= 0 or avg_price <= 0:
                    continue

                # Savepoint-scoped: a write failure for one holding (e.g. a
                # stale idempotency-hash collision on resync) must not abort
                # the shared request-level transaction -- see the matching
                # comment in sync_today_trades for why that would otherwise
                # take down every holding after it, plus the trades sync and
                # dashboard update that follow in the same request.
                with self.instrument_repository.db.begin_nested():
                    instrument = self.instrument_repository.get_or_create(
                        symbol=symbol,
                        instrument_type="equity",
                        name=symbol,
                        isin=isin,
                    )

                    existing_lots = self.holding_lot_repository.get_open_lots(
                        user_id=user_id,
                        instrument_id=instrument.id,
                    )
                    if existing_lots:
                        lot = existing_lots[0]
                        self.holding_lot_repository.update_remaining_quantity(
                            lot=lot,
                            remaining_quantity=quantity,
                            status="open",
                        )
                    else:
                        broker_trade_id = f"holding:{symbol}"
                        idempotency_hash = generate_trade_idempotency_hash(
                            broker_connection_id=broker_connection_id,
                            broker_trade_id=broker_trade_id,
                        )
                        self.trade_service.process_buy_trade(
                            user_id=user_id,
                            instrument_id=instrument.id,
                            broker_connection_id=broker_connection_id,
                            broker_trade_id=broker_trade_id,
                            quantity=quantity,
                            price=avg_price,
                            execution_time=datetime.now(timezone.utc),
                            idempotency_hash=idempotency_hash,
                        )
                synced_count += 1
            except Exception as e:
                errors.append(f"{symbol or '?'}: {e}")

        if connection.status != "active":
            self.broker_connection_repository.update_status(
                connection=connection,
                status="active",
            )

        return {
            "success": True,
            "holdings_synced": synced_count,
            "errors": errors[:5],
        }

    def sync_broker(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
    ) -> dict:
        """
        Full "Sync now" action: holdings snapshot (sync_holdings) plus
        today's executed trades (sync_today_trades). If holdings fails
        (bad/expired credentials), that error is returned immediately --
        no point attempting trades with the same broken credentials. If
        trades fails after holdings already succeeded, that's folded into
        the errors list rather than failing the whole sync.
        """
        holdings_result = self.sync_holdings(
            user_id=user_id,
            broker_connection_id=broker_connection_id,
        )
        if not holdings_result["success"]:
            return holdings_result

        trades_imported = 0
        trades_skipped = 0
        errors = list(holdings_result.get("errors", []))
        try:
            trades_result = self.sync_today_trades(
                user_id=user_id,
                broker_connection_id=broker_connection_id,
            )
            trades_imported = trades_result.imported
            trades_skipped = trades_result.skipped
            errors.extend(trades_result.errors)
        except ValueError as e:
            errors.append(f"Today's trades: {e}")

        holdings_synced = holdings_result["holdings_synced"]
        return {
            "success": True,
            "trades_imported": trades_imported,
            "trades_skipped": trades_skipped,
            "holdings_synced": holdings_synced,
            "errors": errors[:5],
            "message": (
                f"Synced {holdings_synced} holdings and {trades_imported} "
                f"new trades from Zerodha."
            ),
        }
