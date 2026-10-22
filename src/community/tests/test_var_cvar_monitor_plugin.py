"""
VarCvarMonitor (VaR/CVaR 모니터) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.var_cvar_monitor import (
    var_cvar_monitor_condition,
    VAR_CVAR_MONITOR_SCHEMA,
    _calculate_historical_var,
    _calculate_parametric_var,
)


class MockRiskTracker:
    """실제 ``WorkflowRiskTracker.record_risk_event`` 와 같은 시그니처의 fake.

    (event_type, severity, symbol, exchange, details, node_id) → event_id. 실제 클래스에 없는
    ``record_event`` 를 제공하던 옛 목은 '초록인데 라이브에선 0건' 을 가렸다(2026-09-12).
    실제 트래커 왕복은 아래 TestLiveEventPathIsAlive 가 고정한다.
    """
    def __init__(self):
        self.events = []

    def record_risk_event(self, event_type, severity="warning", symbol=None, exchange=None,
                          details=None, node_id=None):
        self.events.append({"event_type": event_type, "severity": severity, "symbol": symbol,
                            "details": details})
        return len(self.events)


class MockContext:
    def __init__(self):
        self.risk_tracker = MockRiskTracker()


class TestVarCvarMonitorPlugin:
    """VarCvarMonitor 플러그인 테스트"""

    @pytest.fixture
    def mock_data_volatile(self):
        """변동성 높은 데이터 (VaR 높음)"""
        import random
        random.seed(42)
        data = []
        price = 100.0
        for i in range(70):
            # 높은 변동성: +-3% 변동
            change = random.uniform(-0.03, 0.03)
            price *= (1 + change)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(price, 2)})
        return data

    @pytest.fixture
    def mock_data_stable(self):
        """변동성 낮은 데이터"""
        data = []
        price = 100.0
        for i in range(70):
            price *= 1.001 if i % 2 == 0 else 0.999
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "BOND", "exchange": "NYSE", "date": date, "close": round(price, 4)})
        return data

    @pytest.fixture
    def mock_data_two_symbols(self):
        """2종목 데이터"""
        import random
        random.seed(42)
        data = []
        aapl_price, tsla_price = 150.0, 200.0
        for i in range(70):
            aapl_price *= 1 + random.uniform(-0.015, 0.015)
            tsla_price *= 1 + random.uniform(-0.03, 0.03)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert VAR_CVAR_MONITOR_SCHEMA.id == "VarCvarMonitor"

    def test_schema_category(self):
        assert VAR_CVAR_MONITOR_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = VAR_CVAR_MONITOR_SCHEMA.fields_schema
        assert "confidence_level" in fields
        assert "var_method" in fields
        assert "alert_threshold_pct" in fields

    # === 헬퍼 함수 테스트 ===
    def test_historical_var(self):
        returns = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, -0.025, 0.015, -0.005]
        var = _calculate_historical_var(returns, 95.0)
        assert var > 0

    def test_parametric_var(self):
        returns = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, -0.025, 0.015, -0.005]
        var = _calculate_parametric_var(returns, 95.0)
        assert var > 0

    def test_historical_var_empty(self):
        assert _calculate_historical_var([], 95.0) == 0.0

    def test_parametric_var_insufficient(self):
        assert _calculate_parametric_var([0.01], 95.0) == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_historical_var_calculation(self, mock_data_volatile):
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 95.0, "var_method": "historical"},
        )
        assert len(result["symbol_results"]) == 1
        sr = result["symbol_results"][0]
        assert sr["var_pct"] > 0
        assert sr["cvar_pct"] > 0
        assert "breached" in sr

    @pytest.mark.asyncio
    async def test_parametric_var_calculation(self, mock_data_volatile):
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 95.0, "var_method": "parametric"},
        )
        sr = result["symbol_results"][0]
        assert sr["var_pct"] > 0
        assert result["analysis"]["var_method"] == "parametric"

    @pytest.mark.asyncio
    async def test_cvar_geq_var(self, mock_data_volatile):
        """CVaR >= VaR (CVaR는 VaR보다 보수적)"""
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 95.0, "var_method": "historical"},
        )
        sr = result["symbol_results"][0]
        assert sr["cvar_pct"] >= sr["var_pct"]

    @pytest.mark.asyncio
    async def test_confidence_levels(self, mock_data_volatile):
        """높은 신뢰수준 → 높은 VaR"""
        result_90 = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 90.0},
        )
        result_99 = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 99.0},
        )
        var_90 = result_90["symbol_results"][0]["var_pct"]
        var_99 = result_99["symbol_results"][0]["var_pct"]
        assert var_99 >= var_90

    @pytest.mark.asyncio
    async def test_time_horizon_scaling(self, mock_data_volatile):
        """N일 VaR = 1일 VaR × sqrt(N)"""
        result_1d = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "time_horizon": 1},
        )
        result_4d = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "time_horizon": 4},
        )
        var_1d = result_1d["symbol_results"][0]["var_pct"]
        var_4d = result_4d["symbol_results"][0]["var_pct"]
        # 4일 VaR ≈ 1일 VaR × 2 (sqrt(4) = 2)
        assert abs(var_4d - var_1d * 2) < var_1d * 0.1

    @pytest.mark.asyncio
    async def test_breach_detection(self, mock_data_volatile):
        """낮은 임계값으로 breach 발생"""
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "alert_threshold_pct": 0.1, "action": "alert_only"},
        )
        assert result["result"] is True
        assert result["analysis"]["breached_count"] > 0

    @pytest.mark.asyncio
    async def test_no_breach(self, mock_data_stable):
        """안정적 데이터 → breach 없음"""
        result = await var_cvar_monitor_condition(
            data=mock_data_stable,
            fields={"lookback": 60, "alert_threshold_pct": 30.0},
        )
        assert result["result"] is False
        assert result["analysis"]["breached_count"] == 0

    @pytest.mark.asyncio
    async def test_portfolio_var_with_positions(self, mock_data_two_symbols):
        """positions 있을 때 달러 VaR 계산"""
        positions = [
            {"symbol": "AAPL", "current_price": 150.0, "qty": 100},
            {"symbol": "TSLA", "current_price": 200.0, "qty": 50},
        ]
        result = await var_cvar_monitor_condition(
            data=mock_data_two_symbols,
            fields={"lookback": 60, "alert_threshold_pct": 0.1},
            positions=positions,
        )
        for sr in result["symbol_results"]:
            if "var_dollar" in sr:
                assert sr["var_dollar"] > 0
                assert sr["position_value"] > 0

    @pytest.mark.asyncio
    async def test_risk_event_recording(self, mock_data_volatile):
        """[목 계약 — 라이브 아님] risk_tracker 이벤트 기록"""
        ctx = MockContext()
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "alert_threshold_pct": 0.1},
            context=ctx,
        )
        if result["result"]:
            assert len(ctx.risk_tracker.events) > 0
            assert ctx.risk_tracker.events[0]["event_type"] == "var_breach"
            assert ctx.risk_tracker.events[0]["details"]["threshold"] == 0.1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await var_cvar_monitor_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_volatile):
        result = await var_cvar_monitor_condition(
            data=mock_data_volatile,
            fields={"lookback": 60, "confidence_level": 99.0},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "VarCvarMonitor"
        assert analysis["confidence_level"] == 99.0
        assert "portfolio_var_pct" in analysis
        assert "portfolio_cvar_pct" in analysis


class TestVarCvarFractionalPosition:
    """소수 포지션 회귀 — int() 절단 + max(1, qty // 2) 바닥올림 (X3).

    ⚠️ 이 분기(positions 인자)는 워크플로우 실행기 경로에서는 도달하지 않는다 —
    실행기의 data 기반 분기가 plugin_kwargs 에 ``positions`` 를 넣지 않기 때문이다
    (플러그인 모듈 docstring 참조). 여기서 검증하는 것은 라이브러리를 직접
    호출하는 경로와 계산식 자체다.
    """

    @staticmethod
    def _volatile_bars(symbol="AAPL", n=70):
        """VaR 가 임계를 확실히 넘도록 +-3% 로 진동하는 결정론적 시계열."""
        bars = []
        price = 150.0
        for i in range(n):
            price = price * (1.03 if i % 2 == 0 else 0.97)
            bars.append({
                "symbol": symbol, "exchange": "NASDAQ",
                "date": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                "close": round(price, 4),
            })
        return bars

    async def _run(self, qty, action="reduce_position", price=150.0):
        return await var_cvar_monitor_condition(
            data=self._volatile_bars(),
            fields={"lookback": 20, "alert_threshold_pct": 1.0, "action": action},
            positions=[{"symbol": "AAPL", "current_price": price, "qty": qty}],
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty", [0.532, 1, 10])
    async def test_sell_quantity_never_exceeds_held(self, qty):
        """0.532 / 1 / 10 보유 어느 쪽도 보유량을 넘는 수량을 싣지 않는다.

        수정 전에는 0.532 보유에서 ``max(1, int(0.532) // 2) = 1`` 이 실렸다
        (보유 초과 매도).
        """
        result = await self._run(qty)
        assert result["result"] is True, "변동성 픽스처가 임계를 넘지 못했다"
        passed = result["passed_symbols"][0]
        assert passed["sell_quantity"] <= qty, (
            f"보유 {qty} 인데 매도 수량 {passed['sell_quantity']}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty,expected", [(0.532, 0.266), (1, 0.5), (10, 5)])
    async def test_sell_quantity_is_exact_half(self, qty, expected):
        """정확히 절반 — 소수는 보존되고 정수는 int 로 남는다."""
        result = await self._run(qty)
        passed = result["passed_symbols"][0]
        assert passed["sell_quantity"] == pytest.approx(expected)
        if float(expected).is_integer():
            assert isinstance(passed["sell_quantity"], int)

    @pytest.mark.asyncio
    async def test_fractional_position_value_is_not_zero(self):
        """150달러 x 0.532 = 79.8 — 수정 전에는 int(0.532)=0 이라 0.0 으로 보고됐다."""
        result = await self._run(0.532)
        sr = result["symbol_results"][0]
        assert sr["position_value"] == pytest.approx(79.8, abs=0.01)
        assert sr["var_dollar"] > 0
        assert "position_value_unavailable_reason" not in sr

    @pytest.mark.asyncio
    async def test_unreadable_quantity_leaves_reason_not_a_made_up_number(self):
        """수량을 읽을 수 없으면 수량을 지어내지 않고 사유를 남긴다."""
        result = await self._run("n/a")
        passed = result["passed_symbols"][0]
        sr = result["symbol_results"][0]
        assert "sell_quantity" not in passed
        assert "보유 수량을 읽을 수 없어" in sr["sell_quantity_unavailable_reason"]
        assert "position_value" not in sr
        assert "position_value_unavailable_reason" in sr

    @pytest.mark.asyncio
    async def test_missing_position_leaves_reason(self):
        """positions 에 종목이 없으면 sell_quantity 대신 사유를 남긴다."""
        result = await var_cvar_monitor_condition(
            data=self._volatile_bars(),
            fields={"lookback": 20, "alert_threshold_pct": 1.0, "action": "reduce_position"},
            positions=[{"symbol": "MSFT", "current_price": 300.0, "qty": 5}],
        )
        passed = result["passed_symbols"][0]
        sr = result["symbol_results"][0]
        assert "sell_quantity" not in passed
        assert "positions 입력에 해당 종목이 없어" in sr["sell_quantity_unavailable_reason"]

    @pytest.mark.asyncio
    async def test_exit_all_still_sells_everything(self):
        """exit_all 은 수량 계산과 무관하게 'all' 이다 (회귀 가드)."""
        result = await self._run(0.532, action="exit_all")
        assert result["passed_symbols"][0]["sell_quantity"] == "all"


class TestSellQuantityDeclarationMatchesValue:
    """Z3 — output_fields 선언과 실제 값이 어긋나지 않아야 한다.

    ``sell_quantity`` 는 'reduce_position' 에서는 숫자지만 'exit_all' 에서는 전량을
    뜻하는 **문자열 "all"** 이다. 선언 type 은 레지스트리 공통 검증
    (``test_plugin_output_fields.VALID_TYPES`` = float/int/str/bool/list/dict)이
    유니온 표기를 허용하지 않으므로, description 이 두 모양을 모두 밝힌다.
    """

    def test_description_documents_the_all_string(self):
        meta = VAR_CVAR_MONITOR_SCHEMA.output_fields["sell_quantity"]
        desc = meta["description"]
        assert '"all"' in desc, "문자열 'all' 을 싣는다는 사실이 선언에 없다"
        assert "exit_all" in desc
        assert "NOT always a number" in desc

    def test_declared_type_stays_in_the_registry_vocabulary(self):
        """공통 검증이 받는 어휘를 벗어나지 않는다(전 플러그인 일괄 테스트와 충돌 금지)."""
        assert VAR_CVAR_MONITOR_SCHEMA.output_fields["sell_quantity"]["type"] in {
            "float", "int", "str", "bool", "list", "dict"
        }

    @pytest.mark.asyncio
    async def test_exit_all_really_emits_the_string(self):
        result = await var_cvar_monitor_condition(
            data=TestVarCvarFractionalPosition._volatile_bars(),
            fields={"lookback": 20, "alert_threshold_pct": 1.0, "action": "exit_all"},
            positions=[{"symbol": "AAPL", "current_price": 150.0, "qty": 10}],
        )
        assert result["passed_symbols"][0]["sell_quantity"] == "all"


class TestReducePositionBelowOneShareIsNotSilent:
    """Z4 — 1주 미만 축소 수량은 주문이 만들어지지 않는다는 사실을 드러낸다.

    주문 송신부 ``NewOrderNodeExecutor._normalize_order`` 라이브 실측(2026-09-12,
    executor 직접 호출): quantity 0.5 → None, 0.999 → None, 1.0 → quantity 1,
    1.5 → quantity 1 + fractional_remainder 0.5. 즉 0 < 수량 < 1 이면 주문 자체가
    만들어지지 않는다. 동작은 바꾸지 않고(수량 그대로) 사유만 드러낸다.
    """

    async def _run(self, qty):
        return await var_cvar_monitor_condition(
            data=TestVarCvarFractionalPosition._volatile_bars(),
            fields={"lookback": 20, "alert_threshold_pct": 1.0, "action": "reduce_position"},
            positions=[{"symbol": "AAPL", "current_price": 150.0, "qty": qty}],
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty,half", [(1, 0.5), (0.532, 0.266), (1.9, 0.95)])
    async def test_sub_one_share_half_leaves_reason(self, qty, half):
        result = await self._run(qty)
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] == pytest.approx(half)  # 수량은 그대로 둔다
        assert result["passed_symbols"][0]["sell_quantity"] == pytest.approx(half)
        assert "1주 미만" in sr["reduce_skipped_reason"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty", [2, 10, 3.5])
    async def test_one_share_or_more_has_no_reason(self, qty):
        result = await self._run(qty)
        sr = result["symbol_results"][0]
        assert sr["sell_quantity"] >= 1
        assert "reduce_skipped_reason" not in sr

    @pytest.mark.asyncio
    async def test_unreadable_quantity_is_a_different_event(self):
        """'못 읽음' 은 축소 무동작이 아니라 수량 미발행이다 — 사유 키가 다르다."""
        result = await self._run("n/a")
        sr = result["symbol_results"][0]
        assert "sell_quantity_unavailable_reason" in sr
        assert "reduce_skipped_reason" not in sr

    def test_schema_declares_the_reason(self):
        assert "reduce_skipped_reason" in VAR_CVAR_MONITOR_SCHEMA.output_fields


class TestLiveEventPathIsAlive:
    """실제 WorkflowRiskTracker(sqlite) 로 var_breach 이벤트가 정말 기록되는지 — 목이 아니라."""

    @staticmethod
    def _real_tracker(tmp_path):
        mod = pytest.importorskip(
            "programgarden.database.workflow_risk_tracker",
            reason="engine package not installed; live-truth pin skipped",
        )
        return mod.WorkflowRiskTracker(
            db_path=str(tmp_path / "rt.db"),
            job_id="pin", product="overseas_stock", provider="ls",
            trading_mode="real", features={"events"},
        )

    @pytest.mark.asyncio
    async def test_real_tracker_records_var_breach(self, tmp_path):
        import json
        import random
        random.seed(7)
        data = []
        for i in range(120):
            data.append({"symbol": "VOL", "close": 100 + random.uniform(-30, 30), "date": f"2026-01-{i % 28 + 1:02d}"})
        tracker = self._real_tracker(tmp_path)

        class Ctx:
            risk_tracker = tracker

        result = await var_cvar_monitor_condition(
            data=data, fields={"lookback": 60, "alert_threshold_pct": 0.1}, context=Ctx(),
        )
        assert result["result"] is True, result
        events = tracker.get_risk_events(event_type="var_breach")
        assert len(events) >= 1
        assert events[0]["symbol"] == "VOL"
        details = json.loads(events[0]["details"])
        assert details["threshold"] == 0.1
        assert "var_pct" in details and "action" in details
