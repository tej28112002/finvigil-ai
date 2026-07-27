from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import pyotp
import requests
from sqlalchemy.exc import IntegrityError

from app.core.idempotency import generate_trade_idempotency_hash
from app.models.broker_connection import BrokerConnection
from app.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
)
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.vault_repository import VaultRepository
from app.schemas.csv_import import CsvImportResponse
from app.services.trade_service import TradeService

# Per Groww's public cURL docs (groww.in/trade-api/docs/curl) -- no OAuth
# redirect exists at all. A fresh access token is generated on demand from
# the user's own api_key (sent as a Bearer header, not a body field) plus a
# live TOTP code derived from their totp_secret.
_GROWW_TOKEN_URL = "https://api.groww.in/v1/token/api/access"
# Groww has no single "trades for today" endpoint like Zerodha/Upstox --
# only GET /v1/order/list (per segment) and GET /v1/order/trades/
# {groww_order_id} (per order, for split-fill detail). sync_today_trades
# uses the order list directly rather than an N+1 per-order trades call;
# see the comment there for the resulting precision trade-off.
_GROWW_ORDER_LIST_URL = "https://api.groww.in/v1/order/list"
_GROWW_SEGMENTS = ("CASH", "FNO")


class GrowwService:
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

    def refresh_access_token(
        self,
        user_id: UUID,
    ) -> str:
        """
        Groww's TOTP-flow token does carry an `expiry` in the response
        (confirmed against Groww's own docs -- contrary to older SDK docs
        claiming "no expiry"), so this is called lazily on every sync
        rather than once at "connect" time, the same refresh-on-demand
        shape as Zerodha/Upstox's daily token expiry.
        """
        connection = self.broker_connection_repository.get_by_user_and_broker(
            user_id=user_id,
            broker_name="groww",
        )
        if not connection or not connection.api_key or not connection.totp_secret_kms_id:
            raise ValueError(
                "No Groww credentials found. Submit your api_key/totp_secret "
                "via POST /brokers/groww/credentials."
            )

        totp_secret = self.vault_repository.get_secret(
            secret_id=UUID(connection.totp_secret_kms_id),
        )
        if not totp_secret:
            raise ValueError(
                "Groww TOTP secret not found in Vault. Please re-submit "
                "your credentials."
            )

        try:
            totp_code = pyotp.TOTP(totp_secret).now()
            response = requests.post(
                _GROWW_TOKEN_URL,
                json={"key_type": "totp", "totp": totp_code},
                headers={
                    "Authorization": f"Bearer {connection.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            response.raise_for_status()
            access_token = response.json()["token"]
        except Exception as e:
            raise ValueError(
                f"Failed to generate Groww access token: {str(e)}"
            )

        vault_name = f"groww_token_{user_id}"
        if connection.access_token_kms_id:
            self.vault_repository.update_secret(
                secret_id=UUID(connection.access_token_kms_id),
                secret_value=access_token,
                name=vault_name,
                description="Groww access token",
            )
        else:
            secret_id = self.vault_repository.create_secret(
                secret_value=access_token,
                name=vault_name,
                description="Groww access token",
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

        return access_token

    def sync_today_trades(
        self,
        user_id: UUID,
        broker_connection_id: UUID,
    ) -> CsvImportResponse:
        access_token = self.refresh_access_token(user_id=user_id)

        orders = []
        for segment in _GROWW_SEGMENTS:
            try:
                response = requests.get(
                    _GROWW_ORDER_LIST_URL,
                    params={"segment": segment, "page": 0, "page_size": 100},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                    timeout=15,
                )
                response.raise_for_status()
                segment_orders = (
                    response.json().get("payload", {}).get("order_list", [])
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to fetch orders from Groww ({segment}): {str(e)}"
                )
            for order in segment_orders:
                order["_segment"] = segment
            orders.extend(segment_orders)

        today = date.today().isoformat()
        imported = 0
        skipped = 0
        errors = []

        for order in orders:
            try:
                if order.get("order_status") != "EXECUTED":
                    continue
                trade_date = order.get("trade_date") or ""
                if trade_date[:10] != today:
                    continue

                instrument_type = "fno" if order["_segment"] == "FNO" else "equity"
                symbol = order["trading_symbol"]

                try:
                    execution_time = datetime.fromisoformat(
                        order["exchange_time"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError, KeyError):
                    execution_time = datetime.now()

                broker_trade_id = str(order["groww_order_id"])
                idempotency_hash = generate_trade_idempotency_hash(
                    broker_connection_id=broker_connection_id,
                    broker_trade_id=broker_trade_id,
                )

                trade_type = order["transaction_type"].lower()
                quantity = Decimal(str(order.get("filled_quantity") or order["quantity"]))
                price = Decimal(str(order["average_fill_price"]))

                # Savepoint-scoped: a duplicate idempotency_hash on resync
                # raises IntegrityError on flush -- without a savepoint
                # boundary here, that would abort the shared request-level
                # transaction, taking every order after it (and this same
                # sync's earlier successes, still uncommitted) down with it.
                savepoint = self.instrument_repository.db.begin_nested()
                try:
                    instrument = self.instrument_repository.get_or_create(
                        symbol=symbol,
                        instrument_type=instrument_type,
                        name=symbol,
                        isin=None,
                    )
                    if instrument_type == "fno":
                        if trade_type == "sell":
                            self.trade_service.process_fno_sell_trade(
                                user_id=user_id,
                                instrument_id=instrument.id,
                                broker_connection_id=broker_connection_id,
                                broker_trade_id=broker_trade_id,
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
                                broker_trade_id=broker_trade_id,
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
                            broker_trade_id=broker_trade_id,
                            quantity=quantity,
                            price=price,
                            execution_time=execution_time,
                            idempotency_hash=idempotency_hash,
                        )
                    savepoint.commit()
                except IntegrityError:
                    savepoint.rollback()
                    skipped += 1
                    continue
                except Exception:
                    savepoint.rollback()
                    raise

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
                        f"Order {order.get('groww_order_id', '?')}: {error_msg}"
                    )

        return CsvImportResponse(
            total_rows=len(orders),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )
