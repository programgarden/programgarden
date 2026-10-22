"""Open-source build: the broker startup-evidence skeleton lets a plain success response
pass startup and sends transport failures, continued pages and non-success codes down
the generic error path."""
from types import SimpleNamespace

import pytest

from programgarden.database.broker_evidence import StartupEvidenceUnavailable, checked_body


class _Raw:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def _response(**overrides):
    fields = dict(
        status_code=200, error_msg=None,
        header=SimpleNamespace(tr_cd="TRX01", tr_cont="N", tr_cont_key=""),
        raw_data=_Raw({"TRX01OutBlock": {}, "TRX01OutBlock1": [{"qty": "1"}]}),
        rsp_cd="00000", rsp_msg="ok",
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


async def test_plain_success_response_passes_startup():
    body = await checked_body(_response(), "TRX01")
    assert body == {"TRX01OutBlock": {}, "TRX01OutBlock1": [{"qty": "1"}]}


async def test_transport_failure_uses_generic_error():
    with pytest.raises(StartupEvidenceUnavailable, match="transport_failure"):
        await checked_body(_response(status_code=500), "TRX01")


async def test_continued_page_uses_generic_error():
    header = SimpleNamespace(tr_cd="TRX01", tr_cont="Y", tr_cont_key="next")
    with pytest.raises(StartupEvidenceUnavailable, match="incomplete_continuation"):
        await checked_body(_response(header=header), "TRX01")


async def test_non_success_code_uses_generic_error():
    with pytest.raises(StartupEvidenceUnavailable, match="unverified_response_code"):
        await checked_body(_response(rsp_cd="99999", rsp_msg="error"), "TRX01")
