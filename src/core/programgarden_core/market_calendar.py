"""Scheduled equity sessions, independent of credentials and live market data.

This schedule includes published holidays and early closes. It cannot observe
new emergency closures, instrument halts, or a broker's ability to accept orders.
"""
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo


@lru_cache(maxsize=8)
def _calendar(name: str, year: int):
    import exchange_calendars

    return exchange_calendars.get_calendar(
        name, start=f"{year}-01-01", end=f"{year}-12-31", side="left",
    )


def scheduled_session_open(name: str, instant: datetime) -> bool:
    """Exact seconds: opening is inclusive and closing is exclusive."""
    if name not in {"XNYS", "XNAS", "XHKG"}:
        raise ValueError("Unsupported exchange calendar")
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Calendar clock must include timezone")
    zone = "Asia/Hong_Kong" if name == "XHKG" else "America/New_York"
    market_date = instant.astimezone(ZoneInfo(zone)).date()
    schedule = _calendar(name, market_date.year).schedule
    day = market_date.isoformat()
    if day not in schedule.index:
        return False
    row = schedule.loc[day]
    clock = instant.astimezone(timezone.utc)
    if not row["open"] <= clock < row["close"]:
        return False
    # XHKG has a scheduled midday break. NaT comparisons are false for markets
    # without breaks; do not admit the lunch interval as an open session.
    if "break_start" in row and row["break_start"] <= clock < row["break_end"]:
        return False
    return True
