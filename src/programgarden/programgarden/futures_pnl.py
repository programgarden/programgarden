"""Preserve currency-scoped estimates without inventing workflow accounting.

Current positions and a native gross price-change estimate do not establish
realized PnL, opening capital, workflow ownership, fees or account return.
The legacy workflow/total scalars therefore remain unavailable. Estimates and
the original broker observations remain visible as separate metadata.
"""

from decimal import Decimal, InvalidOperation
from typing import Any


GROSS_BASIS = "estimated_gross_price_change"
WORKFLOW_SCALARS = tuple(
    f"{scope}_{metric}"
    for scope in ("workflow", "other", "total")
    for metric in ("pnl_rate", "pnl_amount", "eval_amount", "buy_amount")
)


def unavailable_workflow_pnl() -> dict[str, Any]:
    return dict.fromkeys(WORKFLOW_SCALARS) | {
        "workflow_positions": [], "other_positions": [],
        "trust_score": 0, "anomaly_count": 0,
    }


def unavailable_account_pnl() -> dict[str, None]:
    return dict.fromkeys(
        [f"account_total_{metric}" for metric in
         ("pnl_rate", "pnl_amount", "eval_amount", "buy_amount")]
        + [f"account_{product}_{metric}" for product in
           ("overseas_stock", "overseas_futures", "korea_stock")
           for metric in ("pnl_rate", "pnl_amount")]
    )


def _finite(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def futures_pnl_metadata(positions: dict[str, Any] | None) -> dict[str, Any]:
    """Group explicit same-basis estimates; never treat missing metadata as USD."""
    buckets: dict[str, dict[str, Any]] = {}
    details: dict[str, dict[str, Any]] = {}
    unavailable = 0
    for symbol, pos in (positions or {}).items():
        currency = pos.get("pnl_currency")
        position_currency = pos.get("currency")
        amount = _finite(pos.get("pnl_amount"))
        eligible = (
            pos.get("pnl_status") == "available"
            and pos.get("pnl_basis") == GROSS_BASIS
            and isinstance(currency, str)
            and len(currency) == 3 and currency.isascii() and currency.isalpha()
            and currency == currency.upper() and amount is not None
            and isinstance(position_currency, str)
            and currency == position_currency.strip().upper()
        )
        if eligible:
            bucket = buckets.setdefault(currency, {
                "currency": currency, "basis": GROSS_BASIS,
                "total_pnl_amount": Decimal(0), "position_count": 0,
            })
            bucket["total_pnl_amount"] += amount
            bucket["position_count"] += 1
        else:
            unavailable += 1
        # Keep only explicit financial evidence and position facts, never an
        # arbitrary broker/context payload or an inferred workflow classification.
        detail = {key: pos.get(key) for key in (
            "quantity", "buy_price", "current_price", "direction",
            "currency", "pnl_currency", "pnl_basis", "pnl_status",
            "pnl_unavailable_reason", "broker_pnl_basis",
        )}
        detail["pnl_amount"] = amount if eligible else None
        detail["broker_pnl_amount"] = _finite(pos.get("broker_pnl_amount"))
        details[symbol] = detail
    known_currencies = set(buckets)
    single_currency = next(iter(known_currencies)) if len(known_currencies) == 1 and not unavailable else None
    return {
        "currency": single_currency,
        "monetary_status": "estimated" if buckets and not unavailable else (
            "partial" if buckets else "unavailable"
        ),
        "monetary_basis": GROSS_BASIS if buckets else None,
        "monetary_unavailable_reason": "workflow_accounting_basis_unverified" if positions is not None
            else "account_positions_unavailable",
        "pnl_by_currency": buckets,
        "monetary_positions": details,
        "unavailable_position_count": unavailable,
    }
