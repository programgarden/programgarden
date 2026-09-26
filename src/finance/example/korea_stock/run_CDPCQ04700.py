"""One read-only account-history request with explicit scope and private evidence.

Reuse a private copy of an existing token; never issue or refresh one here.
No order, transfer, automatic pagination or request retry is performed. The
operator must coordinate the shared app key's one-request-per-second limit.
The route group does not establish overseas/USD coverage. See
../../docs/cdpcq04700_contract.md before interpreting an observed amount.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import stat
from zoneinfo import ZoneInfo

import requests

from programgarden_finance import CDPCQ04700
from programgarden_finance.ls.config import URLS


def build_body(start: str, end: str, query_mode: str, asset_class: str):
    if query_mode not in {"0", "1", "2", "3", "4", "9"}:
        raise ValueError("Unsupported query mode")
    if asset_class not in {"00", "01", "02", "03", "04", "05", "06"}:
        raise ValueError("Unsupported asset class")
    for value in (start, end):
        if len(value) != 8 or not value.isdigit():
            raise ValueError("Dates must use YYYYMMDD")
        datetime.strptime(value, "%Y%m%d")
    if start > end:
        raise ValueError("Query end must not precede start")
    return CDPCQ04700.CDPCQ04700InBlock1(
        RecCnt=1, QryTp=query_mode, QrySrtDt=start, QryEndDt=end,
        SrtNo=0, PdptnCode="01", IsuLgclssCode=asset_class, IsuNo="",
    )


def load_token(path: Path) -> str:
    """Read an explicit private token file without a credential/token issuer."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise ValueError("Token file must be a private regular file (0600)")
        payload = json.load(source)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise ValueError("Token file must contain an access_token")
    expiry = datetime.fromisoformat(payload["expires_at"])
    if expiry.tzinfo is None or (expiry - datetime.now(timezone.utc)).total_seconds() < 60:
        raise ValueError("Existing token is expired or too close to expiry; stop")
    return token


def main():
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default=today)
    parser.add_argument("--end-date", default=today)
    parser.add_argument("--query-mode", choices=["0", "1", "2", "3", "4", "9"], default="1")
    parser.add_argument("--asset-class", choices=["00", "01", "02", "03", "04", "05", "06"], default="00")
    parser.add_argument("--phase", choices=["before", "after"], default="before")
    parser.add_argument("--output", type=Path, help="New private JSON file; contains account data")
    parser.add_argument("--token-file", type=Path, help="Private JSON with access_token and timezone-aware expires_at")
    parser.add_argument("--dry-run", action="store_true", help="Print the request scope without any API call")
    args = parser.parse_args()
    body = build_body(args.start_date, args.end_date, args.query_mode, args.asset_class)
    # Legacy SDK AcntNo/Pwd inputs are absent from the reviewed REST table.
    request = body.model_dump(exclude={"AcntNo", "Pwd"})
    if args.dry_run:
        print(json.dumps({"tr": "CDPCQ04700", "request": request}))
        return
    if args.output is None:
        parser.error("--output is required for a private response capture")

    if args.token_file is None:
        parser.error("--token-file is required; this example never issues tokens")
    token = load_token(args.token_file)
    # Refuse an existing path/symlink before issuing even a read-only request.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    logging.basicConfig(level=logging.CRITICAL)
    with os.fdopen(fd, "w") as output:
        captured = {"phase": args.phase, "tr": "CDPCQ04700", "request": request,
                    "started_at": datetime.now(timezone.utc).isoformat()}
        # GenericTR.req() has automatic transient/token recovery. Use a single
        # direct transport attempt here so a rejected probe cannot be retried.
        try:
            with requests.Session() as session:
                response = session.post(
                    URLS.KOREA_STOCK_ACCNO_URL,
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json; charset=utf-8",
                             "tr_cd": "CDPCQ04700", "tr_cont": "N", "tr_cont_key": ""},
                    json={"CDPCQ04700InBlock1": request},
                    timeout=10, allow_redirects=False,
                )
            captured.update({"http_status": response.status_code,
                             "headers": {str(k).lower(): v for k, v in response.headers.items()
                                         if str(k).lower() in {"tr_cd", "tr_cont", "tr_cont_key"}}})
            try:
                raw = response.json()
            except ValueError:
                raw = None
                captured["raw_text"] = response.text
                captured["parse_error"] = "Non-JSON response"
            captured["raw_payload"] = raw
            if isinstance(raw, dict):
                tr = CDPCQ04700.TrCDPCQ04700(CDPCQ04700.CDPCQ04700Request(
                    body={"CDPCQ04700InBlock1": body}))
                parsed = tr._build_response(response, raw, None, None)
                captured["parse_error"] = parsed.error_msg
            elif raw is not None:
                captured["parse_error"] = "Non-object JSON response"
        except requests.RequestException as exc:
            # Exception text may contain request metadata; retain its class only.
            captured["transport_error"] = type(exc).__name__
        captured["observed_at"] = datetime.now(timezone.utc).isoformat()
        json.dump(captured, output, ensure_ascii=False, indent=2)
        output.write("\n")
    # Neither account identifiers, monetary values nor raw messages enter logs.
    print(json.dumps({"capture": str(args.output), "http_status": captured.get("http_status"),
                      "parse_error": bool(captured.get("parse_error")),
                      "transport_error": captured.get("transport_error")}))


if __name__ == "__main__":
    main()
