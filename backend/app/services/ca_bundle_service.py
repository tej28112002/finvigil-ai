import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.tax_utils import get_ay_date_range
from app.repositories.ca_export_job_repository import CaExportJobRepository
from app.repositories.instrument_repository import InstrumentRepository
from app.repositories.realized_gain_repository import RealizedGainRepository
from app.services.harvesting_service import HarvestingService
from app.services.itr3_export_service import ITR3ExportService
from app.services.tax_export_service import TaxExportService

_CSV_COLUMNS = [
    "symbol", "isin", "quantity_sold", "buy_date", "sell_date",
    "buy_price", "sell_price", "holding_days", "gain_type", "profit_loss",
]

_INCOME_TYPES_FOR_CSV = ["equity_capital_gains", "crypto_vda"]


class CABundleService:
    """
    Phase 11.1 — packages everything a CA needs for one AY into a single
    ZIP, built entirely in memory (zipfile + io.BytesIO — no temp files on
    disk). Reuses ITR3ExportService and TaxExportService as-is rather than
    duplicating their logic; note that calling TaxExportService also
    creates its OWN ca_export_jobs audit row (export_type=
    "capital_gains_json") as a side effect of that existing service — this
    method creates a SECOND, separate audit row for the bundle itself
    (export_type="ca_bundle_zip"). Both are legitimate, distinct records of
    what was generated.
    """

    def __init__(
        self,
        itr3_export_service: ITR3ExportService,
        tax_export_service: TaxExportService,
        realized_gain_repository: RealizedGainRepository,
        instrument_repository: InstrumentRepository,
        harvesting_service: HarvestingService,
        ca_export_job_repository: CaExportJobRepository,
    ):
        self.itr3_export_service = itr3_export_service
        self.tax_export_service = tax_export_service
        self.realized_gain_repository = realized_gain_repository
        self.instrument_repository = instrument_repository
        self.harvesting_service = harvesting_service
        self.ca_export_job_repository = ca_export_job_repository

    def generate_bundle(self, user_id: UUID, assessment_year: str) -> bytes:
        # Step 1 — ITR-3 schedules. Raises ItrSchemaNotFoundError (no
        # mapping for this AY) or ValueError (no tax summary yet) — left
        # to propagate to the API layer unmodified, same as
        # POST /tax/itr3-export already does.
        itr3_result = self.itr3_export_service.generate_export(
            user_id=user_id, assessment_year=assessment_year
        )

        # Step 2 — CA-readable capital gains summary (Pydantic model ->
        # JSON-safe dict; mode="json" converts Decimal/UUID/datetime).
        capital_gains_summary = self.tax_export_service.generate_export(
            user_id=user_id, assessment_year=assessment_year
        )
        capital_gains_summary_json = capital_gains_summary.model_dump(mode="json")

        # Step 3 — realized_gains.csv, all income types, this AY only.
        realized_gains_csv = self._build_realized_gains_csv(
            user_id=user_id, assessment_year=assessment_year
        )

        # Step 4 — harvest opportunities, degrading gracefully if the
        # harvesting service can't run (e.g. no broker connected for live
        # prices) rather than failing the whole bundle.
        harvest_json = self._build_harvest_opportunities(
            user_id=user_id, assessment_year=assessment_year
        )

        # Step 5 — README
        readme_text = self._build_readme(
            assessment_year=assessment_year,
            schema_version=itr3_result["schema_version"],
        )

        # Step 6 — zip everything in memory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("itr3_schedules.json", json.dumps(itr3_result, indent=2))
            zf.writestr(
                "capital_gains_summary.json",
                json.dumps(capital_gains_summary_json, indent=2),
            )
            zf.writestr("realized_gains.csv", realized_gains_csv)
            zf.writestr("harvest_opportunities.json", json.dumps(harvest_json, indent=2))
            zf.writestr("README.txt", readme_text)
        zip_bytes = buffer.getvalue()

        # Step 7 — audit record for the bundle itself
        self.ca_export_job_repository.create_export_job(
            user_id=user_id,
            assessment_year=assessment_year,
            export_type="ca_bundle_zip",
            status="completed",
        )

        return zip_bytes

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_realized_gains_csv(self, user_id: UUID, assessment_year: str) -> str:
        start, end = get_ay_date_range(assessment_year)

        gains = []
        for income_type in _INCOME_TYPES_FOR_CSV:
            gains += self.realized_gain_repository.get_by_user_income_type_and_date_range(
                user_id=user_id,
                income_type=income_type,
                start=start,
                end=end,
            )
        gains.sort(key=lambda g: g.sell_date)

        instrument_ids = {g.instrument_id for g in gains}
        instruments = {}
        for instrument_id in instrument_ids:
            instrument = self.instrument_repository.get_by_id(instrument_id)
            if instrument:
                instruments[instrument_id] = instrument

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(_CSV_COLUMNS)
        for g in gains:
            instrument = instruments.get(g.instrument_id)
            writer.writerow(
                [
                    instrument.symbol if instrument else "UNKNOWN",
                    instrument.isin if instrument and instrument.isin else "",
                    str(Decimal(str(g.quantity_sold))),
                    g.buy_date.date().isoformat(),
                    g.sell_date.date().isoformat(),
                    str(Decimal(str(g.buy_price))),
                    str(Decimal(str(g.sell_price))),
                    g.holding_days,
                    g.gain_type or "",
                    str(Decimal(str(g.profit_loss))),
                ]
            )
        return output.getvalue()

    def _build_harvest_opportunities(self, user_id: UUID, assessment_year: str) -> dict:
        try:
            summary = self.harvesting_service.get_harvest_summary(
                user_id=user_id, assessment_year=assessment_year
            )
            candidates = self.harvesting_service.get_harvest_candidates(
                user_id=user_id, assessment_year=assessment_year
            )
        except Exception:
            # Harvesting needs live prices (broker connection + quote
            # fetch) — a failure there shouldn't fail the whole bundle.
            return {
                "available": False,
                "message": "No harvest analysis available",
                "candidates": [],
            }

        return {
            "available": True,
            "summary": self._decimals_to_str(summary),
            "candidates": [self._decimals_to_str(c) for c in candidates],
        }

    @staticmethod
    def _decimals_to_str(obj):
        """JSON can't serialize Decimal directly — convert every Decimal
        (recursively) to its exact string form, same convention used for
        every other JSONB/JSON payload in this app."""
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return {k: CABundleService._decimals_to_str(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CABundleService._decimals_to_str(v) for v in obj]
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return obj

    @staticmethod
    def _build_readme(assessment_year: str, schema_version: str) -> str:
        generated_at = datetime.now(timezone.utc).isoformat()
        return (
            f"This bundle was generated by FinVigil AI for Assessment Year {assessment_year}.\n"
            f"\n"
            f"Contents:\n"
            f"- itr3_schedules.json: Upload this to ITR filing software for Schedule CG and VDA\n"
            f"- capital_gains_summary.json: Human-readable summary for your reference\n"
            f"- realized_gains.csv: Transaction-level detail for all capital gains\n"
            f"- harvest_opportunities.json: Tax-loss harvesting opportunities identified\n"
            f"\n"
            f"IMPORTANT: This bundle contains ONLY capital gains data. Personal details, "
            f"salary, house property, TDS, and final tax computation must be added "
            f"separately before filing.\n"
            f"\n"
            f"Generated: {generated_at}\n"
            f"Schema version: {schema_version}\n"
            f"Disclaimer: Not a complete ITR-3 filing.\n"
        )
