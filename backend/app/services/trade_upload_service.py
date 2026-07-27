"""
Generic tradebook upload (CSV / Excel) — column-name detection rather than
a fixed schema, so it accepts exports from Zerodha, Upstox, Groww, or
anything else with roughly the right columns. Separate from
csv_import_service.py (Zerodha-specific tradebook format, requires an
existing broker_connection_id) — this one auto-creates a "csv" broker
connection and tolerates messier input, skipping bad rows instead of
failing the whole upload.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from uuid import UUID

import pandas as pd

from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.repositories.trade_repository import TradeRepository
from app.services.instrument_service import InstrumentService
from app.services.trade_service import TradeService

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

_SYMBOL_EXACT = ("symbol",)
_TYPE_EXACT = ("trade_type", "type", "action")
_QTY_EXACT = ("quantity", "qty")
_PRICE_EXACT = ("price", "avg_price", "trade_price")
_DATE_EXACT = ("order_execution_time", "date", "trade_date")

_SYMBOL_KEYWORDS = ("symbol", "stock")
_TYPE_KEYWORDS = ("buy", "sell", "type", "action")
_QTY_KEYWORDS = ("qty", "quantity", "shares")
_PRICE_KEYWORDS = ("price", "rate", "avg")
_DATE_KEYWORDS = ("date", "time", "execution")


def _read_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    lower = (filename or "").lower()
    if lower.endswith(".csv"):
        return pd.read_csv(BytesIO(file_content))
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(file_content))
    raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")


def _detect_columns(columns: list) -> dict[str, str | None]:
    """Maps our canonical field names to actual column names in the
    uploaded file. Tries exact common header names first (Zerodha-style),
    then falls back to a case-insensitive keyword search."""
    lower_map = {str(c).strip().lower(): c for c in columns}

    def find_exact(candidates: tuple[str, ...]) -> str | None:
        for cand in candidates:
            if cand in lower_map:
                return lower_map[cand]
        return None

    def find_keyword(keywords: tuple[str, ...]) -> str | None:
        for col_lower, original in lower_map.items():
            if any(kw in col_lower for kw in keywords):
                return original
        return None

    return {
        "symbol": find_exact(_SYMBOL_EXACT) or find_keyword(_SYMBOL_KEYWORDS),
        "trade_type": find_exact(_TYPE_EXACT) or find_keyword(_TYPE_KEYWORDS),
        "quantity": find_exact(_QTY_EXACT) or find_keyword(_QTY_KEYWORDS),
        "price": find_exact(_PRICE_EXACT) or find_keyword(_PRICE_KEYWORDS),
        "execution_time": find_exact(_DATE_EXACT) or find_keyword(_DATE_KEYWORDS),
    }


def _parse_trade_type(raw) -> str | None:
    text = str(raw).strip().lower()
    if "buy" in text:
        return "buy"
    if "sell" in text:
        return "sell"
    return None


def _parse_date(raw) -> datetime | None:
    try:
        ts = pd.to_datetime(raw, errors="coerce")
    except (ValueError, TypeError):
        return None
    if ts is None or pd.isna(ts):
        return None
    return ts.to_pydatetime()


def _validate_row(row: dict, columns: dict[str, str | None]) -> tuple[dict | None, str | None]:
    """Returns (parsed_row, None) on success or (None, error_message) on
    failure — exactly one side is populated."""
    missing = [k for k, v in columns.items() if v is None]
    if missing:
        return None, f"could not detect column(s): {', '.join(missing)}"

    symbol_raw = row.get(columns["symbol"])
    if symbol_raw is None or not str(symbol_raw).strip() or str(symbol_raw).strip().lower() == "nan":
        return None, "empty symbol"
    symbol = str(symbol_raw).strip().upper()

    trade_type = _parse_trade_type(row.get(columns["trade_type"]))
    if trade_type is None:
        return None, f"invalid trade type: {row.get(columns['trade_type'])!r}"

    try:
        quantity = Decimal(str(row.get(columns["quantity"])))
    except (InvalidOperation, TypeError, ValueError):
        return None, "invalid quantity"
    if quantity <= 0:
        return None, "quantity must be positive"

    try:
        price = Decimal(str(row.get(columns["price"])))
    except (InvalidOperation, TypeError, ValueError):
        return None, "invalid price"
    if price <= 0:
        return None, "price must be positive"

    execution_time = _parse_date(row.get(columns["execution_time"]))
    if execution_time is None:
        return None, "invalid date format"

    return {
        "symbol": symbol,
        "trade_type": trade_type,
        "quantity": quantity,
        "price": price,
        "execution_time": execution_time,
    }, None


def parse_trade_rows(df: pd.DataFrame) -> tuple[list[dict], list[str], int]:
    """Parses every row of the dataframe. Returns (valid_rows,
    error_messages capped at 10, failed_count) — a bad row is skipped,
    never fails the whole upload."""
    columns = _detect_columns(list(df.columns))
    valid_rows: list[dict] = []
    errors: list[str] = []
    failed = 0

    for i, row in enumerate(df.to_dict(orient="records"), start=1):
        parsed, err = _validate_row(row, columns)
        if parsed is None:
            failed += 1
            if len(errors) < 10:
                errors.append(f"row {i}: {err}")
            continue
        valid_rows.append(parsed)

    return valid_rows, errors, failed


def build_idempotency_hash(
    user_id: UUID,
    symbol: str,
    trade_type: str,
    quantity: Decimal,
    price: Decimal,
    execution_time: datetime,
) -> str:
    raw = f"csv:{user_id}:{symbol}:{trade_type}:{quantity}:{price}:{execution_time}"
    return hashlib.sha256(raw.encode()).hexdigest()


class TradeUploadService:
    def __init__(
        self,
        trade_repository: TradeRepository,
        instrument_service: InstrumentService,
        broker_connection_repository: BrokerConnectionRepository,
        trade_service: TradeService,
    ):
        self.trade_repository = trade_repository
        self.instrument_service = instrument_service
        self.broker_connection_repository = broker_connection_repository
        self.trade_service = trade_service

    def _get_or_create_csv_connection(self, user_id: UUID):
        existing = self.broker_connection_repository.get_by_user_and_broker(user_id, "csv")
        if existing:
            return existing
        return self.broker_connection_repository.create_connection(
            user_id=user_id, broker_name="csv"
        )

    def process_upload(self, file_content: bytes, filename: str, user_id: UUID) -> dict:
        try:
            df = _read_dataframe(file_content, filename)
        except Exception as e:
            return {
                "success": False,
                "trades_processed": 0,
                "trades_skipped": 0,
                "trades_failed": 0,
                "errors": [f"Could not read file: {e}"],
            }

        valid_rows, errors, failed = parse_trade_rows(df)

        connection = self._get_or_create_csv_connection(user_id)
        # Re-queried on every call (not cached) so a second upload of the
        # same rows is correctly detected as duplicates, even across
        # separate requests / service instances.
        existing_hashes = {
            t.idempotency_hash for t in self.trade_repository.get_by_user(user_id)
        }

        processed = 0
        skipped = 0

        for row in valid_rows:
            hash_ = build_idempotency_hash(
                user_id,
                row["symbol"],
                row["trade_type"],
                row["quantity"],
                row["price"],
                row["execution_time"],
            )
            if hash_ in existing_hashes:
                skipped += 1
                continue

            try:
                instrument = self.instrument_service.get_or_create_instrument(
                    symbol=row["symbol"],
                    instrument_type="equity",
                    name=row["symbol"],
                )
                self.trade_service.process_trade(
                    trade_type=row["trade_type"],
                    user_id=user_id,
                    instrument_id=instrument.id,
                    broker_connection_id=connection.id,
                    broker_trade_id=hash_[:32],
                    quantity=row["quantity"],
                    price=row["price"],
                    execution_time=row["execution_time"],
                    idempotency_hash=hash_,
                )
                existing_hashes.add(hash_)
                processed += 1
            except Exception as e:
                failed += 1
                if len(errors) < 10:
                    errors.append(f"{row['symbol']}: {e}")

        return {
            "success": True,
            "trades_processed": processed,
            "trades_skipped": skipped,
            "trades_failed": failed,
            "errors": errors,
        }
