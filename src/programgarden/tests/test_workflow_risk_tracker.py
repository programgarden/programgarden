"""
WorkflowRiskTracker 단위 테스트

Feature-gated 위험관리 추적기의 모든 기능을 검증합니다.
"""

import asyncio
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from programgarden.database.workflow_risk_tracker import (
    WorkflowRiskTracker,
    HWMState,
    HWMUpdateResult,
    HWMValidationResult,
    VALID_FEATURES,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def tmp_db_path(tmp_path):
    """임시 DB 경로"""
    return str(tmp_path / "test_workflow.db")


def make_tracker(db_path, features, trading_mode="live"):
    """테스트용 RiskTracker 생성"""
    return WorkflowRiskTracker(
        db_path=db_path,
        job_id="test-job-001",
        product="overseas_stock",
        provider="ls",
        trading_mode=trading_mode,
        features=set(features),
    )


# ============================================================
# 1. Feature-gated 초기화
# ============================================================

class TestFeatureGatedInit:
    """Feature 조합별 초기화 검증"""

    def test_hwm_only(self, tmp_db_path):
        """{"hwm"} → hwm 테이블만 생성, events/state 미생성"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        assert tracker.has_feature("hwm")
        assert not tracker.has_feature("window")
        assert not tracker.has_feature("events")
        assert not tracker.has_feature("state")
        assert tracker._hwm is not None
        assert tracker._price_window is None

        # hwm 테이블 존재 확인
        with sqlite3.connect(tmp_db_path) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        assert "risk_high_water_mark" in tables
        assert "risk_events" not in tables
        assert "strategy_state" not in tables

    def test_state_only(self, tmp_db_path):
        """{"state"} → state 테이블만, hwm Dict = None"""
        tracker = make_tracker(tmp_db_path, {"state"})
        assert tracker.has_feature("state")
        assert not tracker.has_feature("hwm")
        assert tracker._hwm is None

        with sqlite3.connect(tmp_db_path) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        assert "strategy_state" in tables
        assert "risk_high_water_mark" not in tables

    def test_all_features(self, tmp_db_path):
        """{"hwm", "window", "events", "state"} → 전부 생성"""
        tracker = make_tracker(tmp_db_path, {"hwm", "window", "events", "state"})
        assert tracker.has_feature("hwm")
        assert tracker.has_feature("window")
        assert tracker.has_feature("events")
        assert tracker.has_feature("state")
        assert tracker._hwm is not None
        assert tracker._price_window is not None

        with sqlite3.connect(tmp_db_path) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        assert "risk_high_water_mark" in tables
        assert "risk_events" in tables
        assert "strategy_state" in tables

    def test_empty_features(self, tmp_db_path):
        """set() → 아무 테이블도 생성 안 됨"""
        tracker = make_tracker(tmp_db_path, set())
        assert tracker._hwm is None
        assert tracker._price_window is None
        assert tracker.features == frozenset()

    def test_invalid_features_filtered(self, tmp_db_path):
        """잘못된 feature 이름은 필터링됨"""
        tracker = make_tracker(tmp_db_path, {"hwm", "invalid_feature", "foo"})
        assert tracker.has_feature("hwm")
        assert not tracker.has_feature("invalid_feature")
        assert not tracker.has_feature("foo")
        assert tracker.features == frozenset({"hwm"})


# ============================================================
# 2. HWM 추적 (인메모리)
# ============================================================

class TestHWMTracking:
    """인메모리 HWM 추적 테스트"""

    def test_register_and_get_hwm(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)

        hwm = tracker.get_hwm("AAPL")
        assert hwm is not None
        assert hwm.symbol == "AAPL"
        assert hwm.hwm_price == Decimal("150.0")
        assert hwm.position_qty == 10
        assert hwm.position_avg_price == Decimal("150.0")

    def test_price_increase_updates_hwm(self, tmp_db_path):
        """가격 상승 → HWM 갱신"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)

        result = tracker.update_price("AAPL", "NASDAQ", 160.0)
        assert result is not None
        assert result.hwm_updated is True
        assert result.high_water_mark == Decimal("160.0")
        assert result.drawdown_pct == Decimal("0")

    def test_price_decrease_keeps_hwm(self, tmp_db_path):
        """가격 하락 → HWM 유지, drawdown 계산"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 100.0, 10)
        tracker.update_price("AAPL", "NASDAQ", 120.0)  # HWM = 120

        result = tracker.update_price("AAPL", "NASDAQ", 108.0)
        assert result.hwm_updated is False
        assert result.high_water_mark == Decimal("120.0")
        assert result.drawdown_pct == Decimal("10.00")  # (120-108)/120*100 = 10%

    def test_hwm_feature_없으면_none(self, tmp_db_path):
        """hwm feature 없을 때 update_price → None"""
        tracker = make_tracker(tmp_db_path, {"window"})
        result = tracker.update_price("AAPL", "NASDAQ", 100.0)
        assert result is None
        assert tracker.get_hwm("AAPL") is None

    def test_unregister_symbol(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        assert tracker.get_hwm("AAPL") is not None

        tracker.unregister_symbol("AAPL")
        assert tracker.get_hwm("AAPL") is None

    def test_additional_buy_updates_avg(self, tmp_db_path):
        """추가 매수 시 평단가 업데이트"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 100.0, 10)  # 100 * 10
        tracker.register_symbol("AAPL", "NASDAQ", 120.0, 10)  # 120 * 10

        hwm = tracker.get_hwm("AAPL")
        assert hwm.position_qty == 20
        # avg = (100*10 + 120*10) / 20 = 110
        assert hwm.position_avg_price == Decimal("110")

    def test_check_drawdown_threshold(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 100.0, 10)
        tracker.update_price("AAPL", "NASDAQ", 120.0)  # HWM = 120
        tracker.update_price("AAPL", "NASDAQ", 108.0)  # dd = 10%

        assert tracker.check_drawdown_threshold("AAPL", 5.0) is True
        assert tracker.check_drawdown_threshold("AAPL", 15.0) is False

    def test_get_all_hwm(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        tracker.register_symbol("MSFT", "NASDAQ", 300.0, 5)

        all_hwm = tracker.get_all_hwm()
        assert len(all_hwm) == 2
        assert "AAPL" in all_hwm
        assert "MSFT" in all_hwm


# ============================================================
# 3. Flush 동작
# ============================================================

class TestFlush:
    """Hot → Cold flush 테스트"""

    @pytest.mark.asyncio
    async def test_dirty_data_flush(self, tmp_db_path):
        """dirty 데이터만 DB write"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        tracker.update_price("AAPL", "NASDAQ", 160.0)

        count = await tracker.flush_to_db()
        assert count == 1

        # DB 확인
        with sqlite3.connect(tmp_db_path) as conn:
            rows = conn.execute("SELECT * FROM risk_high_water_mark").fetchall()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_clean_data_skip(self, tmp_db_path):
        """clean 데이터는 skip"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        await tracker.flush_to_db()  # 첫 flush

        count = await tracker.flush_to_db()  # 두번째 flush (clean)
        assert count == 0

    @pytest.mark.asyncio
    async def test_no_flush_without_hwm(self, tmp_db_path):
        """hwm feature 없을 때 flush → 0"""
        tracker = make_tracker(tmp_db_path, {"events"})
        count = await tracker.flush_to_db()
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush_loop_lifecycle(self, tmp_db_path):
        """flush loop 시작/중지"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)

        tracker.FLUSH_INTERVAL = 0.1  # 100ms for test
        tracker.start_flush_loop()
        assert tracker._flush_task is not None

        await asyncio.sleep(0.3)  # 몇 번 flush 되도록 대기

        await tracker.stop_flush_loop()
        assert tracker._flush_task is None

        # DB에 flush 되었는지 확인
        with sqlite3.connect(tmp_db_path) as conn:
            rows = conn.execute("SELECT * FROM risk_high_water_mark").fetchall()
        assert len(rows) == 1


# ============================================================
# 4. DB 복원
# ============================================================

class TestDBRestore:
    """Cold → Hot 복원 테스트"""

    @pytest.mark.asyncio
    async def test_restore_from_db(self, tmp_db_path):
        """DB에 저장된 HWM이 새 인스턴스에서 복원"""
        # 1차: 저장
        t1 = make_tracker(tmp_db_path, {"hwm"})
        t1.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        t1.update_price("AAPL", "NASDAQ", 170.0)
        await t1.flush_to_db()

        # 2차: 복원
        t2 = make_tracker(tmp_db_path, {"hwm"})
        hwm = t2.get_hwm("AAPL")
        assert hwm is not None
        assert hwm.hwm_price == Decimal("170")
        assert hwm.position_qty == 10


# ============================================================
# 5. 슬라이딩 윈도우 메트릭
# ============================================================

class TestSlidingWindow:
    """window feature 테스트"""

    def test_volatility_calculation(self, tmp_db_path):
        """get_volatility 정상 계산"""
        tracker = make_tracker(tmp_db_path, {"hwm", "window"})
        tracker.register_symbol("AAPL", "NASDAQ", 100.0, 10)

        # 30틱 이상 추가
        import random
        random.seed(42)
        for i in range(50):
            price = 100 + random.uniform(-5, 5)
            tracker.update_price("AAPL", "NASDAQ", price)

        vol = tracker.get_volatility("AAPL")
        assert vol is not None
        assert vol > Decimal("0")

    def test_insufficient_ticks_returns_none(self, tmp_db_path):
        """30틱 미만 → None"""
        tracker = make_tracker(tmp_db_path, {"window"})
        for i in range(10):
            tracker.add_tick("AAPL", 100.0 + i)

        vol = tracker.get_volatility("AAPL")
        assert vol is None

    def test_window_feature_없으면_none(self, tmp_db_path):
        """window feature 없을 때 → None"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        assert tracker.get_volatility("AAPL") is None

    def test_max_drawdown_window(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"window"})
        # 100 → 110 → 90 (MDD = (110-90)/110 = 18.18%)
        tracker.add_tick("AAPL", 100.0)
        tracker.add_tick("AAPL", 110.0)
        tracker.add_tick("AAPL", 90.0)

        mdd = tracker.get_max_drawdown_window("AAPL")
        assert mdd is not None
        assert mdd == Decimal("18.18")

    def test_tick_count(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"window"})
        now = datetime.now(timezone.utc)
        # 최근 10초 내 5틱
        for i in range(5):
            tracker._price_window.append(("AAPL", Decimal("100"), now))

        count = tracker.get_tick_count("AAPL", seconds=60)
        assert count == 5


