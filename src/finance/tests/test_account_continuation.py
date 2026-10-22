"""Header-only continuation for six account TRs (SPEC K1), offline.

The LS guide gives these TRs the common ``tr_cont``/``tr_cont_key`` headers and
no body cursor. ``occurs_req`` re-sends the same body with ``tr_cont="Y"`` and
the previous key, keeps pages separate, keeps a failed page as the last
element and stops on a blank/repeated key or the page limit. Real SDK request
and response models are used; HTTP is mocked and sockets are denied.
"""

from dataclasses import dataclass
import socket
from typing import Any, Callable, Dict
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import requests

from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.tr_base import OccursReqAbstract
from programgarden_finance.ls.tr_helpers import DEFAULT_OCCURS_MAX_PAGES, occurs_complete
from programgarden_finance.ls.korea_stock.accno import CSPAQ13700 as cspaq13700
from programgarden_finance.ls.overseas_stock.accno import COSAQ00102 as cosaq00102
from programgarden_finance.ls.overseas_stock.accno import COSOQ00201 as cosoq00201
from programgarden_finance.ls.overseas_futureoption.accno import CIDBQ01500 as cidbq01500
from programgarden_finance.ls.overseas_futureoption.accno import CIDBQ01800 as cidbq01800
from programgarden_finance.ls.overseas_futureoption.accno import CIDBQ02400 as cidbq02400


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("continuation tests must remain offline")

    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    yield
    assert not attempts


@dataclass(frozen=True)
class Case:
    code: str
    module: Any
    url: str
    in_block: Callable[[], Any]
    detail_block: str     # response key of the repeated detail rows
    detail_attr: str      # parsed attribute holding those rows
    marker: str           # row field used to tell pages apart
    header_tr_cd: str     # tr_cd LS echoes in the response header

    def make_tr(self, **options):
        request_cls = getattr(self.module, f"{self.code}Request")
        tr_cls = getattr(self.module, f"Tr{self.code}")
        request = request_cls(
            body={f"{self.code}InBlock1": self.in_block()},
            options=SetupOptions(
                rate_limit_count=100, rate_limit_seconds=1, on_rate_limit="wait",
                rate_limit_key="", transient_retries=0, **options,
            ),
        )
        return tr_cls(request)

    def payload(self, marker_value) -> Dict[str, Any]:
        return {
            "rsp_cd": "00136",
            "rsp_msg": "Offline fixture",
            f"{self.code}OutBlock1": {},
            self.detail_block: [{self.marker: marker_value}],
        }

    def rows(self, response):
        return [getattr(row, self.marker) for row in getattr(response, self.detail_attr)]


CASES = [
    Case("CSPAQ13700", cspaq13700, URLS.KOREA_STOCK_ACCNO_URL,
         lambda: cspaq13700.CSPAQ13700InBlock1(),
         "CSPAQ13700OutBlock3", "block3", "OrdNo", "CSPAQ13700"),
    Case("COSAQ00102", cosaq00102, URLS.ACCNO_URL,
         lambda: cosaq00102.COSAQ00102InBlock1(OrdDt="20261015"),
         "COSAQ00102OutBlock3", "block3", "OrdNo", "COSAQ00102"),
    Case("COSOQ00201", cosoq00201, URLS.ACCNO_URL,
         lambda: cosoq00201.COSOQ00201InBlock1(),
         "COSOQ00201OutBlock4", "block4", "ShtnIsuNo", "COSOQ00201"),
    Case("CIDBQ01500", cidbq01500, URLS.FO_ACCNO_URL,
         lambda: cidbq01500.CIDBQ01500InBlock1(),
         "CIDBQ01500OutBlock2", "block2", "IsuCodeVal", "CIDBQ"),
    Case("CIDBQ01800", cidbq01800, URLS.FO_ACCNO_URL,
         lambda: cidbq01800.CIDBQ01800InBlock1(IsuCodeVal="", OrdDt="20261015"),
         "CIDBQ01800OutBlock2", "block2", "IsuCodeVal", "CIDBQ"),
    Case("CIDBQ02400", cidbq02400, URLS.FO_ACCNO_URL,
         lambda: cidbq02400.CIDBQ02400InBlock1(
             IsuCodeVal="", QrySrtDt="", QryEndDt="", ThdayTpCode="1", OrdStatCode="0",
             BnsTpCode="0", QryTpCode="1", OrdPtnCode="00", OvrsDrvtFnoTpCode="A"),
         "CIDBQ02400OutBlock2", "block2", "IsuCodeVal", "CIDBQ"),
]
IDS = [case.code for case in CASES]


