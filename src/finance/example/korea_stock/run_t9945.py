"""Read-only KOSPI/KOSDAQ master example with explicit NXT eligibility.

Use --nxt-only to show only rows with an observed nxt_chk='1'. Eligibility is
not current market-open or fill evidence. No orders are constructed or submitted.
"""
import argparse
from collections import Counter
import json
import os

from dotenv import load_dotenv
from programgarden_finance import LS, t9945


def nxt_status(row) -> str:
    if "nxt_chk" not in row.model_fields_set:
        return "unknown"
    return {"1": "provided", "0": "not_provided"}.get(row.nxt_chk, "unknown")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nxt-only", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    load_dotenv()
    ls = LS()
    if not ls.login(appkey=os.getenv("APPKEY_KOREA"), appsecretkey=os.getenv("APPSECRET_KOREA")):
        raise SystemExit("Domestic broker login failed")
    for market_code in ("1", "2"):
        tr = ls.korea_stock().market().주식마스터조회(t9945.T9945InBlock(gubun=market_code))
        result = tr.req()
        if result.error_msg or result.rsp_cd != "00000":
            raise SystemExit(f"Master query failed: rsp_cd={result.rsp_cd}")
        rows = result.block
        counts = Counter(nxt_status(row) for row in rows)
        selected = [row for row in rows if not args.nxt_only or nxt_status(row) == "provided"]
        print(json.dumps({"market": market_code, "rows": len(rows), "nxt_status": dict(counts),
                          "displayed": [{"symbol": row.shcode, "name": row.hname,
                                         "nxt_status": nxt_status(row)} for row in selected[:args.limit]]},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
