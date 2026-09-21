"""Strict terminal broker evidence for execution startup.

The observed response checks follow the server startup gate. SDK defaults must
not turn a missing detail block, partial page or rejection into an empty account.
"""

import inspect
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone

_BLOCKS = {
    "t0424": ("t0424OutBlock", "t0424OutBlock1"),
    "t0425": ("t0425OutBlock", "t0425OutBlock1"),
    "COSOQ00201": ("COSOQ00201OutBlock1", "COSOQ00201OutBlock3", "COSOQ00201OutBlock4"),
    "COSAQ00102": ("COSAQ00102OutBlock1", "COSAQ00102OutBlock2", "COSAQ00102OutBlock3"),
    "CIDBQ05300": ("CIDBQ05300OutBlock1", "CIDBQ05300OutBlock2"),
    "CIDBQ02400": ("CIDBQ02400OutBlock1", "CIDBQ02400OutBlock2"),
    "CIDBQ01500": ("CIDBQ01500OutBlock1", "CIDBQ01500OutBlock2"),
}

# These exact short response headers were observed on live read-only probes.
# The body still has to contain the full requested TR's blocks and query echo.
# Do not generalize this to arbitrary prefixes or other transaction families.
_OBSERVED_RESPONSE_CODES = {
    "COSAQ00102": {"COSAQ00102", "COSAQ"},
    "COSOQ00201": {"COSOQ00201", "COSOQ"},
    "CIDBQ01500": {"CIDBQ01500", "CIDBQ"},
    "CIDBQ02400": {"CIDBQ02400", "CIDBQ"},
    "CIDBQ05300": {"CIDBQ05300", "CIDBQ"},
}


class StartupEvidenceUnavailable(RuntimeError):
    """An incomplete response must never authorize execution."""


class StartupQueryDateMismatch(StartupEvidenceUnavailable):
    def __init__(self, business_day):
        super().__init__("COSAQ00102: query_echo_mismatch:OrdDt")
        self.business_day = business_day


