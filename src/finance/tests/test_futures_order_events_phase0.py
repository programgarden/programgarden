"""Overseas futures TC1/TC2/TC3 frames and CIDBQ01800 rows captured on LS paper (2026-10-15).

Fixture: ``fixtures/tc_frames_paper_futures_20261015.json`` — the frames and
rows as LS sent them, with the login id and account number replaced by
placeholders. Nothing in the fixture is synthesised.

What the capture showed (and these tests pin):
- TC2 sends ``user_id`` where the guide says ``userid``; with ``userid``
  required, every TC2 frame failed validation and listeners got ``body=None``.
- TC2 cancel confirmations carry ``ordr_typ_cd ""``.
- TC1 sends ``xrc_rsv_tcp_code`` where the guide says ``xrc_rsv_tp_code``.
- CIDBQ01800 order numbers are zero-padded (``"0000000027"``) while TC frames
  and order TRs say ``"27"``.
"""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from websockets.asyncio.server import serve

from programgarden_finance.ls.overseas_futureoption.accno.CIDBQ01800.blocks import (
    CIDBQ01800OutBlock2,
    CIDBQ01800Response,
)
from programgarden_finance.ls.overseas_futureoption.extension.execution_history import normalize_broker_identity
from programgarden_finance.ls.overseas_futureoption.extension.tracker import FuturesAccountTracker
from programgarden_finance.ls.overseas_futureoption.real import Real as FuturesReal
from programgarden_finance.ls.overseas_futureoption.real.TC1.blocks import TC1RealResponseBody
from programgarden_finance.ls.overseas_futureoption.real.TC2.blocks import TC2RealResponseBody
from programgarden_finance.ls.overseas_futureoption.real.TC3.blocks import TC3RealResponseBody
from programgarden_finance.ls.token_manager import TokenManager

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "tc_frames_paper_futures_20261015.json").read_text(encoding="utf-8"))
MODELS = {"TC1": TC1RealResponseBody, "TC2": TC2RealResponseBody, "TC3": TC3RealResponseBody}


def frames(code=None, service=None, ccd=None):
    out = [item["frame"] for item in FIXTURE["tc_frames"]]
    if code:
        out = [f for f in out if f["header"]["tr_cd"] == code]
    if service:
        out = [f for f in out if f["body"]["svc_id"] == service]
    if ccd:
        out = [f for f in out if f["body"]["ordr_ccd"] == ccd]
    return out


def test_fixture_is_redacted():
    text = json.dumps(FIXTURE, ensure_ascii=False)
    assert '"masked"' not in text
    for frame in frames():
        body = frame["body"]
        assert body["ac_no"] == body["key"] == "12345678901"
        for name in ("user", "userid", "user_id"):
            assert body.get(name, "TESTUSR1") == "TESTUSR1"


@pytest.mark.parametrize("frame", frames(), ids=lambda f: f"{f['header']['tr_cd']}-{f['body']['svc_id']}-{f['body']['ordr_no']}")
def test_every_captured_frame_validates(frame):
    body = MODELS[frame["header"]["tr_cd"]].model_validate(frame["body"])
    assert body.svc_id == frame["body"]["svc_id"]
    assert body.ordr_no == frame["body"]["ordr_no"]


def test_tc2_reads_user_id_and_keeps_the_guide_name():
    modify = frames("TC2", "HO02", "2")[0]["body"]
    assert "user_id" in modify and "userid" not in modify  # as LS sent it
    assert TC2RealResponseBody.model_validate(modify).userid == "TESTUSR1"
    guide = {k: v for k, v in modify.items() if k != "user_id"} | {"userid": "GUIDEUSR"}
    assert TC2RealResponseBody.model_validate(guide).userid == "GUIDEUSR"
    absent = {k: v for k, v in modify.items() if k != "user_id"}
    assert TC2RealResponseBody.model_validate(absent).userid == ""


