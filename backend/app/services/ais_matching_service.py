from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.ais_line import AisLine
from app.repositories.realized_gain_repository import RealizedGainRepository

ZERO = Decimal("0")
MATCH_ABS_TOLERANCE = Decimal("1.00")
MATCH_REL_TOLERANCE = Decimal("0.01")  # 1%
QTY_RATIO_TOLERANCE = Decimal("0.02")  # 2% band around a "nice" ratio

_EQUITY_KEYWORDS = ["securit", "equity", "share", "stock", "mutual fund"]
_CRYPTO_KEYWORDS = ["virtual digital asset", "vda", "crypto", "digital asset"]
_TDS_KEYWORDS = ["tds", "tax deducted"]

# Ratios consistent with a plausible unit-count difference (a missed stock
# split, a doubled/halved lot) rather than a genuine value disagreement.
_NICE_RATIOS = [
    Decimal("2"), Decimal("0.5"),
    Decimal("3"), Decimal("1") / Decimal("3"),
    Decimal("4"), Decimal("0.25"),
]


class AisMatchingService:
    """
    Auto-match engine (BRD FR-AIS-03). For every AisLine on an upload,
    compares its reported_amount against FinVigil's own computed sale
    consideration for the same category, at SECTION/CATEGORY granularity —
    real AIS/TIS data has no per-transaction detail (no ISIN, quantity, or
    price on a line), so per-holding-lot matching isn't possible; this
    reconciles aggregate-reported vs aggregate-computed, the same
    granularity the AIS portal itself reports at.

    Category detection is a keyword heuristic over section_code +
    description, NOT a lookup against real CBDT/SFT code tables (pinning
    those codes is a separate, unresolved dependency — BRD Appendix A). An
    unrecognized section falls through to 'unresolved', never silently
    guessed as matched.
    """

    def __init__(self, realized_gain_repository: RealizedGainRepository):
        self.realized_gain_repository = realized_gain_repository

    def run_match(
        self,
        user_id: UUID,
        assessment_year: str,
        lines: list[AisLine],
        ay_start: datetime,
        ay_end: datetime,
    ) -> list[dict]:
        computed_by_category = {
            "equity_capital_gains": self._computed_sale_consideration(
                user_id, "equity_capital_gains", ay_start, ay_end
            ),
            "crypto_vda": self._computed_sale_consideration(
                user_id, "crypto_vda", ay_start, ay_end
            ),
        }

        seen_signatures: dict[tuple, UUID] = {}
        results: list[dict] = []

        for line in lines:
            reported = (
                Decimal(str(line.reported_amount))
                if line.reported_amount is not None
                else ZERO
            )

            signature = (line.section_code.strip().lower(), reported.quantize(Decimal("0.01")))
            if signature in seen_signatures:
                results.append(
                    {
                        "ais_line_id": line.id,
                        "match_status": "mismatch",
                        "mismatch_type": "duplicate",
                        "resolution_notes": (
                            "Duplicate of an earlier line with the same "
                            "section code and amount in this upload."
                        ),
                    }
                )
                continue
            seen_signatures[signature] = line.id

            category = self._detect_category(line.section_code, line.description)

            if category == "tds":
                results.append(
                    {
                        "ais_line_id": line.id,
                        "match_status": "mismatch",
                        "mismatch_type": "TDS",
                        "resolution_notes": (
                            "No TDS credit ledger exists yet to reconcile "
                            "this against — manual verification required."
                        ),
                    }
                )
                continue

            if category is None:
                results.append(
                    {
                        "ais_line_id": line.id,
                        "match_status": "unresolved",
                        "mismatch_type": None,
                        "resolution_notes": (
                            "Unrecognized AIS section — could not "
                            "automatically categorize against FinVigil "
                            "data. Manual review required."
                        ),
                    }
                )
                continue

            computed = computed_by_category[category]

            if computed == ZERO and reported > ZERO:
                results.append(
                    {
                        "ais_line_id": line.id,
                        "match_status": "mismatch",
                        "mismatch_type": "missing",
                        "resolution_notes": (
                            f"AIS reports Rs.{reported} but FinVigil has no "
                            f"matching trades for this category in "
                            f"{assessment_year} — check that the relevant "
                            f"broker is connected and synced."
                        ),
                    }
                )
                continue

            if self._within_tolerance(computed, reported):
                results.append(
                    {
                        "ais_line_id": line.id,
                        "match_status": "matched",
                        "mismatch_type": None,
                        "resolution_notes": None,
                    }
                )
                continue

            mismatch_type = (
                "qty" if self._looks_like_qty_mismatch(computed, reported) else "price"
            )
            results.append(
                {
                    "ais_line_id": line.id,
                    "match_status": "mismatch",
                    "mismatch_type": mismatch_type,
                    "resolution_notes": (
                        f"FinVigil computed Rs.{computed} vs AIS-reported "
                        f"Rs.{reported} for this category — review before "
                        f"filing."
                    ),
                }
            )

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _computed_sale_consideration(
        self,
        user_id: UUID,
        income_type: str,
        start: datetime,
        end: datetime,
    ) -> Decimal:
        gains = self.realized_gain_repository.get_by_user_income_type_and_date_range(
            user_id=user_id,
            income_type=income_type,
            start=start,
            end=end,
        )
        return sum(
            (
                Decimal(str(g.sell_price)) * Decimal(str(g.quantity_sold))
                for g in gains
            ),
            ZERO,
        )

    @staticmethod
    def _detect_category(section_code: str, description: str | None) -> str | None:
        haystack = f"{section_code} {description or ''}".lower()
        if any(k in haystack for k in _TDS_KEYWORDS):
            return "tds"
        if any(k in haystack for k in _CRYPTO_KEYWORDS):
            return "crypto_vda"
        if any(k in haystack for k in _EQUITY_KEYWORDS):
            return "equity_capital_gains"
        return None

    @staticmethod
    def _within_tolerance(computed: Decimal, reported: Decimal) -> bool:
        diff = abs(computed - reported)
        if diff <= MATCH_ABS_TOLERANCE:
            return True
        larger = max(abs(computed), abs(reported))
        if larger == ZERO:
            return True
        return (diff / larger) <= MATCH_REL_TOLERANCE

    @staticmethod
    def _looks_like_qty_mismatch(computed: Decimal, reported: Decimal) -> bool:
        """
        Heuristic only — ais_lines carries no quantity field, so a true
        qty-vs-price distinction isn't derivable from this data. If the
        ratio between computed and reported sits close to a "nice" integer
        or simple-fraction multiple (2x, 0.5x, 3x, ...), that's consistent
        with a unit-count difference (e.g. a stock split not applied, a
        lot double-counted) rather than a genuine price disagreement —
        flagged as 'qty'. Anything else defaults to 'price'.
        """
        if reported == ZERO:
            return False
        ratio = computed / reported
        return any(abs(ratio - nice) <= QTY_RATIO_TOLERANCE for nice in _NICE_RATIOS)
