from datetime import datetime, timezone


def get_assessment_year(sell_date: datetime) -> str:
    """
    Map a sell/transaction date to its Indian Assessment Year (AY).
    FY runs April-March; AY = the year after FY ends.
    MUST be used by every service that buckets realized income by AY, so the
    mapping is identical across equity, F&O, and crypto engines.
    Verified: 2025-06-15 -> AY 2026-27.
    """
    if sell_date.month >= 4:
        fy_start_year = sell_date.year
    else:
        fy_start_year = sell_date.year - 1

    ay_start_year = fy_start_year + 1
    ay_end_year = ay_start_year + 1

    return f"{ay_start_year}-{str(ay_end_year)[2:]}"


def get_ay_date_range(assessment_year: str) -> tuple[datetime, datetime]:
    """
    The exact inverse of get_assessment_year(): given an AY string (e.g.
    "2026-27"), returns the [start, end) half-open UTC datetime range of the
    FY that maps to it — start = April 1 of fy_start_year, end = April 1 of
    fy_start_year + 1 (exclusive), so a comparison is `start <= date < end`
    with no microsecond-boundary ambiguity.

    Exists so realized_gains/tds_credit_ledger can be filtered by AY at the
    SQL level (WHERE sell_date >= start AND sell_date < end) instead of
    fetching every row across a user's entire trading history and filtering
    in Python — correct today's small test data, but fetches strictly more
    rows every year as real trading history accumulates.

    MUST stay the exact inverse of get_assessment_year() — verified by a
    dedicated round-trip test (see backend/tests or the Stage-2D-followup
    investigation script) checking classify-then-range-check agrees with
    get_assessment_year() for every day across several years, including the
    March 31 / April 1 boundary specifically.
    """
    ay_start_year = int(assessment_year.split("-")[0])
    fy_start_year = ay_start_year - 1
    start = datetime(fy_start_year, 4, 1, tzinfo=timezone.utc)
    end = datetime(fy_start_year + 1, 4, 1, tzinfo=timezone.utc)
    return start, end