def test_tc2_modify_and_cancel_confirmations_link_by_original_number():
    modify_35, modify_38 = (TC2RealResponseBody.model_validate(f["body"]) for f in frames("TC2", "HO02", "2"))
    assert (modify_35.ordr_no, modify_35.orgn_ordr_no, modify_35.mthr_ordr_no, modify_35.cnfr_q) == ("35", "27", "27", "2")
    assert (modify_38.ordr_no, modify_38.orgn_ordr_no, modify_38.mthr_ordr_no, modify_38.cnfr_q) == ("38", "35", "27", "1")
    cancel_40, cancel_41 = (TC2RealResponseBody.model_validate(f["body"]) for f in frames("TC2", "HO02", "3"))
    # A cancel gets its own number; the cancelled order is orgn_ordr_no.
    assert (cancel_40.ordr_no, cancel_40.orgn_ordr_no, cancel_40.cnfr_q, cancel_40.ordr_typ_cd) == ("40", "38", "1", "")
    assert (cancel_41.ordr_no, cancel_41.orgn_ordr_no, cancel_41.cnfr_q, cancel_41.ordr_typ_cd) == ("41", "35", "1", "")


def test_no_tc2_for_new_orders():
    new_orders = {f["body"]["ordr_no"] for f in frames("TC1", ccd="1")}
    assert new_orders == {"27", "614", "615"}
    assert not [f for f in frames("TC2") if f["body"]["ordr_no"] in new_orders]


def test_side_code_follows_the_guide():
    # Guide apis[30] TC1/TC2/TC3 s_b_ccd: 1 = 매도 (sell), 2 = 매수 (buy).
    # 27/35/38/40/41/614 were buys (BnsTpCode "2"); 615 was the closing sell (BnsTpCode "1").
    for frame in frames():
        expected = "1" if frame["body"]["ordr_no"] == "615" else "2"
        assert frame["body"]["s_b_ccd"] == expected


def test_tc1_reads_the_observed_exercise_reservation_spelling():
    body = frames("TC1")[0]["body"]
    assert body["xrc_rsv_tcp_code"] == "0" and "xrc_rsv_tp_code" not in body
    assert TC1RealResponseBody.model_validate(body).xrc_rsv_tp_code == "0"
    guide = {k: v for k, v in body.items() if k != "xrc_rsv_tcp_code"} | {"xrc_rsv_tp_code": "1"}
    assert TC1RealResponseBody.model_validate(guide).xrc_rsv_tp_code == "1"
    absent = {k: v for k, v in body.items() if k != "xrc_rsv_tcp_code"}
    assert TC1RealResponseBody.model_validate(absent).xrc_rsv_tp_code == ""


# ---------------------------------------------------------------------------
# End to end: the SDK receive loop hands listeners parsed bodies
# ---------------------------------------------------------------------------

class _ReplayServer:
    """Sends the captured account ack and frames once the client registers TC1."""

    def __init__(self, payloads):
        self.payloads = payloads
        self.received = []
        self._server = None
        self.port = None

    async def _handle(self, ws):
        try:
            async for raw in ws:
                message = json.loads(raw)
                self.received.append(message)
                if message["header"]["tr_type"] == "1":
                    for payload in self.payloads:
                        await ws.send(json.dumps(payload, ensure_ascii=False))
        except Exception:
            return

    async def __aenter__(self):
        self._server = await serve(self._handle, "localhost", 0)
        self.port = next(iter(self._server.sockets)).getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()


@pytest.mark.asyncio
async def test_listeners_receive_parsed_tc2_bodies_over_the_socket():
    ack = next(a["frame"] for a in FIXTURE["acks"] if a["frame"]["header"]["tr_type"] == "1")
    payloads = [ack] + frames("TC1", ccd="3") + frames("TC2")
    async with _ReplayServer(payloads) as server:
        tm = TokenManager()
        tm.access_token = "stub-access-token"
        tm.wss_url = f"ws://localhost:{server.port}"
        real = FuturesReal(token_manager=tm, max_backoff=1.0)
        got = {"TC1": [], "TC2": []}
        try:
            await real.connect(timeout=5.0)
            real.TC1().on_tc1_message(got["TC1"].append)
            real.TC2().on_tc2_message(got["TC2"].append)
            deadline = asyncio.get_running_loop().time() + 5
            while len(got["TC2"]) < 4 and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.02)
        finally:
            await real.close(force=True)
    assert server.received[0]["body"] == {"tr_cd": "TC1", "tr_key": ""}
    assert [r.error_msg for r in got["TC2"]] == [None] * 4
    assert [(r.body.ordr_no, r.body.orgn_ordr_no, r.body.ordr_ccd) for r in got["TC2"]] == [
        ("35", "27", "2"), ("38", "35", "2"), ("40", "38", "3"), ("41", "35", "3")]
    assert all(r.body is not None and r.body.xrc_rsv_tp_code == "0" for r in got["TC1"])