async def checked_body(response, tr, request=None):
    """Read original broker blocks so SDK defaults cannot manufacture success."""
    if response.status_code != 200 or response.error_msg:
        raise StartupEvidenceUnavailable(f"{tr}: transport_failure")
    header = response.header
    if (header is None or not {"tr_cd", "tr_cont", "tr_cont_key"} <= header.model_fields_set
            or header.tr_cd not in _OBSERVED_RESPONSE_CODES.get(tr, {tr})
            or header.tr_cont not in {"N", "0"} or header.tr_cont_key.strip()):
        raise StartupEvidenceUnavailable(f"{tr}: incomplete_continuation")
    raw = response.raw_data
    body = raw.json() if raw is not None else None
    if inspect.isawaitable(body):
        body = await body
    if not isinstance(body, dict) or any(name not in body for name in _BLOCKS[tr]):
        raise StartupEvidenceUnavailable(f"{tr}: missing_response_blocks")
    rows = body[_BLOCKS[tr][-1]]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise StartupEvidenceUnavailable(f"{tr}: malformed_detail_rows")
    detail_attr = {"COSOQ00201": "block4", "COSAQ00102": "block3",
                   "CIDBQ01500": "block2", "CIDBQ02400": "block2"}.get(tr)
    if detail_attr is not None:
        parsed = getattr(response, detail_attr, None)
        if (not isinstance(parsed, list) or len(parsed) != len(rows)
                or getattr(response, "parse_warnings", [])):
            raise StartupEvidenceUnavailable(f"{tr}: incomplete_parsed_details")
    for name in _BLOCKS[tr][:-1]:
        if not isinstance(body[name], (dict, list)):
            raise StartupEvidenceUnavailable(f"{tr}: malformed_summary_block")
    row_fields = {
        "t0424": ("expcode", "janqty"), "t0425": ("expcode", "ordrem", "ordno"),
        "COSOQ00201": ("AstkBalQty",), "COSAQ00102": ("OrdNo", "UnercQty"),
        "CIDBQ02400": ("IsuCodeVal", "OvrsFutsOrdNo", "UnercQty"),
        "CIDBQ01500": ("IsuCodeVal", "BnsTpCode", "BalQty"),
    }.get(tr, ())
    for row in rows:
        if any(field not in row or row[field] in (None, "") for field in row_fields):
            raise StartupEvidenceUnavailable(f"{tr}: incomplete_row")
        if tr in {"COSOQ00201", "COSAQ00102"} and not (row.get("ShtnIsuNo") or row.get("IsuNo")):
            raise StartupEvidenceUnavailable(f"{tr}: missing_symbol")
        for field in ("AstkBalQty", "OrdNo", "UnercQty", "janqty", "ordrem", "ordno", "BalQty"):
            if field not in row_fields:
                continue
            try:
                valid = Decimal(str(row[field])).is_finite()
            except InvalidOperation:
                valid = False
            if not valid:
                raise StartupEvidenceUnavailable(f"{tr}: invalid_quantity")
    code = response.rsp_cd
    accepted = code in {"00000", "00136"}
    if tr == "COSOQ00201" and code == "00001":
        accepted = True  # Observed terminal stock balance response, 2026-09-16.
    if tr == "COSAQ00102" and code == "02679":
        echo = body["COSAQ00102OutBlock1"]
        accepted = (not rows and isinstance(echo, dict)
                    and response.rsp_msg == "조회내역이 없습니다."
                    and echo.get("OrdMktCode") == "%"
                    and echo.get("ThdayBnsAppYn") == "1"
                    and echo.get("BnsTpCode") == "0" and echo.get("CrcyCode") == "000")
    elif tr in {"CIDBQ01500", "CIDBQ02400"} and code == "00707":
        accepted = (not rows and response.rsp_msg == "모의투자 조회할 내역(자료)이 없습니다.")
    if not accepted:
        raise StartupEvidenceUnavailable(f"{tr}: unverified_response_code={code}")
    if tr in {"t0424", "t0425"}:
        cursor = "cts_expcode" if tr == "t0424" else "cts_ordno"
        summary = body[_BLOCKS[tr][0]]
        if not isinstance(summary, dict) or cursor not in summary or str(summary[cursor]).strip():
            raise StartupEvidenceUnavailable(f"{tr}: incomplete_continuation")
    if request is not None and tr not in {"t0424", "t0425"}:
        echo = response.block1
        expected = next(iter(request.request_data.body.values()))
        # Some TRs echo only a documented subset of input fields. An explicitly
        # returned field must match; required scope fields cannot be omitted.
        required = {
            "COSAQ00102": {"OrdDt", "OrdMktCode", "ThdayBnsAppYn", "BnsTpCode", "CrcyCode"},
            "COSOQ00201": {"BaseDt", "CrcyCode", "AstkBalTpCode"},
            "CIDBQ05300": {"OvrsAcntTpCode", "CrcyCode"},
            "CIDBQ02400": {"QrySrtDt", "QryEndDt", "ThdayTpCode", "OrdStatCode"},
            "CIDBQ01500": {"AcntTpCode", "BalTpCode", "FcmAcntNo"},
        }[tr]
        if echo is None or not required <= echo.model_fields_set:
            raise StartupEvidenceUnavailable(f"{tr}: missing_query_echo")
        mismatches = set()
        for field in expected.model_fields_set & echo.model_fields_set:
            sent, received = str(getattr(expected, field)), str(getattr(echo, field))
            if tr == "COSAQ00102" and field == "OrdMktCode" and sent == "00" and received == "%":
                continue
            if tr == "CIDBQ01500" and field == "QryDt" and sent == "":
                continue  # The documented current business-day selector.
            if field == "RecCnt":
                continue  # Response record count is not a query filter.
            if sent != received:
                mismatches.add(field)
        if mismatches:
            # LS returned the prior business date after KST midnight. Never use
            # that mismatched result: allow one exact-date confirmation query.
            if tr == "COSAQ00102" and mismatches == {"OrdDt"} and echo.ThdayBnsAppYn == "1":
                today = datetime.now(timezone(timedelta(hours=9)))
                if echo.OrdDt in {today.strftime("%Y%m%d"), (today - timedelta(days=1)).strftime("%Y%m%d")}:
                    raise StartupQueryDateMismatch(echo.OrdDt)
            raise StartupEvidenceUnavailable(f"{tr}: query_echo_mismatch")
    return body
