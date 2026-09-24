from datetime import datetime
from zoneinfo import ZoneInfo

from programgarden.executor import ls_overseas_business_dates, ls_overseas_stock_side


def test_overnight_session_accepts_the_us_business_date():
    # 2026-09-24 04:17 KST == 2026-09-23 15:17 New York: the broker echoed 20260923.
    now = datetime(2026, 9, 24, 4, 17, tzinfo=ZoneInfo("Asia/Seoul"))
    assert ls_overseas_business_dates(now) == {"20260924", "20260923"}


def test_daytime_session_dates_coincide():
    now = datetime(2026, 9, 24, 23, 0, tzinfo=ZoneInfo("Asia/Seoul"))  # 10:00 New York same day
    assert ls_overseas_business_dates(now) == {"20260924"}


def test_naive_input_is_read_as_seoul_time():
    assert ls_overseas_business_dates(datetime(2026, 9, 24, 4, 17)) == {"20260924", "20260923"}


def test_side_accepts_single_character_and_zero_padded_codes():
    assert ls_overseas_stock_side("2") == "buy"
    assert ls_overseas_stock_side("02") == "buy"
    assert ls_overseas_stock_side("1") == "sell"
    assert ls_overseas_stock_side("01") == "sell"


def test_side_reports_unknown_instead_of_guessing_sell():
    assert ls_overseas_stock_side("") == "unknown"
    assert ls_overseas_stock_side(None) == "unknown"
    assert ls_overseas_stock_side("7") == "unknown"
