from decimal import Decimal
from datetime import datetime
from uuid import UUID

from app.core.idempotency import generate_trade_idempotency_hash
from app.services.csv_parser_service import CsvParserService
from app.services.trade_service import TradeService
from app.repositories.instrument_repository import InstrumentRepository
from app.schemas.csv_import import CsvImportResponse


class CsvImportService:
    def __init__(
        self,
        csv_parser_service: CsvParserService,
        trade_service: TradeService,
        instrument_repository: InstrumentRepository,
    ):
        self.csv_parser_service = csv_parser_service
        self.trade_service = trade_service
        self.instrument_repository = instrument_repository

    def import_tradebook(
        self,
        file_content: bytes,
        filename: str,
        user_id: UUID,
        broker_connection_id: UUID,
    ) -> CsvImportResponse:
        # STEP 1 — Parse the file
        rows = self.csv_parser_service.parse_tradebook(
            file_content=file_content,
            filename=filename,
        )

        # STEP 2 — Process each row
        imported = 0
        skipped = 0
        errors: list[str] = []

        for row in rows:
            try:
                # Step 2a — Determine instrument_type from segment
                segment = row["segment"]  # already uppercased by parser
                if segment == "FO":
                    instrument_type = "fno"
                else:
                    instrument_type = "equity"

                # Step 2b — Get or create instrument
                instrument = self.instrument_repository.get_or_create(
                    symbol=row["symbol"],
                    instrument_type=instrument_type,
                    name=row["symbol"],  # symbol as name fallback
                    isin=row["isin"],    # None for F&O
                )

                # Step 2c — Parse execution time
                try:
                    execution_time = datetime.fromisoformat(
                        row["order_execution_time"]
                    )
                except (ValueError, TypeError):
                    execution_time = datetime.strptime(
                        row["trade_date"], "%Y-%m-%d"
                    ).replace(hour=0, minute=0, second=0)

                # Step 2d — Build idempotency hash (shared utility)
                idempotency_hash = generate_trade_idempotency_hash(
                    broker_connection_id=broker_connection_id,
                    broker_trade_id=row["trade_id"],
                )

                # Step 2e — Route to correct trade processor
                trade_type = row["trade_type"]  # "buy" or "sell"
                quantity = Decimal(str(row["quantity"]))
                price = row["price"]  # already Decimal from parser

                if instrument_type == "fno":
                    if trade_type == "sell":
                        self.trade_service.process_fno_sell_trade(
                            user_id=user_id,
                            instrument_id=instrument.id,
                            broker_connection_id=broker_connection_id,
                            broker_trade_id=row["trade_id"],
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
                            broker_trade_id=row["trade_id"],
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
                        broker_trade_id=row["trade_id"],
                        quantity=quantity,
                        price=price,
                        execution_time=execution_time,
                        idempotency_hash=idempotency_hash,
                    )

                imported += 1

            except Exception as e:
                error_msg = str(e)
                # Skip duplicate trades silently
                if (
                    "duplicate key" in error_msg.lower()
                    or "uniqueviolation" in error_msg.lower()
                    or "idempotency_hash" in error_msg.lower()
                ):
                    skipped += 1
                else:
                    errors.append(
                        f"Row {row.get('trade_id', '?')}: {error_msg}"
                    )

        # STEP 3 — Return summary
        return CsvImportResponse(
            total_rows=len(rows),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )