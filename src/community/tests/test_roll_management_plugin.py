"""
RollManagement (롤오버 관리) 플러그인 테스트
"""

import pytest
from datetime import datetime
from programgarden_community.plugins.roll_management import (
    roll_management_condition,
    ROLL_MANAGEMENT_SCHEMA,
    _parse_expiry_date,
    _get_next_contract,
    risk_features,
)


class TestRollManagementPlugin:
    """RollManagement 플러그인 테스트"""

    @pytest.fixture
    def positions_near_expiry(self):
        """만기 임박 포지션"""
        # 현재 날짜 기준으로 곧 만기될 월물
        now = datetime.now()
        # 현재 월의 월물 코드 찾기
        month_code_map = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
                         7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
        current_month_code = month_code_map[now.month]
        year_str = str(now.year)[-2:]
        symbol = f"CL{current_month_code}{year_str}"
        return [
            {"symbol": symbol, "current_price": 70.5, "qty": 2, "market_code": "CME"},
        ]

    @pytest.fixture
    def positions_far_expiry(self):
        """만기 먼 포지션"""
        return [
            {"symbol": "CLZ30", "current_price": 72.0, "qty": 3, "market_code": "CME"},
        ]

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert ROLL_MANAGEMENT_SCHEMA.id == "RollManagement"

    def test_schema_category(self):
        assert ROLL_MANAGEMENT_SCHEMA.category == "position"

    def test_risk_features(self):
        assert "state" in risk_features

    def test_futures_only(self):
        from programgarden_core.registry.plugin_registry import ProductType
        assert ProductType.OVERSEAS_FUTURES in ROLL_MANAGEMENT_SCHEMA.products
        assert len(ROLL_MANAGEMENT_SCHEMA.products) == 1

    # === 유틸 함수 테스트 ===
    def test_parse_expiry_january(self):
        expiry = _parse_expiry_date("CLF26")
        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 1

    def test_parse_expiry_december(self):
        expiry = _parse_expiry_date("CLZ25")
        assert expiry is not None
        assert expiry.year == 2025
        assert expiry.month == 12

    def test_parse_expiry_long_prefix(self):
        expiry = _parse_expiry_date("HMCEG26")
        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 2

    def test_parse_expiry_invalid(self):
        assert _parse_expiry_date("AB") is None

    def test_get_next_contract_standard(self):
        assert _get_next_contract("CLF26") == "CLG26"

    def test_get_next_contract_december_to_january(self):
        assert _get_next_contract("CLZ25") == "CLF26"

    def test_get_next_contract_long_prefix(self):
        assert _get_next_contract("HMCEG26") == "HMCEH26"

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_near_expiry_triggered(self, positions_near_expiry):
        result = await roll_management_condition(
            positions=positions_near_expiry,
            fields={"days_before_expiry": 30},  # 넉넉한 기간
        )
        # 현재 월의 만기가 가까우므로 triggered
        if result["result"]:
            assert len(result["passed_symbols"]) > 0
            sr = result["symbol_results"][0]
            assert "next_contract" in sr
            assert sr["should_roll"] is True

    @pytest.mark.asyncio
    async def test_far_expiry_not_triggered(self, positions_far_expiry):
        result = await roll_management_condition(
            positions=positions_far_expiry,
            fields={"days_before_expiry": 5},
        )
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        result = await roll_management_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_output_structure(self, positions_far_expiry):
        result = await roll_management_condition(
            positions=positions_far_expiry,
            fields={"days_before_expiry": 5},
        )
        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert result["analysis"]["indicator"] == "RollManagement"

    @pytest.mark.asyncio
    async def test_symbol_results_detail(self, positions_far_expiry):
        result = await roll_management_condition(
            positions=positions_far_expiry,
            fields={"days_before_expiry": 5},
        )
        sr = result["symbol_results"][0]
        assert "expiry_date" in sr
        assert "days_to_expiry" in sr
        assert "next_contract" in sr
        assert "should_roll" in sr

    @pytest.mark.asyncio
    async def test_invalid_symbol_handling(self):
        positions = [
            {"symbol": "INVALID", "current_price": 70.0, "qty": 1, "market_code": "CME"},
        ]
        result = await roll_management_condition(positions=positions, fields={})
        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1


def _current_month_contract() -> str:
    """현재 월 월물(만기 = 이달 셋째 금요일 근사) — days_before_expiry=30 이면 항상 should_roll."""
    now = datetime.now()
    month_code_map = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
                      7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
    return f"CL{month_code_map[now.month]}{str(now.year)[-2:]}"


class TestLiveStatePathIsAlive:
    """상태 경로가 **실제 트래커로 실제로 돈다**는 것을 고정한다 (2026-09-12 수정).

    수정 전에는 실제 트래커에 없는 ``set_state`` 를 await 했고 ``except: pass`` 가 그
    AttributeError 를 삼켜 롤 신호 이력이 **한 번도 저장되지 않았다**. 여기서는 실제
    ``WorkflowRiskTracker`` 인스턴스(sqlite, tmp_path)로 저장·직렬화를 본다.
    """

    @staticmethod
    def _real_tracker(tmp_path, features=frozenset({"state"})):
        mod = pytest.importorskip(
            "programgarden.database.workflow_risk_tracker",
            reason="engine package not installed; live-truth pin skipped",
        )
        return mod.WorkflowRiskTracker(
            db_path=str(tmp_path / "rt.db"),
            job_id="pin", product="overseas_futures", provider="ls",
            trading_mode="real", features=set(features),
        )

    @staticmethod
    def _ctx(tracker):
        class RealCtx:
            risk_tracker = tracker
        return RealCtx()

    @pytest.mark.asyncio
    async def test_real_tracker_persists_roll_signal_date(self, tmp_path):
        tracker = self._real_tracker(tmp_path)
        symbol = _current_month_contract()
        before = datetime.now().strftime("%Y-%m-%d")
        result = await roll_management_condition(
            positions=[{"symbol": symbol, "current_price": 70.5, "qty": 2, "market_code": "CME"}],
            fields={"days_before_expiry": 30},
            context=self._ctx(tracker),
        )
        after = datetime.now().strftime("%Y-%m-%d")
        assert result["symbol_results"][0]["should_roll"] is True  # 전제
        saved = tracker.load_state(f"roll.{symbol}.signal_date")
        assert saved in {before, after}  # 자정 경계 허용
        assert isinstance(saved, str)  # 'string' 타입 왕복

    @pytest.mark.asyncio
    async def test_real_tracker_does_not_write_when_no_roll_signal(self, tmp_path):
        tracker = self._real_tracker(tmp_path)
        await roll_management_condition(
            positions=[{"symbol": "CLZ30", "current_price": 72.0, "qty": 3, "market_code": "CME"}],
            fields={"days_before_expiry": 5},
            context=self._ctx(tracker),
        )
        assert tracker.load_state("roll.CLZ30.signal_date") is None

    @pytest.mark.asyncio
    async def test_tracker_without_state_feature_warns_instead_of_swallowing(self, tmp_path, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        tracker = self._real_tracker(tmp_path, features=frozenset())
        symbol = _current_month_contract()
        result = await roll_management_condition(
            positions=[{"symbol": symbol, "current_price": 70.5, "qty": 2, "market_code": "CME"}],
            fields={"days_before_expiry": 30},
            context=self._ctx(tracker),
        )
        assert result["symbol_results"][0]["should_roll"] is True  # 판정 자체는 그대로
        assert tracker.load_state(f"roll.{symbol}.signal_date") is None
        assert any("RollManagement: 상태 저장 실패" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_foreign_tracker_variant_degrades_instead_of_crashing(self):
        class Foreign:
            async def set_state(self, key, value):  # 옛 이름 — 실제 트래커엔 없다
                raise AssertionError("must not be called")

        class Ctx:
            risk_tracker = Foreign()

        result = await roll_management_condition(
            positions=[{"symbol": _current_month_contract(), "current_price": 70.5, "qty": 2, "market_code": "CME"}],
            fields={"days_before_expiry": 30},
            context=Ctx(),
        )
        assert result["symbol_results"][0]["should_roll"] is True
