"""Distinguish complete futures reads from defaults, errors and partial pages."""

import math


def require_complete_rows(response, request, tr):
    """Validate the observed terminal envelope and return its detail rows.

    00707 is accepted only for an explicitly empty, matching terminal response
    for the two position/pending TRs observed on the paper server. It is not a
    generic success code. Continuation pages remain unavailable in this reader.
    """
    if (
        response.status_code != 200
        or response.error_msg
        or response.rsp_cd not in {"00000", "00136", "00707"}
        or response.header is None
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
    if response.rsp_cd == "00707" and (
        tr not in {"CIDBQ01500", "CIDBQ02400"} or response.block2
    ):
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
