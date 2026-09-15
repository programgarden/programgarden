"""Retain dated broker equity and daily cash flows without inventing a return."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from ..accno.CIDBQ03000.blocks import CIDBQ03000InBlock1, CIDBQ03000Response


AMOUNT_FIELDS = {
    "equity": "EvalAssetAmt",
    "daily_net_cash_flow": "CustmMnyioAmt",
    "unrealized_pnl": "AbrdFutsEvalPnlAmt",
    "margin": "AbrdFutsCsgnMgn",
}
SNAPSHOT_FIELDS = {"TrdDt", "CrcyObjCode", *AMOUNT_FIELDS.values()}


def _date(value):
    if value == "":
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{8}", value):
        raise ValueError("invalid_trading_date")
    datetime.strptime(value, "%Y%m%d")
    return value


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("invalid_account_amount")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("invalid_account_amount") from exc
    if not number.is_finite():
        raise ValueError("nonfinite_account_amount")
    return number


def futures_account_snapshot(response, request, observed_at):
    """Whitelist complete currency rows from the existing CIDBQ03000 query.

    Daily net flow is a snapshot, not an increment to sum on every poll. An
    empty broker date stays unknown, including around overnight sessions.
    Currency targets such as TOT(USD) are retained separately from native rows.
    No account identifiers, return percentage or inferred gain/loss split leaves
    this boundary. Missing optional amounts remain None; malformed ones reject
    the snapshot. A failed or partial response cannot replace missing values
    with Pydantic defaults or an older observation.
    """
    if not isinstance(response, CIDBQ03000Response) or not isinstance(request, CIDBQ03000InBlock1):
        return None
    if (response.status_code != 200 or response.error_msg
            or response.rsp_cd not in {"00000", "00001", "00136"}
            or response.header is None or response.header.tr_cd not in {"CIDBQ03000", "CIDBQ"}
            or response.header.tr_cont != "N" or response.header.tr_cont_key.strip()
            or not isinstance(observed_at, datetime) or observed_at.utcoffset() is None):
        return None
    echo = response.block1
    echo_fields = {"RecCnt", "AcntTpCode", "TrdDt"}
    if (echo is None or not echo_fields <= echo.model_fields_set
            or any(getattr(echo, field) != getattr(request, field) for field in echo_fields)
            or request.RecCnt != 1 or request.AcntTpCode != "1"):
        return None
    raw_rows = response._account_snapshot_rows
    if not raw_rows or len(raw_rows) != len(response.block2):
        return None
    rows = []
    seen = set()
    try:
        requested_date = _date(request.TrdDt)
        trading_date = _date(echo.TrdDt)
        for raw, parsed in zip(raw_rows, response.block2):
            required = {"CrcyObjCode", "TrdDt", "EvalAssetAmt"}
            if not required <= raw.keys() or not required <= parsed.model_fields_set:
                return None
            target = raw["CrcyObjCode"]
            if not isinstance(target, str):
                return None
            target = target.strip().upper()
            match = re.fullmatch(r"([A-Z]{3})|TOT\(([A-Z]{3})\)", target)
            if not match or target in seen:
                return None
            seen.add(target)
            row_date = _date(raw["TrdDt"])
            if row_date != trading_date:
                return None
            row = {
                "currency_target": target,
                "currency": match.group(1) or match.group(2),
                "aggregation": "native_currency" if match.group(1) else "broker_aggregate",
                "trading_date": row_date,
            }
            for output, source in AMOUNT_FIELDS.items():
                row[output] = _amount(raw[source]) if source in raw else None
            rows.append(row)
    except (TypeError, ValueError, AttributeError):
        return None
    return {
        "version": 1,
        "product": "overseas_futures",
        "source": "CIDBQ03000",
        "basis": "broker_account_snapshot",
        "observed_at": observed_at.isoformat(),
        "requested_date": requested_date,
        "trading_date": trading_date,
        "cash_flow_basis": "business_day_net",
        "rows": sorted(rows, key=lambda row: row["currency_target"]),
    }
