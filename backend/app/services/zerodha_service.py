from datetime import datetime
from decimal import Decimal
from uuid import UUID

from kiteconnect import KiteConnect

from app.core.config import settings
from app.core.idempotency import generate_trade_idempotency_hash
from app.models.broker_connection import BrokerConnection
from app.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
)
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.csv_import import CsvImportResponse
from app.services.trade_service import TradeService


class ZerodhaService:
    def __init__(
        self,
        broker_connection_repository: BrokerConnectionRepository,
        vault_repository: VaultRepository,
        trade_service: TradeService,
        instrument_repository: InstrumentRepository,
    ):
        self.broker_connection_repository = broker_connection_repository
        self.vault_repository = vault_repository
        self.trade_service = trade_service
        self.instrument_repository = instrument_repository

    def get_login_url(
        self,
        user_id: UUID,
    ) -> str:
        # Step 1 — Ensure broker_connection exists
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection:
            connection = self.broker_connection_repository.create_connection(
                user_id=user_id,
                broker_name="zerodha",
                credentials_kms_id=None,
            )

        # Step 2 — Generate and return login URL
        kite = KiteConnect(api_key=settings.ZERODHA_API_KEY)
        return kite.login_url()

    def handle_callback(
        self,
        user_id: UUID,
        request_token: str,
    ) -> BrokerConnection:
        # Step 1 — Fetch existing broker connection
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="zerodha",
        )
        if not connection:
            raise ValueError(
                "No Zerodha connection found. "
                "Call GET /brokers/zerodha/login first."
            )

        # Step 2 — Exchange request_token for access_token
        try:
            kite = KiteConnect(api_key=settings.ZERODHA_API_KEY)
            data = kite.generate_session(
                request_token,
                api_secret=settings.ZERODHA_API_SECRET,
            )
            access_token = data["access_token"]
        except Exception as e:
            raise ValueError(
                f"Failed to exchange request token: {str(e)}"
            )

        # Step 3 — Store in Vault (create or update)
        vault_name = f"zerodha_token_{user_id}"
        if connection.credentials_kms_id:
            self.vault_repository.update_secret(
                secret_id=UUID(connection.credentials_kms_id),
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
            self.broker_connection_repository.update_credentials_kms_id(
                connection=connection,
                credentials_kms_id=str(secret_id),
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
        if not connection or not connection.credentials_kms_id:
            raise ValueError(
                "No Zerodha access token found. "
                "Please log in via GET /brokers/zerodha/login."
            )
        token = self.vault_repository.get_secret(
            secret_id=UUID(connection.credentials_kms_id),
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
        Retrieves the access token from Vault and sets it.
        """
        access_token = self.get_access_token(user_id=user_id)
        kite = KiteConnect(api_key=settings.ZERODHA_API_KEY)
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
