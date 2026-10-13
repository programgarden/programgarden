"""Explicit mappings for the existing single-page LS futures chart requests."""

MINUTE_INTERVALS = {"30s": 0, "1m": 1, "5m": 5, "15m": 15, "30m": 30}
DAILY_INTERVALS = {"1d": "0", "1w": "1", "1M": "2"}
INTERVAL_ALIASES = {"1min": "1m", "5min": "5m", "15min": "15m", "30min": "30m"}


def normalize_interval(interval):
    """Preserve known legacy minute names without falling back to daily data."""
    if isinstance(interval, str):
        interval = INTERVAL_ALIASES.get(interval, interval)
        if interval in MINUTE_INTERVALS or interval in DAILY_INTERVALS:
            return interval
    raise ValueError(
        "UNSUPPORTED_FUTURES_HISTORY_INTERVAL: choose 30s, 1m, 5m, 15m, 30m, "
        "1d, 1w or 1M. Hourly and unknown periods are not implemented; no daily fallback."
    )


def validate_adjust(adjust):
    """Never describe exact-contract prices as rollover-adjusted history."""
    if adjust is not False:
        raise ValueError("FUTURES_HISTORY_ADJUST_UNSUPPORTED: adjust must be false; rollover adjustment is not implemented")
