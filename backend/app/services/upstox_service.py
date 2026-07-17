from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode
from uuid import UUID

import requests

from app.core.config import settings
from app.core.idempotency import generate_trade_idempotency_hash
from app.core.oauth_state import sign_state, verify_state
from app.models.broker_connection import BrokerConnection
from app.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
)
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.csv_import import CsvImportResponse
from app.services.trade_service import TradeService

# Per Upstox's public docs (upstox.com/developer/api-documentation/) --
# unlike Kite Connect, Upstox's authorize dialog natively supports a `state`
# query param, so no redirect_params workaround is needed here.
_UPSTOX_AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
_UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"
_UPSTOX_TRADES_URL = "https://api.upstox.com/v2/order/trades/get-trades-for-day"
_TIMESTAMP_FORMAT = "%d-%b-%Y %H:%M:%S"  # e.g. "03-Aug-2017 15:03:42"


class UpstoxService:
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

    def _redirect_uri(self) -> str:
        # Must exactly match the Redirect URI registered on the user's own
        # Upstox app -- same value shown to the user in the frontend setup
        # instructions (built from NEXT_PUBLIC_API_URL there).
        return f"{settings.BACKEND_URL}/brokers/upstox/callback"

    def get_login_url(
        self,
        user_id: UUID,
    ) -> str:
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="upstox",
        )
        if not connection or not connection.api_key:
            raise ValueError(
                "No Upstox API key on file. Submit your Upstox app's "
                "client_id and client_secret via POST /brokers/upstox/credentials "
                "before connecting."
            )

        state = sign_state(user_id)
        params = {
            "client_id": connection.api_key,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "state": state,
        }
        return f"{_UPSTOX_AUTH_URL}?{urlencode(params)}"

    def handle_callback(
        self,
        state: str,
        code: str,
    ) -> BrokerConnection:
        try:
            user_id = verify_state(state)
        except ValueError as e:
            raise ValueError(f"Invalid or expired login session: {e}")

        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="upstox",
        )
        if not connection or not connection.api_key or not connection.api_secret_kms_id:
            raise ValueError(
                "No Upstox credentials found. Submit your client_id/client_secret "
                "via POST /brokers/upstox/credentials, then call "
                "GET /brokers/upstox/login."
            )

        api_secret = self.vault_repository.get_secret(
            secret_id=UUID(connection.api_secret_kms_id),
        )
        if not api_secret:
            raise ValueError(
                "Upstox API secret not found in Vault. Please re-submit "
                "your credentials."
            )

        try:
            response = requests.post(
                _UPSTOX_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": connection.api_key,
                    "client_secret": api_secret,
                    "redirect_uri": self._redirect_uri(),
                    "grant_type": "authorization_code",
                },
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15,
            )
            response.raise_for_status()
            access_token = response.json()["access_token"]
        except Exception as e:
            raise ValueError(
                f"Failed to exchange authorization code: {str(e)}"
            )

        vault_name = f"upstox_token_{user_id}"
        if connection.access_token_kms_id:
            self.vault_repository.update_secret(
                secret_id=UUID(connection.access_token_kms_id),
                secret_value=access_token,
                name=vault_name,
                description="Upstox daily access token",
            )
        else:
            secret_id = self.vault_repository.create_secret(
                secret_value=access_token,
                name=vault_name,
                description="Upstox daily access token",
            )
            self.broker_connection_repository.update_access_token_kms_id(
                connection=connection,
                access_token_kms_id=str(secret_id),
            )

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
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="upstox",
        )
        if not connection or not connection.access_token_kms_id:
            raise ValueError(
                "No Upstox access token found. "
                "Please log in via GET /brokers/upstox/login."
            )
        token = self.vault_repository.get_secret(
            secret_id=UUID(connection.access_token_kms_id),
        )
        if not token:
            raise ValueError(
                "Upstox access token not found in Vault. "
                "Please log in again via GET /brokers/upstox/login."
            )
        return token

    def sync_today_trades(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
    ) -> CsvImportResponse:
        access_token = self.get_access_token(user_id=user_id)

        try:
            response = requests.get(
                _UPSTOX_TRADES_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=15,
            )
            response.raise_for_status()
            trades = response.json().get("data", [])
        except Exception as e:
            raise ValueError(
                f"Failed to fetch trades from Upstox: {str(e)}"
            )

        imported = 0
        skipped = 0
        errors = []

        for trade in trades:
            try:
                # `exchange` is the bare exchange ("NSE"/"BSE") on both
                # equity and F&O trades -- instrument_token carries the
                # actual segment ("NSE_FO|...", "BSE_FO|...") per Upstox's
                # instrument-key docs, so that's what F&O detection uses.
                instrument_token = trade.get("instrument_token", "")
                if instrument_token.startswith(("NSE_FO", "BSE_FO")):
                    instrument_type = "fno"
                else:
                    instrument_type = "equity"

                symbol = trade.get("trading_symbol") or trade["tradingsymbol"]
                instrument = self.instrument_repository.get_or_create(
                    symbol=symbol,
                    instrument_type=instrument_type,
                    name=symbol,
                    isin=None,
                )

                try:
                    execution_time = datetime.strptime(
                        trade["exchange_timestamp"],
                        _TIMESTAMP_FORMAT,
                    )
                except (ValueError, TypeError, KeyError):
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
