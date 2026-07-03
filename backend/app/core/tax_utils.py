from datetime import datetime


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