# ---------------------------------------------------------------------------
# CIDBQ01800: zero-padded order numbers
# ---------------------------------------------------------------------------

def _snapshot(label_start):
    return next(s for s in FIXTURE["cidbq01800"] if s["label"].startswith(label_start))


def test_cidbq01800_rows_keep_zero_padded_numbers_that_match_tc_numbers_by_value():
    rows = [CIDBQ01800OutBlock2.model_validate(row) for row in _snapshot("end of run")["rows"]]
    assert [r.OvrsFutsOrdNo for r in rows] == ["0000000027", "0000000035", "0000000038", "0000000040", "0000000041", "0000000614", "0000000615"]
    assert rows[0].OvrsFutsOrgOrdNo == "0000000000"
    tc_numbers = {f["body"]["ordr_no"] for f in frames()}
    assert {normalize_broker_identity(r.OvrsFutsOrdNo) for r in rows} == tc_numbers
    assert normalize_broker_identity(rows[0].OvrsFutsOrgOrdNo) is None


@pytest.mark.asyncio
async def test_tracker_open_orders_use_cidbq01800_fields_and_integer_order_numbers():
    snapshot = _snapshot("after modify")
    response = CIDBQ01800Response(
        block2=[CIDBQ01800OutBlock2.model_validate(row) for row in snapshot["rows"]],
        rsp_cd=snapshot["rsp_cd"], rsp_msg=snapshot["rsp_msg"],
    )
    accno = SimpleNamespace(CIDBQ01800=lambda body: SimpleNamespace(req_async=AsyncMock(return_value=response)))
    tracker = FuturesAccountTracker(accno, None)
    tracker._spec_manager.get_spec = lambda symbol: SimpleNamespace(exchange_code="HKEX") if symbol == "HMHV26" else None
    await tracker._fetch_open_orders()
    orders = tracker.get_open_orders()
    # 27 was fully moved to 35 (UnercQty 0) and is not open; 35 and 38 each have 1 lot.
    assert sorted(orders) == ["35", "38"]
    o35, o38 = orders["35"], orders["38"]
    assert (o35.symbol, o35.exchange_code, o35.is_long, o35.order_type) == ("HMHV26", "HKEX", True, "2")
    assert (o35.order_qty, o35.remaining_qty, str(o35.order_price)) == (2, 1, "22990.0")
    assert (o38.order_qty, o38.remaining_qty, str(o38.order_price), o38.order_time) == (1, 1, "22980.0", "072226113")
    assert tracker._last_errors.get("open_orders") is None


@pytest.mark.asyncio
async def test_tracker_open_orders_empty_when_nothing_is_working():
    snapshot = _snapshot("end of run")
    response = CIDBQ01800Response(
        block2=[CIDBQ01800OutBlock2.model_validate(row) for row in snapshot["rows"]],
        rsp_cd=snapshot["rsp_cd"], rsp_msg=snapshot["rsp_msg"],
    )
    accno = SimpleNamespace(CIDBQ01800=lambda body: SimpleNamespace(req_async=AsyncMock(return_value=response)))
    tracker = FuturesAccountTracker(accno, None)
    tracker._spec_manager.get_spec = lambda symbol: None
    tracker._open_orders["stale"] = object()
    await tracker._fetch_open_orders()
    assert tracker.get_open_orders() == {}