# ============================================================
# 6. Risk Events
# ============================================================

class TestRiskEvents:
    """events feature 테스트"""

    def test_record_and_query(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"events"})

        event_id = tracker.record_risk_event(
            event_type="trailing_stop_triggered",
            severity="warning",
            symbol="AAPL",
            exchange="NASDAQ",
            details={"drawdown": 5.2, "threshold": 3.0},
        )
        assert event_id is not None

        events = tracker.get_risk_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "trailing_stop_triggered"
        assert events[0]["severity"] == "warning"
        assert events[0]["symbol"] == "AAPL"

    def test_events_feature_없으면_none(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm"})
        result = tracker.record_risk_event("test", "info")
        assert result is None
        assert tracker.get_risk_events() == []

    def test_event_count(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"events"})
        tracker.record_risk_event("type_a", "info")
        tracker.record_risk_event("type_a", "warning")
        tracker.record_risk_event("type_b", "critical")

        assert tracker.get_risk_event_count() == 3
        assert tracker.get_risk_event_count(event_type="type_a") == 2
        assert tracker.get_risk_event_count(event_type="type_b") == 1

    def test_event_filter_by_symbol(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"events"})
        tracker.record_risk_event("alert", "warning", symbol="AAPL")
        tracker.record_risk_event("alert", "warning", symbol="MSFT")

        aapl_events = tracker.get_risk_events(symbol="AAPL")
        assert len(aapl_events) == 1
        assert aapl_events[0]["symbol"] == "AAPL"


