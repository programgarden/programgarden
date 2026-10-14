"""Distinguish complete futures reads from defaults, errors and partial pages."""

import math

from programgarden.database.broker_evidence import NO_RESULT_MESSAGE, unverified_response_code

_NO_DATA_TRS = {"CIDBQ01500", "CIDBQ02400"}


def require_complete_rows(response, request, tr, *, paper_trading=False):
    """Validate the observed terminal envelope and return its detail rows.

    00707 is accepted only for an explicitly empty, matching terminal response
    for the two position/pending TRs observed on the paper server. It is not a
    generic success code. Continuation pages remain unavailable in this reader.

    For a paper client only, 02679 with the exact observed empty-result message
    and explicitly empty rows is the same complete empty result on those two
    TRs, mirroring the startup gate. Live clients and other TRs still reject it.
    """
    if response.status_code != 200 or response.error_msg:
        raise ValueError(f"{tr} did not return a complete terminal response")
    code = response.rsp_cd
    accepted = code in {"00000", "00136", "00707"} or (
        paper_trading is True
        and tr in _NO_DATA_TRS
        and code == "02679"
        and not response.block2
        and response.rsp_msg == NO_RESULT_MESSAGE
    )
    if not accepted:
        raise ValueError(unverified_response_code(tr, code, response.rsp_msg))
    if (
        response.header is None
        or response.header.tr_cd not in {tr, "CIDBQ"}
        or response.header.tr_cont != "N"
        or response.header.tr_cont_key
        or "block2" not in response.model_fields_set
    ):
        raise ValueError(f"{tr} did not return a complete terminal response")
    echo = response.block1
    expected = request.model_dump()
    if (
        echo is None
        or not set(expected) <= echo.model_fields_set
        or any(getattr(echo, field) != value for field, value in expected.items())
    ):
        raise ValueError(f"{tr} query echo is missing or mismatched")
    if code == "00707" and (tr not in _NO_DATA_TRS or response.block2):
        raise ValueError(f"{tr} no-data response is inconsistent")
    return response.block2


def require_position_identity(row):
    required = {"IsuCodeVal", "BnsTpCode", "BalQty"}
    if (
        not required <= row.model_fields_set
        or not row.IsuCodeVal.strip()
        or row.BnsTpCode not in {"1", "2"}
        or not math.isfinite(row.BalQty)
        or row.BalQty < 0
    ):
        raise ValueError("CIDBQ01500 position identity or quantity is unavailable")


def require_pending_identity(row):
    required = {
        "OvrsFutsOrdNo",
        "IsuCodeVal",
        "BnsTpCode",
        "OrdQty",
        "ExecQty",
        "UnercQty",
    }
    if (
        not required <= row.model_fields_set
        or not row.OvrsFutsOrdNo.strip()
        or not row.IsuCodeVal.strip()
        or row.BnsTpCode not in {"1", "2"}
        or any(getattr(row, field) < 0 for field in ("OrdQty", "ExecQty", "UnercQty"))
    ):
        raise ValueError("CIDBQ02400 pending order identity or quantity is unavailable")
