"""
CorrelationGuard (상관관계 가드) 플러그인 테스트

상태(strategy_state)·이벤트 경로 — 2026-09-12 수정
------------------------------------------------------------------------------------------
``FakeRiskTracker`` 는 실제 트래커 ``programgarden.database.workflow_risk_tracker.
WorkflowRiskTracker`` 의 **실제 시그니처**(``load_state``/``save_state``/``delete_state``/
``record_risk_event`` — 전부 동기)를 흉내낸다. 종전 목은 실제 클래스에 없는
``get_state``/``set_state``/``record_event`` 를 제공해, 테스트는 통과하는데 라이브에서는
except 가 AttributeError 를 삼켜 히스테리시스도 이벤트도 동작하지 않았다.
``TestLiveStatePathIsAlive`` 가 **실제 트래커 인스턴스**로 그 사실을 고정한다.
"""

import pytest
from programgarden_community.plugins.correlation_guard import (
    correlation_guard_condition,
    CORRELATION_GUARD_SCHEMA,
    _pearson_correlation,
    _spearman_correlation,
)


class FakeRiskTracker:
    """실제 WorkflowRiskTracker 의 state/events 인터페이스와 같은 이름·동기 규약의 fake."""

    def __init__(self, initial_state=None):
        self.state = initial_state or {}
        self.events = []

    def load_state(self, key, default=None):
        return self.state.get(key, default)

    def save_state(self, key, value):
        self.state[key] = value
        return True

    def delete_state(self, key):
        return self.state.pop(key, None) is not None

    def record_risk_event(self, event_type, severity="warning", symbol=None,
                          exchange=None, details=None, node_id=None):
        self.events.append({
            "event_type": event_type, "severity": severity, "symbol": symbol,
            "exchange": exchange, "details": details, "node_id": node_id,
        })
        return len(self.events)


MockRiskTracker = FakeRiskTracker  # 기존 테스트 본문 이름 유지 (실제 시그니처 fake)


class MockContext:
    def __init__(self, initial_state=None):
        self.risk_tracker = FakeRiskTracker(initial_state)


async def _boundary_fields(data, lookback=60):
    """실제 avg_correlation 을 재서 recovery < avg < threshold 인 필드를 만든다."""
    probe = await correlation_guard_condition(data=data, fields={"lookback": lookback})
    avg = probe["analysis"]["avg_correlation"]
    return {
        "lookback": lookback,
        "correlation_threshold": avg + 0.05,
        "recovery_threshold": avg - 0.05,
    }


def _high_correlation_data():
    """고상관 2종목 (거의 동일한 움직임) — 클래스 픽스처와 같은 데이터"""
    data = []
    aapl_price, msft_price = 150.0, 300.0
    for i in range(70):
        move = 1.01 if i % 3 < 2 else 0.99
        aapl_price *= move
        msft_price *= move * (1 + 0.001)
        date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
        data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(aapl_price, 2)})
        data.append({"symbol": "MSFT", "exchange": "NASDAQ", "date": date, "close": round(msft_price, 2)})
    return data


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
        """히스테리시스: 경계 구간(recovery < avg < threshold)에서는 이전 regime 유지.

        픽스처의 avg_correlation 은 1.0 이라(실측) 고정 임계값 0.99 로는 경계 구간이
        만들어지지 않았다 — 종전 이 테스트는 avg ≥ threshold 로 무조건 high 가 나와
        히스테리시스를 검증하지 못했다. 실제 avg 를 재고 그 ±0.05 를 임계값으로 쓴다.
        """
        fields = await _boundary_fields(mock_data_high_correlation)
        ctx = MockContext(initial_state={"correlation_guard_regime": "high_correlation"})
        result = await correlation_guard_condition(
            data=mock_data_high_correlation, fields=fields, context=ctx,
        )
        assert result["analysis"]["regime"] == "high_correlation"  # 이전 regime 유지
        # 대조군: 이전 regime 이 없으면 같은 입력에서 normal
        control = await correlation_guard_condition(
            data=mock_data_high_correlation, fields=fields, context=MockContext(),
        )
        assert control["analysis"]["regime"] == "normal"

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


