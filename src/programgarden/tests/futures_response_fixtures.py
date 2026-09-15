"""Typed broker envelopes for offline futures regression tests."""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from programgarden_finance import CIDBQ01500, CIDBQ02400, CIDBQ05300


def parsed_response(
    tr, request, rows, *, code="00136", missing_rows=False, continuation=False
):
    module = {
        "CIDBQ01500": CIDBQ01500,
        "CIDBQ02400": CIDBQ02400,
        "CIDBQ05300": CIDBQ05300,
    }[tr]
    cls = getattr(module, "Tr" + tr)
    body = {
        tr + "OutBlock1": request.model_dump(),
        "rsp_cd": code,
        "rsp_msg": "Offline fixture",
    }
    if not missing_rows:
        body[tr + "OutBlock2"] = rows
    header = {
        "Content-Type": "application/json",
        "tr_cd": "CIDBQ",
        "tr_cont": "Y" if continuation else "N",
        "tr_cont_key": "next" if continuation else "",
    }
    return cls._build_response(
        None, SimpleNamespace(status_code=200), body, header, None
    )


def position_request():
    return CIDBQ01500.CIDBQ01500InBlock1(
        RecCnt=1,
        AcntTpCode="1",
        QryDt=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d"),
        BalTpCode="2",
        FcmAcntNo="",
    )