def marker_values(case):
    """Distinct per-page row values of the right type for the marker field."""
    return (101, 102, 103) if case.marker == "OrdNo" else ("PAGE1", "PAGE2", "PAGE3")


def headers(case, cont="N", key=""):
    return {"Content-Type": "application/json; charset=utf-8", "tr_cd": case.header_tr_cd,
            "tr_cont": cont, "tr_cont_key": key}


def sync_wire(case, status=200, payload=None, cont="N", key=""):
    wire = Mock(spec=requests.Response, status_code=status, headers=headers(case, cont, key))
    wire.json.return_value = payload
    return wire


def install_sync(monkeypatch, wires):
    post = Mock(side_effect=list(wires))
    monkeypatch.setattr(requests, "post", post)
    return post


def sent(post_call):
    return post_call.kwargs["headers"], post_call.kwargs["json"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_tr_declares_continuation_capability(case):
    tr = case.make_tr()
    assert isinstance(tr, OccursReqAbstract)
    assert callable(tr.occurs_req) and callable(tr.occurs_req_async)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_two_pages_resend_same_body_with_header_key(monkeypatch, case):
    m1, m2, _ = marker_values(case)
    post = install_sync(monkeypatch, [
        sync_wire(case, payload=case.payload(m1), cont="Y", key="KEY-1"),
        sync_wire(case, payload=case.payload(m2), cont="N", key=""),
    ])
    tr = case.make_tr()
    statuses = []
    pages = tr.occurs_req(callback=lambda resp, status: statuses.append(status), delay=0)

    assert post.call_count == 2
    (h1, b1), (h2, b2) = sent(post.call_args_list[0]), sent(post.call_args_list[1])
    assert post.call_args_list[1].kwargs["url"] == case.url
    assert (h1["tr_cd"], h1["tr_cont"], h1["tr_cont_key"]) == (case.code, "N", "")
    assert (h2["tr_cd"], h2["tr_cont"], h2["tr_cont_key"]) == (case.code, "Y", "KEY-1")
    # The guide defines no body cursor for these TRs: the body is re-sent unchanged.
    assert b1 == b2
    # Pages stay separate; rows are not merged.
    assert [case.rows(page) for page in pages] == [[m1], [m2]]
    assert occurs_complete(pages)
    assert statuses == [RequestStatus.REQUEST, RequestStatus.RESPONSE, RequestStatus.OCCURS_REQUEST,
                        RequestStatus.RESPONSE, RequestStatus.COMPLETE, RequestStatus.CLOSE]
    # The request header is restored so a later req() starts from page one.
    assert (tr.request_data.header.tr_cont, tr.request_data.header.tr_cont_key) == ("N", "")


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_failed_second_page_is_kept_and_marks_the_walk_incomplete(monkeypatch, case):
    m1, _, _ = marker_values(case)
    post = install_sync(monkeypatch, [
        sync_wire(case, payload=case.payload(m1), cont="Y", key="KEY-1"),
        sync_wire(case, status=500, payload={"rsp_cd": "IGW00201", "rsp_msg": "호출 거래건수를 초과하였습니다."}),
    ])
    statuses = []
    pages = case.make_tr().occurs_req(callback=lambda resp, status: statuses.append(status), delay=0)

    # transient_retries=0: the failed page is not retried by the SDK.
    assert post.call_count == 2
    assert len(pages) == 2
    assert case.rows(pages[0]) == [m1]
    assert pages[-1].error_msg and "HTTP 500" in pages[-1].error_msg
    assert not occurs_complete(pages)
    assert RequestStatus.FAIL in statuses


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_repeated_key_stops_without_looping(monkeypatch, case):
    m1, m2, _ = marker_values(case)
    post = install_sync(monkeypatch, [
        sync_wire(case, payload=case.payload(m1), cont="Y", key="KEY-1"),
        sync_wire(case, payload=case.payload(m2), cont="Y", key="KEY-1"),
    ])
    pages = case.make_tr().occurs_req(delay=0)
    assert post.call_count == 2
    assert [case.rows(page) for page in pages] == [[m1], [m2]]
    assert pages[-1].header.tr_cont == "Y"
    assert not occurs_complete(pages)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_blank_key_is_not_sent_as_a_continuation(monkeypatch, case):
    m1, _, _ = marker_values(case)
    post = install_sync(monkeypatch, [sync_wire(case, payload=case.payload(m1), cont="Y", key="  ")])
    pages = case.make_tr().occurs_req(delay=0)
    assert post.call_count == 1
    assert not occurs_complete(pages)


@pytest.mark.parametrize("case", CASES[:1] + CASES[3:4], ids=["CSPAQ13700", "CIDBQ01500"])
def test_page_limit_reports_incomplete(monkeypatch, case):
    m1, m2, m3 = marker_values(case)
    post = install_sync(monkeypatch, [
        sync_wire(case, payload=case.payload(m1), cont="Y", key="KEY-1"),
        sync_wire(case, payload=case.payload(m2), cont="Y", key="KEY-2"),
        sync_wire(case, payload=case.payload(m3), cont="N"),
    ])
    pages = case.make_tr().occurs_req(delay=0, max_pages=2)
    assert post.call_count == 2
    assert not occurs_complete(pages)
    with pytest.raises(ValueError):
        case.make_tr().occurs_req(delay=0, max_pages=0)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_single_terminal_page_is_complete(monkeypatch, case):
    m1, _, _ = marker_values(case)
    post = install_sync(monkeypatch, [sync_wire(case, payload=case.payload(m1), cont="N", key="0")])
    pages = case.make_tr().occurs_req(delay=0)
    assert post.call_count == 1 and occurs_complete(pages)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_failed_first_page_is_returned_not_hidden(monkeypatch, case):
    install_sync(monkeypatch, [sync_wire(case, status=500, payload={"rsp_cd": "IGW40013", "rsp_msg": "x"})])
    pages = case.make_tr().occurs_req(delay=0)
    assert len(pages) == 1 and pages[0].error_msg
    assert not occurs_complete(pages)


def test_occurs_complete_rules():
    ok = Mock(error_msg=None, header=Mock(tr_cont="N"))
    more = Mock(error_msg=None, header=Mock(tr_cont="Y"))
    empty_success = Mock(error_msg="", header=Mock(tr_cont="0"))
    failed = Mock(error_msg="HTTP 500", header=None)
    headerless = Mock(error_msg=None, header=None)
    assert occurs_complete([ok]) and occurs_complete([more, empty_success])
    assert not occurs_complete([])
    assert not occurs_complete([more])
    assert not occurs_complete([more, failed])
    assert not occurs_complete([headerless])
    assert DEFAULT_OCCURS_MAX_PAGES == 100


def async_session(case, pages):
    """aiohttp session mock returning the given (status, payload, cont, key) pages in order."""
    contexts = []
    for status, payload, cont, key in pages:
        wire = MagicMock(status=status, headers=headers(case, cont, key))
        wire.json = AsyncMock(return_value=payload)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=wire)
        context.__aexit__ = AsyncMock(return_value=False)
        contexts.append(context)
    session = MagicMock()
    session.post.side_effect = contexts
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_async_two_pages_share_one_session(monkeypatch, case):
    m1, m2, _ = marker_values(case)
    session = async_session(case, [(200, case.payload(m1), "Y", "KEY-1"), (200, case.payload(m2), "N", "")])
    factory = Mock(return_value=session)
    monkeypatch.setattr("aiohttp.ClientSession", factory)
    tr = case.make_tr()
    pages = await tr.occurs_req_async(delay=0)

    assert factory.call_count == 1 and session.post.call_count == 2
    first, second = session.post.call_args_list
    assert (first.kwargs["headers"]["tr_cont"], first.kwargs["headers"]["tr_cont_key"]) == ("N", "")
    assert (second.kwargs["headers"]["tr_cont"], second.kwargs["headers"]["tr_cont_key"]) == ("Y", "KEY-1")
    assert first.kwargs["json"] == second.kwargs["json"]
    assert [case.rows(page) for page in pages] == [[m1], [m2]]
    assert occurs_complete(pages)
    assert (tr.request_data.header.tr_cont, tr.request_data.header.tr_cont_key) == ("N", "")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_async_failed_page_is_kept(monkeypatch, case):
    m1, _, _ = marker_values(case)
    session = async_session(case, [(200, case.payload(m1), "Y", "KEY-1"),
                                   (500, {"rsp_cd": "IGW00201", "rsp_msg": "limit"}, "N", "")])
    monkeypatch.setattr("aiohttp.ClientSession", Mock(return_value=session))
    pages = await case.make_tr().occurs_req_async(delay=0)
    assert session.post.call_count == 2
    assert len(pages) == 2 and pages[-1].error_msg
    assert not occurs_complete(pages)
