"""Currency-scoped open workflow valuation, independent of realized trades."""

from dataclasses import asdict, is_dataclass
from decimal import Decimal, InvalidOperation
import re


def workflow_valuation_snapshot(result, account_positions, observed_at, product):
    if product != "overseas_stock" or not isinstance(account_positions, dict):
        return None
    positions = result.get("workflow_positions")
    if not isinstance(positions, list):
        return None
    if positions and result.get("workflow_pnl_rate") is None:
        return None
    groups = {}
    seen = set()
    for item in positions:
        row = asdict(item) if is_dataclass(item) else item
        if not isinstance(row, dict):
            return None
        symbol = row.get("symbol")
        account = account_positions.get(symbol)
        if not isinstance(account, dict) or symbol in seen:
            return None
        seen.add(symbol)
        currency = account.get("currency")
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            return None
        values = {}
        for key in ("quantity", "avg_price", "current_price", "pnl_amount"):
            value = row.get(key)
            if value is None or isinstance(value, bool):
                return None
            try:
                values[key] = Decimal(str(value))
            except InvalidOperation:
                return None
            if not values[key].is_finite() or (key != "pnl_amount" and values[key] <= 0):
                return None
        # Valuation is an estimate from the workflow's own retained cost basis.
        pnl = values["pnl_amount"]
        if abs(pnl - (values["current_price"] - values["avg_price"]) * values["quantity"]) > Decimal("0.0001"):
            return None
        group = groups.setdefault(currency, {"earned": Decimal(0), "lost": Decimal(0), "net": Decimal(0)})
        group["earned"] += max(pnl, Decimal(0))
        group["lost"] += max(-pnl, Decimal(0))
        group["net"] = group["earned"] - group["lost"]
    return {"version": 1, "product": product, "basis": "workflow_open_positions_gross",
            "observed_at": observed_at.isoformat(),
            "groups": [{"currency": currency, **group} for currency, group in sorted(groups.items())]}