class TestLiveStatePathIsAlive:
    """상태·이벤트 경로가 **실제 트래커로 실제로 돈다**는 것을 고정한다 (2026-09-12 수정).

    켜졌을 때의 의미: 경계 구간(recovery < avg < threshold)에서 '이전 regime 유지' 가
    실제로 **직전 사이클이 저장한 regime** 을 따른다(수정 전엔 항상 normal).
    """

    @staticmethod
    def _real_tracker(tmp_path, features=frozenset({"state", "events"}), name="rt.db"):
        mod = pytest.importorskip(
            "programgarden.database.workflow_risk_tracker",
            reason="engine package not installed; live-truth pin skipped",
        )
        return mod.WorkflowRiskTracker(
            db_path=str(tmp_path / name),
            job_id="pin", product="overseas_stock", provider="ls",
            trading_mode="real", features=set(features),
        )

    @staticmethod
    def _ctx(tracker):
        class RealCtx:
            risk_tracker = tracker
        return RealCtx()

    @pytest.mark.asyncio
    async def test_real_tracker_hysteresis_round_trip(self, tmp_path):
        """1회차 고상관 트리거 → 2회차 경계 구간은 **저장된** high_correlation 을 유지한다."""
        tracker = self._real_tracker(tmp_path)
        first = await correlation_guard_condition(
            data=_high_correlation_data(),
            fields={"lookback": 60, "correlation_threshold": 0.5},
            context=self._ctx(tracker),
        )
        assert first["analysis"]["regime"] == "high_correlation"
        assert tracker.load_state("correlation_guard_regime") == "high_correlation"

        boundary = await _boundary_fields(_high_correlation_data())
        second = await correlation_guard_condition(
            data=_high_correlation_data(), fields=boundary, context=self._ctx(tracker),
        )
        assert second["analysis"]["regime"] == "high_correlation", "히스테리시스가 상태를 되읽지 못했다"

        # 이력이 없는 새 DB 의 트래커는 같은 입력에서 normal 이다 — 위 결과가 상태 덕분임을 고정
        fresh = self._real_tracker(tmp_path, name="fresh.db")
        third = await correlation_guard_condition(
            data=_high_correlation_data(), fields=boundary, context=self._ctx(fresh),
        )
        assert third["analysis"]["regime"] == "normal"

    @pytest.mark.asyncio
    async def test_real_tracker_regime_survives_restart(self, tmp_path):
        await correlation_guard_condition(
            data=_high_correlation_data(),
            fields={"lookback": 60, "correlation_threshold": 0.5},
            context=self._ctx(self._real_tracker(tmp_path)),
        )
        restarted = self._real_tracker(tmp_path)  # 같은 rt.db
        result = await correlation_guard_condition(
            data=_high_correlation_data(), fields=await _boundary_fields(_high_correlation_data()),
            context=self._ctx(restarted),
        )
        assert result["analysis"]["regime"] == "high_correlation"

    @pytest.mark.asyncio
    async def test_real_tracker_records_risk_event(self, tmp_path):
        """수정 전엔 record_event(없는 이름) → except 삼킴 → 이벤트 0건."""
        import json
        tracker = self._real_tracker(tmp_path)
        result = await correlation_guard_condition(
            data=_high_correlation_data(),
            fields={"lookback": 60, "correlation_threshold": 0.5, "action": "reduce_pct"},
            context=self._ctx(tracker),
        )
        assert result["analysis"]["triggered"] is True
        events = tracker.get_risk_events(event_type="high_correlation")
        assert len(events) == 1
        assert events[0]["symbol"] == "PORTFOLIO"
        details = json.loads(events[0]["details"])
        assert details["avg_correlation"] == result["analysis"]["avg_correlation"]
        assert details["action"] == "reduce_pct"

    @pytest.mark.asyncio
    async def test_tracker_without_features_warns_instead_of_swallowing(self, tmp_path, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        tracker = self._real_tracker(tmp_path, features=frozenset())
        result = await correlation_guard_condition(
            data=_high_correlation_data(),
            fields={"lookback": 60, "correlation_threshold": 0.5},
            context=self._ctx(tracker),
        )
        assert result["analysis"]["regime"] == "high_correlation"  # 판정 자체는 그대로
        messages = [r.message for r in caplog.records]
        assert any("CorrelationGuard: 상태 저장 실패" in m for m in messages)
        assert any("CorrelationGuard: 위험 이벤트 기록 실패" in m for m in messages)

    @pytest.mark.asyncio
    async def test_foreign_tracker_variant_degrades_instead_of_crashing(self):
        class Foreign:
            def get_state(self, key):  # 옛 이름 — 실제 트래커엔 없다
                raise AssertionError("must not be called")

        class Ctx:
            risk_tracker = Foreign()

        result = await correlation_guard_condition(
            data=_high_correlation_data(), fields=await _boundary_fields(_high_correlation_data()),
            context=Ctx(),
        )
        assert result["analysis"]["regime"] == "normal"  # prev_regime 기본값