# ============================================================
# 7. Strategy State (KV)
# ============================================================

class TestStrategyState:
    """state feature 테스트"""

    def test_save_load_string(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        assert tracker.save_state("my_key", "hello") is True
        assert tracker.load_state("my_key") == "hello"

    def test_save_load_int(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("count", 42)
        assert tracker.load_state("count") == 42

    def test_save_load_float(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("ratio", 0.75)
        assert tracker.load_state("ratio") == 0.75

    def test_save_load_bool(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("flag", True)
        assert tracker.load_state("flag") is True

    def test_save_load_dict(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        data = {"a": 1, "b": "test"}
        tracker.save_state("config", data)
        assert tracker.load_state("config") == data

    def test_save_load_list(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        data = [1, 2, 3]
        tracker.save_state("items", data)
        assert tracker.load_state("items") == data

    def test_load_nonexistent(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        assert tracker.load_state("nonexistent") is None
        assert tracker.load_state("nonexistent", default="fallback") == "fallback"

    def test_state_feature_없으면_false(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm"})
        assert tracker.save_state("key", "value") is False
        assert tracker.load_state("key") is None

    def test_delete_state(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("temp", "data")
        assert tracker.delete_state("temp") is True
        assert tracker.load_state("temp") is None

    def test_load_states_by_prefix(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("plugin.a.x", 1)
        tracker.save_state("plugin.a.y", 2)
        tracker.save_state("plugin.b.z", 3)

        states = tracker.load_states("plugin.a.")
        assert len(states) == 2
        assert states["plugin.a.x"] == 1
        assert states["plugin.a.y"] == 2

    def test_delete_states_by_prefix(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("ns.a", 1)
        tracker.save_state("ns.b", 2)
        tracker.save_state("other.c", 3)

        deleted = tracker.delete_states("ns.")
        assert deleted == 2
        assert tracker.load_state("ns.a") is None
        assert tracker.load_state("other.c") == 3

    def test_snapshot(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        data = {"x": 10, "y": 20}
        tracker.save_snapshot("my_snapshot", data)

        restored = tracker.load_snapshot("my_snapshot")
        assert restored == data

    def test_upsert_overwrite(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"state"})
        tracker.save_state("key", "old")
        tracker.save_state("key", "new")
        assert tracker.load_state("key") == "new"


# ============================================================
# 8. 재시작 HWM 검증
# ============================================================

class TestHWMValidation:
    """validate_hwm_on_restart 테스트"""

    @pytest.mark.asyncio
    async def test_position_same_keeps_hwm(self, tmp_db_path):
        """포지션 동일 → 유지"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        tracker.update_price("AAPL", "NASDAQ", 170.0)
        await tracker.flush_to_db()

        # mock position tracker
        class MockPT:
            def get_workflow_positions(self):
                return {"AAPL": type("P", (), {"symbol": "AAPL", "quantity": 10, "avg_price": 150.0, "exchange": "NASDAQ"})()}

        results = tracker.validate_hwm_on_restart(MockPT())
        assert len(results) == 1
        assert results[0].action == "kept"

    @pytest.mark.asyncio
    async def test_position_changed_resets_hwm(self, tmp_db_path):
        """수량/평단 변동 → 리셋"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)
        tracker.update_price("AAPL", "NASDAQ", 200.0)

        class MockPT:
            def get_workflow_positions(self):
                return {"AAPL": type("P", (), {"symbol": "AAPL", "quantity": 20, "avg_price": 160.0, "exchange": "NASDAQ"})()}

        results = tracker.validate_hwm_on_restart(MockPT())
        reset_result = [r for r in results if r.action == "reset"]
        assert len(reset_result) == 1
        assert reset_result[0].old_hwm == Decimal("200.0")

    @pytest.mark.asyncio
    async def test_position_closed_deletes_hwm(self, tmp_db_path):
        """전량 청산 → 삭제"""
        tracker = make_tracker(tmp_db_path, {"hwm"})
        tracker.register_symbol("AAPL", "NASDAQ", 150.0, 10)

        class MockPT:
            def get_workflow_positions(self):
                return {}  # 포지션 없음

        results = tracker.validate_hwm_on_restart(MockPT())
        assert len(results) == 1
        assert results[0].action == "deleted"
        assert tracker.get_hwm("AAPL") is None

    @pytest.mark.asyncio
    async def test_new_position_creates_hwm(self, tmp_db_path):
        """신규 종목 → 신규 생성"""
        tracker = make_tracker(tmp_db_path, {"hwm"})

        class MockPT:
            def get_workflow_positions(self):
                return {"TSLA": type("P", (), {"symbol": "TSLA", "quantity": 5, "avg_price": 200.0, "exchange": "NASDAQ"})()}

        results = tracker.validate_hwm_on_restart(MockPT())
        new_results = [r for r in results if r.action == "new"]
        assert len(new_results) == 1
        assert tracker.get_hwm("TSLA") is not None


# ============================================================
# 9. Trading Mode 분리
# ============================================================

class TestTradingMode:
    """paper/live 데이터 격리 테스트"""

    @pytest.mark.asyncio
    async def test_paper_live_isolation(self, tmp_db_path):
        """paper/live 데이터 격리"""
        # paper 모드
        paper = make_tracker(tmp_db_path, {"hwm", "state"}, trading_mode="paper")
        paper.register_symbol("AAPL", "NASDAQ", 100.0, 10)
        paper.save_state("mode", "paper")
        await paper.flush_to_db()

        # live 모드
        live = make_tracker(tmp_db_path, {"hwm", "state"}, trading_mode="live")
        live.register_symbol("AAPL", "NASDAQ", 200.0, 5)
        live.save_state("mode", "live")
        await live.flush_to_db()

        # 격리 확인
        paper2 = make_tracker(tmp_db_path, {"hwm", "state"}, trading_mode="paper")
        hwm = paper2.get_hwm("AAPL")
        assert hwm is not None
        assert hwm.hwm_price == Decimal("100")
        assert paper2.load_state("mode") == "paper"

        live2 = make_tracker(tmp_db_path, {"hwm", "state"}, trading_mode="live")
        hwm = live2.get_hwm("AAPL")
        assert hwm is not None
        assert hwm.hwm_price == Decimal("200")
        assert live2.load_state("mode") == "live"


# ============================================================
# 10. Context 통합
# ============================================================

class TestContextIntegration:
    """ExecutionContext와의 통합 테스트"""

    def test_no_risk_tracker_by_default(self):
        """관련 노드 없을 때 context.risk_tracker = None"""
        from programgarden.context import ExecutionContext
        ctx = ExecutionContext(job_id="test", workflow_id="test-wf")
        assert ctx.risk_tracker is None

    def test_init_risk_tracker(self, tmp_db_path):
        """관련 노드 있을 때 정상 초기화"""
        from programgarden.context import ExecutionContext
        ctx = ExecutionContext(job_id="test", workflow_id="test-wf")

        # DB 경로를 오버라이드하기 위해 직접 초기화
        from programgarden.database import WorkflowRiskTracker
        ctx._workflow_risk_tracker = WorkflowRiskTracker(
            db_path=tmp_db_path,
            job_id="test",
            product="overseas_stock",
            provider="ls",
            trading_mode="live",
            features={"hwm", "window"},
        )

        assert ctx.risk_tracker is not None
        assert ctx.risk_tracker.has_feature("hwm")
        assert ctx.risk_tracker.has_feature("window")

    def test_empty_features_no_init(self):
        """빈 feature set → init_risk_tracker에서 return"""
        from programgarden.context import ExecutionContext
        ctx = ExecutionContext(job_id="test", workflow_id="test-wf")
        ctx.init_risk_tracker(
            features=set(),
            product="overseas_stock",
            provider="ls",
            paper_trading=False,
        )
        assert ctx.risk_tracker is None


# ============================================================
# 11. RiskEvent + Listener
# ============================================================

class TestRiskEventListener:
    """RiskEvent + on_risk_event 콜백 테스트"""

    @pytest.mark.asyncio
    async def test_on_risk_event_callback(self):
        """on_risk_event 리스너 호출 확인"""
        from programgarden.context import ExecutionContext
        from programgarden_core.bases.listener import RiskEvent, BaseExecutionListener

        received_events = []

        class TestListener(BaseExecutionListener):
            async def on_risk_event(self, event: RiskEvent):
                received_events.append(event)

        ctx = ExecutionContext(job_id="test", workflow_id="test-wf")
        ctx._listeners = [TestListener()]

        event = RiskEvent(
            job_id="test",
            event_type="trailing_stop_triggered",
            severity="warning",
            symbol="AAPL",
            details={"drawdown": 5.2},
        )
        await ctx.notify_risk_event(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "trailing_stop_triggered"
        assert received_events[0].symbol == "AAPL"


# ============================================================
# 12. update_price + window 연동
# ============================================================

class TestUpdatePriceWindowIntegration:
    """update_price 호출 시 window에도 틱이 추가되는지 확인"""

    def test_update_price_adds_to_window(self, tmp_db_path):
        tracker = make_tracker(tmp_db_path, {"hwm", "window"})
        tracker.register_symbol("AAPL", "NASDAQ", 100.0, 10)

        for i in range(50):
            tracker.update_price("AAPL", "NASDAQ", 100.0 + i * 0.1)

        assert len(tracker._price_window) == 50
        vol = tracker.get_volatility("AAPL")
        assert vol is not None
