"""Parse local CIDBQ02400 execution evidence without inferring accounting.

The returned wall time has no implicit timezone. Callers must establish the
broker timezone before converting it to an instant. Order date, execution date
and execution wall time remain independent broker fields. This module neither
establishes complete query coverage nor calculates monetary PnL.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Iterable, Mapping


SOURCE_TR = "CIDBQ02400"
EVIDENCE_FIELDS = (
    "FutsOrdStatCode", "TrxStatCode", "TrxStatCodeNm", "TrdTpNm", "TpCodeNm",
    "MdaCode", "ExecDt", "ExecDttm",
)


@dataclass(frozen=True)
class FuturesExecutionObservation:
    broker_order_no: str
    broker_order_date: date
    broker_execution_no: str
    broker_execution_date: date
    execution_datetime_raw: str
    execution_wall_time: datetime
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    evidence: Mapping[str, Any]
    source_tr: str = SOURCE_TR
    source_status: str | None = None


@dataclass(frozen=True)
class FuturesExecutionIssue:
    reason: str
    broker_order_no: str | None
    broker_order_date: date | None
    broker_execution_no: str | None
    evidence: Mapping[str, Any]
    source_tr: str = SOURCE_TR


@dataclass(frozen=True)
class ParsedFuturesExecutions:
    executions: tuple[FuturesExecutionObservation, ...]
    issues: tuple[FuturesExecutionIssue, ...]


def normalize_broker_identity(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isascii() and text.isdecimal():
        return text.lstrip("0") or None
    if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", text):
        return None
    # Preserve opaque broker strings and their case; never substitute an
    # exchange execution number or any other identifier namespace.
    return text


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 8 or not value.isascii() or not value.isdecimal():
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount.is_finite() else None


def _wall_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) != 17 or not value.isascii() or not value.isdecimal():
        return None
    try:
        result = datetime.strptime(value, "%Y%m%d%H%M%S%f")
        return result if result.strftime("%Y%m%d%H%M%S%f")[:17] == value else None
    except ValueError:
        return None


def parse_futures_execution_history(rows: Iterable[Any]) -> ParsedFuturesExecutions:
    """Preserve positive execution facts and report unusable/correction rows.

    Pydantic defaults do not establish that the broker supplied a field.
    Output status 1 or 4 is not used as a universal execution filter; identity,
    quantity and explicit execution fields supply the evidence. Ordinary zero
    quantity rows are ignored. Cancellation labels remain issues even when their
    quantity is zero. No subtraction, deletion, source alias or fill ID is guessed.
    """
    executions: list[FuturesExecutionObservation] = []
    issues: list[FuturesExecutionIssue] = []
    for item in rows:
        if hasattr(item, "model_dump"):
            row = item.model_dump(exclude_unset=True)
        elif isinstance(item, Mapping):
            row = dict(item)
        else:
            raise TypeError("History rows must be response models or mappings")

        order_no = normalize_broker_identity(row.get("OvrsFutsOrdNo"))
        order_date = _date(row.get("OrdDt"))
        execution_no = normalize_broker_identity(row.get("OvrsFutsExecNo"))
        evidence = {key: row[key] for key in EVIDENCE_FIELDS if key in row}

        def issue(reason: str) -> None:
            issues.append(FuturesExecutionIssue(reason, order_no, order_date, execution_no, evidence))

        transaction_label = str(row.get("TrxStatCodeNm") or "").strip()
        if transaction_label == "체결취소":
            issue("execution_cancellation_effect_unverified")
            continue
        quantity = _decimal(row.get("ExecQty"))
        if quantity == 0:
            continue
        if quantity is None or quantity < 0 or quantity != quantity.to_integral_value():
            issue("missing_or_invalid_execution_quantity")
            continue
        if transaction_label not in ("", "체결"):
            issue("execution_transaction_label_unverified")
            continue
        if order_no is None or order_date is None:
            issue("missing_or_invalid_broker_order_identity")
            continue
        if execution_no is None:
            issue("missing_or_invalid_broker_execution_number")
            continue
        execution_date = _date(row.get("ExecDt"))
        if execution_date is None:
            issue("missing_or_invalid_broker_execution_date")
            continue
        raw_time = row.get("ExecDttm")
        wall_time = _wall_time(raw_time)
        if wall_time is None:
            issue("missing_or_invalid_execution_datetime")
            continue
        side = {"1": "sell", "2": "buy"}.get(str(row.get("ExecBnsTpCode") or "").strip())
        if side is None:
            issue("missing_or_invalid_execution_side")
            continue
        symbol = row.get("OvrsDrvtExecIsuCode")
        if not isinstance(symbol, str) or not symbol.strip():
            issue("missing_execution_symbol")
            continue
        price = _decimal(row.get("AbrdFutsExecPrc"))
        if price is None:
            issue("missing_or_invalid_execution_price")
            continue
        executions.append(FuturesExecutionObservation(
            broker_order_no=order_no, broker_order_date=order_date,
            broker_execution_no=execution_no, broker_execution_date=execution_date,
            execution_datetime_raw=raw_time, execution_wall_time=wall_time,
            symbol=symbol.strip(), side=side, quantity=quantity, price=price,
            evidence=evidence,
            source_status=str(row["FutsOrdStatCode"]) if row.get("FutsOrdStatCode") is not None else None,
        ))
    return ParsedFuturesExecutions(tuple(executions), tuple(issues))
