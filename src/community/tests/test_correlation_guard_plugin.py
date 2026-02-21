"""
CorrelationGuard (상관관계 가드) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.correlation_guard import (
    correlation_guard_condition,
    CORRELATION_GUARD_SCHEMA,
    _pearson_correlation,
    _spearman_correlation,
)


class MockRiskTracker:
    """mock risk tracker for state/event"""
    def __init__(self, initial_state=None):
        self.state = initial_state or {}
        self.events = []

    def get_state(self, key):
        return self.state.get(key)

    def set_state(self, key, value):
        self.state[key] = value

    def record_event(self, event_type, symbol, data):
        self.events.append({"event_type": event_type, "symbol": symbol, "data": data})


class MockContext:
    def __init__(self, initial_state=None):
        self.risk_tracker = MockRiskTracker(initial_state)


class TestCorrelationGuardPlugin:
    """CorrelationGuard 플러그인 테스트"""

    @pytest.fixture
    def mock_data_high_correlation(self):
        """고상관 2종목 (거의 동일한 움직임)"""
        data = []
        aapl_price, msft_price = 150.0, 300.0
        for i in range(70):
            move = 1.01 if i % 3 < 2 else 0.99
            aapl_price *= move
            msft_price *= move * (1 + 0.001)  # 거의 동일
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": round(msft_price, 2)})
        return data

    @pytest.fixture
    def mock_data_low_correlation(self):
        """저상관 2종목 (서로 무관한 움직임)"""
        import random
        random.seed(123)
        data = []
        aapl_price, gold_price = 150.0, 1800.0
        for i in range(70):
            # 완전히 독립적인 랜덤 움직임 → 상관관계 ≈ 0
            aapl_price *= 1 + random.uniform(-0.01, 0.01)
            gold_price *= 1 + random.uniform(-0.01, 0.01)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
            data.append({"symbol": "GOLD", "exchange": "NYSE", "date": date, "close": round(gold_price, 2)})
        return data

    @pytest.fixture
    def mock_data_three_symbols(self):
        """3종목 (AAPL-MSFT 고상관, GOLD 저상관)"""
        data = []
        aapl, msft, gold = 150.0, 300.0, 1800.0
        for i in range(70):
            move = 1.01 if i % 3 < 2 else 0.99
            aapl *= move
            msft *= move * (1 + 0.0005)
            gold *= 1 / move  # 역방향
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl, 2)})
            data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": round(msft, 2)})
            data.append({"symbol": "GOLD", "exchange": "NYSE", "date": date, "close": round(gold, 2)})
        return data

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert CORRELATION_GUARD_SCHEMA.id == "CorrelationGuard"

    def test_schema_category(self):
        assert CORRELATION_GUARD_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = CORRELATION_GUARD_SCHEMA.fields_schema
        assert "correlation_threshold" in fields
        assert "recovery_threshold" in fields
        assert "action" in fields

    # === 헬퍼 함수 테스트 ===
    def test_pearson_perfect_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = _pearson_correlation(x, y)
        assert abs(corr - 1.0) < 0.001

    def test_spearman_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = _spearman_correlation(x, y)
        assert abs(corr - 1.0) < 0.001

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_high_correlation_trigger(self, mock_data_high_correlation):
        """고상관 → regime=high_correlation, triggered=True"""
        result = await correlation_guard_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60, "correlation_threshold": 0.7, "action": "reduce_pct"},
        )
        assert result["analysis"]["regime"] == "high_correlation"
        assert result["analysis"]["triggered"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_low_correlation_pass(self, mock_data_low_correlation):
        """저상관 → regime=normal, triggered=False"""
        result = await correlation_guard_condition(
            data=mock_data_low_correlation,
            fields={"lookback": 60, "correlation_threshold": 0.8},
        )
        assert result["analysis"]["regime"] == "normal"
        assert result["analysis"]["triggered"] is False

    @pytest.mark.asyncio
    async def test_hysteresis(self, mock_data_high_correlation):
        """히스테리시스: 이전 regime 유지"""
        # 이전 regime이 high_correlation인데, 현재 avg가 threshold~recovery 사이
        ctx = MockContext(initial_state={"correlation_guard_regime": "high_correlation"})
        result = await correlation_guard_condition(
            data=mock_data_high_correlation,
            fields={
                "lookback": 60,
                "correlation_threshold": 0.99,  # 이 기준은 안 넘지만
                "recovery_threshold": 0.1,      # 이것보다는 높으므로
            },
            context=ctx,
        )
        # 이전 regime 유지 (high_correlation)
        assert result["analysis"]["regime"] == "high_correlation"

    @pytest.mark.asyncio
    async def test_regime_recovery(self, mock_data_low_correlation):
        """recovery_threshold 미만이면 normal로 복귀"""
        ctx = MockContext(initial_state={"correlation_guard_regime": "high_correlation"})
        result = await correlation_guard_condition(
            data=mock_data_low_correlation,
            fields={
                "lookback": 60,
                "correlation_threshold": 0.8,
                "recovery_threshold": 0.9,  # 높게 설정해서 쉽게 recovery
            },
            context=ctx,
        )
        assert result["analysis"]["regime"] == "normal"

    @pytest.mark.asyncio
    async def test_alert_only_action(self, mock_data_high_correlation):
        """alert_only: triggered이지만 passed_symbols 없음"""
        result = await correlation_guard_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60, "correlation_threshold": 0.5, "action": "alert_only"},
        )
        assert result["result"] is False  # alert_only는 passed에 추가 안 함

    @pytest.mark.asyncio
    async def test_exit_highest_action(self, mock_data_three_symbols):
        """exit_highest: 가장 높은 상관 종목만 exit"""
        result = await correlation_guard_condition(
            data=mock_data_three_symbols,
            fields={"lookback": 60, "correlation_threshold": 0.3, "action": "exit_highest"},
        )
        if result["result"]:
            # exit_highest: 1개만 passed
            assert len(result["passed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_pair_correlations_output(self, mock_data_three_symbols):
        """pair_correlations 출력 확인"""
        result = await correlation_guard_condition(
            data=mock_data_three_symbols,
            fields={"lookback": 60},
        )
        assert "pair_correlations" in result
        # 3종목 → 3개 페어
        assert len(result["pair_correlations"]) == 3

    @pytest.mark.asyncio
    async def test_risk_event_recording(self, mock_data_high_correlation):
        """risk_tracker 이벤트 기록"""
        ctx = MockContext()
        result = await correlation_guard_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60, "correlation_threshold": 0.5},
            context=ctx,
        )
        if result["analysis"]["triggered"]:
            assert len(ctx.risk_tracker.events) > 0
            assert ctx.risk_tracker.events[0]["event_type"] == "high_correlation"
            # state 저장 확인
            assert ctx.risk_tracker.state.get("correlation_guard_regime") == "high_correlation"

    @pytest.mark.asyncio
    async def test_single_symbol_error(self):
        """단일 종목 → 에러"""
        data = [{"symbol": "AAPL", "exchange": "NASDAQ", "date": f"2026010{i+1}", "close": 150 + i} for i in range(70)]
        result = await correlation_guard_condition(data=data, fields={"lookback": 60})
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await correlation_guard_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_spearman_method(self, mock_data_high_correlation):
        """spearman 방식 테스트"""
        result = await correlation_guard_condition(
            data=mock_data_high_correlation,
            fields={"lookback": 60, "method": "spearman"},
        )
        assert result["analysis"]["method"] == "spearman"
