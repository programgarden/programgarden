"""Retain broker valuation amounts separately from tick-derived PnL estimates."""

from decimal import Decimal, InvalidOperation
import re

from ..accno.COSOQ00201.blocks import COSOQ00201Response


def _amount(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() else None
    except InvalidOperation:
        return None


def stock_valuation_snapshot(response, request, observed_at):
    """Require complete, matching broker rows; never recover gross PnL from net."""
    if not isinstance(response, COSOQ00201Response):
        return None
    if (response.status_code != 200 or response.error_msg or response.parse_warnings
            or response.rsp_cd not in {"00000", "00001"} or response.header is None
            # The observed LS response uses the COSOQ family header. Exact
            # COSOQ00201 blocks and the matching request echo still prove scope.
            or response.header.tr_cd not in {"COSOQ00201", "COSOQ"} or not response._valuation_blocks_present
            or response.header.tr_cont != "N" or response.header.tr_cont_key.strip()):
        return None
    echo = response.block1
    if echo is None or any(getattr(echo, name) != getattr(request, name)
                           for name in ("BaseDt", "CrcyCode", "AstkBalTpCode")):
        return None
    groups = {}
    for balance in response.block3:
        if not {"CrcyCode", "FcurrEvalPnlAmt"} <= balance.model_fields_set:
            return None
        currency = balance.CrcyCode.strip().upper()
        net = _amount(balance.FcurrEvalPnlAmt)
        if not re.fullmatch(r"[A-Z]{3}", currency) or currency in groups or net is None:
            return None
        groups[currency] = {"net": net, "earned": Decimal(0), "lost": Decimal(0)}
    if not groups or "block4" not in response.model_fields_set:
        return None
    seen = set()
    for position in response.block4:
        if not {"AstkBalQty", "CrcyCode", "FcurrEvalPnlAmt"} <= position.model_fields_set:
            return None
        quantity = _amount(position.AstkBalQty)
        pnl = _amount(position.FcurrEvalPnlAmt)
        currency = position.CrcyCode.strip().upper()
        symbol = position.ShtnIsuNo.strip() or position.IsuNo.strip()
        identity = (currency, symbol, position.FcurrMktCode, position.AstkBalTpCode)
        if (quantity is None or quantity < 0 or pnl is None or currency not in groups
                or not symbol or identity in seen):
            return None
        seen.add(identity)
        if quantity == 0:
            if pnl != 0:
                return None
            continue
        groups[currency]["earned"] += max(pnl, Decimal(0))
        groups[currency]["lost"] += max(-pnl, Decimal(0))
    for group in groups.values():
        net = group["earned"] - group["lost"]
        # The supplied LS amount specification has four decimal places.
        if abs(net - group["net"]) > Decimal("0.0001"):
            return None
        group["net"] = net
    return {"version": 1, "product": "overseas_stock", "basis": "broker_open_positions",
            "observed_at": observed_at.isoformat(), "source": "COSOQ00201",
            "groups": [{"currency": currency, **group} for currency, group in sorted(groups.items())]}
