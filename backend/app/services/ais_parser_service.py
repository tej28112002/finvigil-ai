import io
import json
from decimal import Decimal, InvalidOperation

import pandas as pd

# BRD FR-AIS-01 priority order is JSON -> CSV -> PDF (OCR last). PDF/OCR
# parsing is deliberately NOT built here — it's explicitly the lowest
# priority in that same requirement and needs a separate OCR pipeline
# decision (engine choice, cost, accuracy), not a natural extension of
# this parser.


class AisParserService:
    """
    Pure file-parsing service for AIS uploads — zero DB access, mirrors
    CsvParserService's shape. Real AIS/TIS portal exports are reported at
    the SFT-source/section level (no per-transaction ISIN/qty/price), so
    both formats parse into the same flat shape: one dict per reported
    line with section_code, description, reported_amount.
    """

    def parse_json(self, file_content: bytes) -> list[dict]:
        try:
            data = json.loads(file_content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid JSON file: {e}")

        if isinstance(data, list):
            raw_lines = data
        elif isinstance(data, dict):
            raw_lines = data.get("lines") or data.get("data") or data.get("records")
            if raw_lines is None:
                raise ValueError(
                    "AIS JSON must be a list of entries, or an object with "
                    "a 'lines' array."
                )
        else:
            raise ValueError("AIS JSON must be a list or an object with a 'lines' array.")

        return self._normalize_rows(raw_lines)

    def parse_csv(self, file_content: bytes) -> list[dict]:
        try:
            df = pd.read_csv(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Could not read AIS CSV file: {e}")

        # Case/whitespace-insensitive header match against the accepted
        # aliases for each field — real AIS CSV exports don't have a
        # standardized header name for these columns.
        col_map = {str(c).strip().lower(): c for c in df.columns}
        section_col = self._find_column(
            col_map, ["section_code", "section", "sft code", "sft_code", "code"]
        )
        if section_col is None:
            raise ValueError(
                "AIS CSV must have a section/SFT code column "
                "(e.g. 'section_code', 'SFT Code')."
            )
        desc_col = self._find_column(
            col_map, ["description", "desc", "particulars", "information description"]
        )
        amount_col = self._find_column(
            col_map,
            ["reported_amount", "amount", "value", "reported amount", "amount paid/credited"],
        )
        if amount_col is None:
            raise ValueError(
                "AIS CSV must have an amount column (e.g. 'reported_amount', 'Amount')."
            )

        df = df.dropna(subset=[section_col])

        rows: list[dict] = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "section_code": str(row[section_col]).strip(),
                    "description": (
                        str(row[desc_col]).strip()
                        if desc_col and pd.notna(row.get(desc_col))
                        else None
                    ),
                    "reported_amount": row.get(amount_col),
                }
            )
        return self._normalize_rows(rows)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_column(col_map: dict, aliases: list[str]) -> str | None:
        for alias in aliases:
            if alias in col_map:
                return col_map[alias]
        return None

    @staticmethod
    def _normalize_rows(raw_lines) -> list[dict]:
        if not isinstance(raw_lines, list):
            raise ValueError("AIS entries must be a list.")

        rows: list[dict] = []
        for i, item in enumerate(raw_lines):
            if not isinstance(item, dict):
                raise ValueError(f"Entry {i} is not a valid object.")

            section_code = (
                item.get("section_code")
                or item.get("section")
                or item.get("sft_code")
                or item.get("code")
            )
            if not section_code or not str(section_code).strip():
                raise ValueError(f"Entry {i} is missing a section_code.")

            description = item.get("description") or item.get("particulars")

            raw_amount = item.get("reported_amount")
            if raw_amount is None:
                raw_amount = item.get("amount")

            reported_amount: Decimal | None = None
            if raw_amount is not None and str(raw_amount).strip() != "":
                try:
                    reported_amount = Decimal(str(raw_amount))
                except InvalidOperation:
                    raise ValueError(
                        f"Entry {i} ({section_code}) has a non-numeric amount: {raw_amount!r}"
                    )

            rows.append(
                {
                    "section_code": str(section_code).strip(),
                    "description": str(description).strip() if description else None,
                    "reported_amount": reported_amount,
                }
            )
        return rows
