import io
from decimal import Decimal

import pandas as pd


class CsvParserService:
    """
    Pure file-parsing service for Zerodha tradebook files.
    Zero DB access — takes raw bytes, validates structure,
    returns a list of clean row dicts.
    """

    REQUIRED_COLUMNS = [
        "Symbol",
        "Trade Date",
        "Segment",
        "Trade Type",
        "Quantity",
        "Price",
        "Trade ID",
        "Order Execution Time",
    ]

    def parse_tradebook(
        self,
        file_content: bytes,
        filename: str,
    ) -> list[dict]:
        """
        Parse a Zerodha tradebook file (.xlsx or .csv).

        Args:
            file_content: Raw bytes of the uploaded file.
            filename:     Original filename (used to detect format).

        Returns:
            List of clean row dicts ready for downstream processing.

        Raises:
            ValueError: If the file format is unsupported or the
                        tradebook structure is invalid.
        """

        # ----------------------------------------------------------
        # STEP 1 — Detect file type and read into DataFrame
        # ----------------------------------------------------------
        if filename.lower().endswith(".xlsx"):
            df = pd.read_excel(
                io.BytesIO(file_content),
                header=14,
                sheet_name=0,
            )
        elif filename.lower().endswith(".csv"):
            # Zerodha CSV exports may include 14 branding rows.
            # Try header=14 first; fall back to header=0.
            df = pd.read_csv(
                io.BytesIO(file_content),
                header=14,
            )
            if not self._has_required_columns(df):
                df = pd.read_csv(
                    io.BytesIO(file_content),
                    header=0,
                )
        else:
            raise ValueError(
                "Unsupported file format. "
                "Please upload a .xlsx or .csv file."
            )

        # ----------------------------------------------------------
        # STEP 2 — Drop unnamed columns
        # ----------------------------------------------------------
        unnamed_cols = [
            col for col in df.columns
            if str(col).startswith("Unnamed")
        ]
        df = df.drop(columns=unnamed_cols)

        # ----------------------------------------------------------
        # STEP 3 — Validate required columns present
        # ----------------------------------------------------------
        missing = [
            col for col in self.REQUIRED_COLUMNS
            if col not in df.columns
        ]
        if missing:
            raise ValueError(
                f"Invalid tradebook format. "
                f"Missing columns: {missing}. "
                f"Please download a fresh tradebook "
                f"from Zerodha Console."
            )

        # ----------------------------------------------------------
        # STEP 4 — Drop completely empty rows
        # ----------------------------------------------------------
        df = df.dropna(subset=["Symbol", "Trade ID"])

        # ----------------------------------------------------------
        # STEP 5 — Build and return list of clean dicts
        # ----------------------------------------------------------
        rows: list[dict] = []
        for _, row in df.iterrows():
            rows.append({
                "symbol": str(row["Symbol"]).strip(),
                "isin": (
                    str(row["ISIN"]).strip()
                    if pd.notna(row.get("ISIN"))
                    else None
                ),
                "trade_date": str(row["Trade Date"]).strip(),
                "exchange": str(
                    row.get("Exchange", "NSE")
                ).strip(),
                "segment": str(row["Segment"]).strip().upper(),
                "trade_type": str(
                    row["Trade Type"]
                ).strip().lower(),
                "quantity": int(row["Quantity"]),
                "price": Decimal(str(row["Price"])),
                "trade_id": str(row["Trade ID"]).strip(),
                "order_execution_time": str(
                    row["Order Execution Time"]
                ).strip(),
            })
        return rows

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_required_columns(self, df: pd.DataFrame) -> bool:
        """Check whether the DataFrame contains all required columns."""
        return all(
            col in df.columns
            for col in self.REQUIRED_COLUMNS
        )
