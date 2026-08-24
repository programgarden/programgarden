"""COSOQ00201 소수점(fractional) 잔고 회귀 테스트.

prod 2026-08-24 실측 재현: LS 가 소수점 잔고(AstkBalTpCode='20')를
'0.847972' 같은 소수 문자열로 반환하면, 종전 int 타입은 pydantic
ValidationError 를 던져 정상 종목까지 포함한 잔고 응답 전체를 유실시켰다.

기존 test_account_balance.py 는 MagicMock 으로 block 을 만들어 pydantic
검증을 한 번도 타지 않았다 — 여기서는 실제 모델/실제 파서를 태운다.
"""
import types

import pytest

from programgarden_finance.ls.overseas_stock.accno.COSOQ00201 import TrCOSOQ00201
from programgarden_finance.ls.overseas_stock.accno.COSOQ00201.blocks import (
    COSOQ00201OutBlock4,
)
from programgarden_finance.ls.tr_helpers import ResponseParseException
from programgarden_finance.ls.overseas_stock.extension.tracker import (
    StockAccountTracker,
)


def _fractional_row(symbol: str = "IBM", qty: str = "0.847972") -> dict:
    """prod 실측 모양의 소수점 잔고 행 (수량이 소수 문자열로 온다)."""
    return {
        "ShtnIsuNo": symbol,
        "AstkBalTpCode": "20",
        "AstkBalQty": qty,
        "AstkSellAbleQty": qty,
    }


def _integer_row(symbol: str = "SOXL", qty: int = 16) -> dict:
    return {
        "ShtnIsuNo": symbol,
        "AstkBalTpCode": "10",
        "AstkBalQty": qty,
        "AstkSellAbleQty": qty,
    }


def _build(resp_json: dict, exc: Exception = None):
    """_build_response 는 self 를 쓰지 않는다 — 인스턴스 없이 직접 호출."""
    return TrCOSOQ00201._build_response(None, None, resp_json, None, exc)


class TestFractionalBalanceParsing:
    def test_fractional_string_parses_as_float(self):
        block = COSOQ00201OutBlock4.model_validate(_fractional_row())
        assert block.AstkBalQty == pytest.approx(0.847972)
        assert block.AstkSellAbleQty == pytest.approx(0.847972)

    def test_prod_regression_mixed_rows_all_survive(self):
        """신고 재현: IBM 0.847972주(무관 종목) + SOXL 16주 — 전체가 살아야 한다."""
        resp = _build({
            "rsp_cd": "00000",
            "rsp_msg": "정상",
            "COSOQ00201OutBlock4": [_integer_row(), _fractional_row()],
        })
        assert resp.error_msg is None
        assert len(resp.block4) == 2
        by_symbol = {b.ShtnIsuNo: b for b in resp.block4}
        assert by_symbol["SOXL"].AstkBalQty == 16
        assert by_symbol["IBM"].AstkBalQty == pytest.approx(0.847972)

    def test_bad_row_skipped_survivors_kept(self):
        """불량 행 1개가 나머지를 죽이지 않는다 (행 단위 파싱)."""
        resp = _build({
            "rsp_cd": "00000",
            "COSOQ00201OutBlock4": [
                _integer_row(),
                {"ShtnIsuNo": "BAD", "AstkBalQty": "not-a-number"},
            ],
        })
        assert resp.error_msg is None
        assert len(resp.block4) == 1
        assert resp.block4[0].ShtnIsuNo == "SOXL"

    def test_all_rows_bad_sets_error(self):
        """블록 전멸은 빈 잔고가 아니라 에러다 (조용한 오답 금지)."""
        resp = _build({
            "rsp_cd": "00000",
            "COSOQ00201OutBlock4": [
                {"ShtnIsuNo": "BAD1", "AstkBalQty": "x"},
                {"ShtnIsuNo": "BAD2", "AstkBalQty": "y"},
            ],
        })
        assert resp.error_msg is not None
        assert "response parse error" in resp.error_msg
        assert resp.block4 == []

    def test_parse_exception_prefix_distinguishes_from_transport(self):
        exc = ResponseParseException(ValueError("boom"))
        assert str(exc).startswith("response parse error:")
        resp = _build({}, exc=exc)
        assert resp.error_msg.startswith("response parse error:")


class _StubTR:
    def __init__(self, resp):
        self._resp = resp

    async def req_async(self):
        return self._resp


class _StubAccnoClient:
    def __init__(self, resp):
        self._resp = resp

    def cosoq00201(self, body=None):
        return _StubTR(self._resp)


def _make_tracker(resp) -> StockAccountTracker:
    return StockAccountTracker(accno_client=_StubAccnoClient(resp), real_client=None)


class TestTrackerFailClosed:
    @pytest.mark.asyncio
    async def test_parse_failure_does_not_clear_positions(self):
        """GenericTR fallback(빈 응답 + error_msg)이 '보유종목 0개' 로 둔갑하면 안 된다."""
        failure = types.SimpleNamespace(
            rsp_cd="", rsp_msg="", error_msg="response parse error: ...",
            block3=[], block4=[],
        )
        tracker = _make_tracker(failure)
        sentinel = object()
        tracker._positions["SOXL"] = sentinel

        await tracker._fetch_positions()

        assert tracker._positions.get("SOXL") is sentinel, "기존 포지션이 지워지면 안 된다"
        assert "positions" in tracker._last_errors
        assert "response parse error" in tracker._last_errors["positions"]

    @pytest.mark.asyncio
    async def test_no_data_response_still_clears(self):
        """정상 '데이터 없음' 응답은 종전대로 빈 잔고 처리."""
        no_data = types.SimpleNamespace(
            rsp_cd="00123", rsp_msg="조회내역이 없습니다", error_msg=None,
            block3=[], block4=[],
        )
        tracker = _make_tracker(no_data)
        tracker._positions["SOXL"] = object()

        await tracker._fetch_positions()

        assert tracker._positions == {}
        assert "positions" not in tracker._last_errors
