"""Preview the owner-supplied LS NXT limit-order example without network calls.

Running this file never logs in or submits an order. The default values are the
historical LS documentation example, not a recommendation or current quote.
Applications can import build_order() with their authenticated LS instance and
explicit trade parameters. Calling the returned TR's req()/req_async() sends a
live order, so the application must check session, eligibility and pending orders.
"""
from __future__ import annotations

import argparse
import json
import re

from programgarden_finance import CSPAT00601


def build_body(symbol: str, side: str, quantity: int, limit_price: int):
    if not re.fullmatch(r"A?[0-9]{6}", symbol):
        raise ValueError("Use six digits or A followed by six digits")
    if side not in {"buy", "sell"}:
        raise ValueError("Choose buy or sell")
    if type(quantity) is not int or quantity <= 0:
        raise ValueError("Quantity must be a positive integer")
    if type(limit_price) is not int or limit_price <= 0:
        raise ValueError("This stock example requires a positive integer KRW limit price")
    return CSPAT00601.CSPAT00601InBlock1(
        IsuNo=symbol, OrdQty=quantity, OrdPrc=limit_price,
        BnsTpCode="2" if side == "buy" else "1",
        OrdprcPtnCode="00", MgntrnCode="000", LoanDt="",
        OrdCndiTpCode="0", MbrNo="NXT",
    )


def build_order(ls, *, symbol: str, side: str, quantity: int, limit_price: int):
    """Construct a TR using the public SDK facade; this does not send the order."""
    return ls.korea_stock().order().cspat00601(
        build_body(symbol, side, quantity, limit_price)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="A272210")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--limit-price", type=int, default=35000)
    args = parser.parse_args(argv)
    body = build_body(args.symbol, args.side, args.quantity, args.limit_price)
    print(json.dumps({"CSPAT00601InBlock1": body.model_dump()}, indent=2))
    print("Preview only. No broker login or order submission occurred.")


if __name__ == "__main__":
    main()
