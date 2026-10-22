"""
TimeBasedExit 플러그인 테스트

상태(strategy_state) 경로 — 2026-09-12 수정
------------------------------------------------------------------------------------------
이 파일의 ``FakeRiskTracker`` 는 실제 트래커
``programgarden.database.workflow_risk_tracker.WorkflowRiskTracker`` 의 **실제 시그니처**
(``load_state`` / ``save_state`` / ``delete_state`` / ``load_states`` — 전부 동기)를 그대로
흉내낸다. 종전의 ``MockRiskTracker`` 는 실제 클래스에 없는 ``get_state``/``set_state``
(그것도 async) 를 제공해, 테스트는 통과하는데 실제 트래커를 넘기면
``AttributeError: 'WorkflowRiskTracker' object has no attribute 'get_state'`` 로 즉사했다.

아래 ``TestLiveStatePathIsAlive`` 는 **실제 트래커 인스턴스**(sqlite, tmp_path)로 왕복해
그 사실을 고정한다 — fake 로는 증명되지 않는 것(직렬화·재시작 복원·정리 스윕)만 거기서 본다.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch
from programgarden_community.plugins.time_based_exit import (
    time_based_exit_condition,
    TIME_BASED_EXIT_SCHEMA,
)


class FakeRiskTracker:
    """실제 WorkflowRiskTracker 의 state 인터페이스와 **같은 이름·같은 동기 규약**의 fake.

    실제 클래스: load_state(key, default=None) / save_state(key, value) -> bool /
    delete_state(key) -> bool / load_states(prefix) -> dict. 전부 동기.
    """

    def __init__(self):
        self._state = {}

    def load_state(self, key, default=None):
        return self._state.get(key, default)

    def save_state(self, key, value):
        self._state[key] = value
        return True

    def delete_state(self, key):
        return self._state.pop(key, None) is not None

    def load_states(self, prefix):
        return {k: v for k, v in self._state.items() if k.startswith(prefix)}


# 기존 테스트 본문의 이름을 유지하기 위한 별칭 (실제 시그니처 fake 다 — 목 계약이 아니다)
MockRiskTracker = FakeRiskTracker


class MockContext:
    def __init__(self, risk_tracker=None):
        self.risk_tracker = risk_tracker


class TestTimeBasedExitPlugin:

    @pytest.mark.asyncio
    async def test_new_position_records_entry(self):
        """신규 포지션 진입일 기록"""
        tracker = MockRiskTracker()
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5, "warn_days": 0},
            context=context,
        )
        # 오늘 등록 → hold_days=0 → 미트리거
        assert result["result"] is False
        assert "time_exit.AAPL.entry_date" in tracker._state
        sr = result["symbol_results"][0]
        assert sr["hold_days"] == 0
        assert sr["action"] == "hold"

    @pytest.mark.asyncio
    async def test_exit_triggered(self):
        """보유일 초과 시 청산 트리거"""
        tracker = MockRiskTracker()
        entry = (date.today() - timedelta(days=6)).isoformat()
        tracker._state["time_exit.AAPL.entry_date"] = entry
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5},
            context=context,
        )
        assert result["result"] is True
        sr = result["symbol_results"][0]
        assert sr["hold_days"] >= 5
        assert sr["action"] == "exit"

    @pytest.mark.asyncio
    async def test_warn_triggered(self):
        """경고 일수 도달"""
        tracker = MockRiskTracker()
        entry = (date.today() - timedelta(days=4)).isoformat()
        tracker._state["time_exit.AAPL.entry_date"] = entry
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5, "warn_days": 2},
            context=context,
        )
        assert result["result"] is False  # 아직 exit 아님
        sr = result["symbol_results"][0]
        assert sr["warn"] is True
        assert sr["action"] == "warn"

    @pytest.mark.asyncio
    async def test_position_closed_clears_state(self):
        """포지션 청산 시 상태 삭제"""
        tracker = MockRiskTracker()
        tracker._state["time_exit.AAPL.entry_date"] = "2025-01-01"
        context = MockContext(tracker)

        positions = [{"symbol": "AAPL", "qty": 0, "market_code": "82"}]
        await time_based_exit_condition(positions=positions, fields={}, context=context)
        assert "time_exit.AAPL.entry_date" not in tracker._state

    @pytest.mark.asyncio
    async def test_without_context(self):
        """context 없이 실행"""
        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5},
        )
        # context 없으면 진입일 저장 불가 → 항상 오늘로 기록 → hold_days=0
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        """빈 포지션"""
        result = await time_based_exit_condition(positions=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_multiple_symbols(self):
        """여러 종목"""
        tracker = MockRiskTracker()
        tracker._state["time_exit.AAPL.entry_date"] = (date.today() - timedelta(days=10)).isoformat()
        tracker._state["time_exit.NVDA.entry_date"] = (date.today() - timedelta(days=2)).isoformat()
        context = MockContext(tracker)

        positions = [
            {"symbol": "AAPL", "qty": 100, "market_code": "82"},
            {"symbol": "NVDA", "qty": 50, "market_code": "82"},
        ]
        result = await time_based_exit_condition(
            positions=positions,
            fields={"max_hold_days": 5},
            context=context,
        )
        assert result["result"] is True
        assert len(result["passed_symbols"]) == 1  # AAPL만
        assert result["passed_symbols"][0]["symbol"] == "AAPL"

    def test_schema(self):
        assert TIME_BASED_EXIT_SCHEMA.id == "TimeBasedExit"
        cat = TIME_BASED_EXIT_SCHEMA.category
        assert (cat.value if hasattr(cat, 'value') else cat) == "position"
        assert "max_hold_days" in TIME_BASED_EXIT_SCHEMA.fields_schema
        assert "warn_days" in TIME_BASED_EXIT_SCHEMA.fields_schema


class TestUnreadableQuantityIsReachable:
    """Z1 — 원값 비교(``if qty <= 0``)가 '수량을 못 읽었다' 를 삼키지 않아야 한다.

    구 코드는 pos_data 원값을 그대로 비교해, 수량이 숫자가 아니면 그 줄에서
    TypeError 로 플러그인 전체가 죽었다(``'n/a' <= 0`` · ``'100' <= 0`` ·
    ``None <= 0`` 모두 TypeError — 직접 실행 확인 2026-09-12). 결과에 사유가
    남을 기회 자체가 없었다.
    """

    @staticmethod
    async def _run(qty):
        return await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": qty, "market_code": "82"}],
            fields={"max_hold_days": 5},
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty", ["n/a", None, "", float("nan")])
    async def test_unreadable_quantity_leaves_reason_instead_of_crashing(self, qty):
        result = await self._run(qty)  # 구 코드: TypeError
        sr = result["symbol_results"][0]
        assert sr["action"] == "skip"
        assert "보유 수량을 읽을 수 없어" in sr["reason"]
        assert repr(qty) in sr["reason"]
        assert result["passed_symbols"] == []
        assert result["failed_symbols"][0]["symbol"] == "AAPL"
        # 보유일수를 지어내지 않는다
        assert "hold_days" not in sr

    @pytest.mark.asyncio
    async def test_numeric_string_quantity_is_read_not_crashed(self):
        """'100' 은 읽을 수 있는 수량이다 — 구 코드는 여기서도 TypeError 였다."""
        result = await self._run("100")
        sr = result["symbol_results"][0]
        assert sr["action"] in {"hold", "warn", "exit"}
        assert sr["hold_days"] == 0

    @pytest.mark.asyncio
    async def test_readable_zero_is_still_cleared(self):
        """'0' 과 '못 읽음' 은 다른 사건 — 0 은 종전대로 청산 완료(cleared)."""
        result = await self._run(0)
        sr = result["symbol_results"][0]
        assert sr["action"] == "cleared"
        assert sr["reason"] == "Position closed"

    @pytest.mark.asyncio
    async def test_unreadable_quantity_does_not_delete_entry_date_state(self):
        """청산인지 알 수 없으므로 진입일 상태를 지우지 않는다."""
        tracker = MockRiskTracker()
        key = "time_exit.AAPL.entry_date"
        tracker._state[key] = (date.today() - timedelta(days=10)).isoformat()
        result = await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": "n/a", "market_code": "82"}],
            fields={"max_hold_days": 5},
            context=MockContext(tracker),
        )
        assert result["symbol_results"][0]["action"] == "skip"
        assert key in tracker._state

    def test_schema_declares_skip_and_reason(self):
        of = TIME_BASED_EXIT_SCHEMA.output_fields
        assert "reason" in of
        assert "skip" in of["action"]["description"]


class _FakeDate(date):
    """``date.today()`` 를 고정/전진시키기 위한 date 서브클래스 (fromisoformat 은 그대로)."""

    _today = date(2026, 9, 14)

    @classmethod
    def today(cls):
        return cls._today


class TestLiveStatePathIsAlive:
    """상태 경로가 **실제 트래커로 실제로 돈다**는 것을 고정한다 (2026-09-12 수정).

    수정 전에는 (1) 실행기의 positions 분기가 context 를 넘기지 않았고, (2) 플러그인이
    실제 트래커에 없는 ``get_state``/``set_state`` 를 await 했다. (1) 은 executor 쪽
    테스트에서, (2) 는 여기서 **실제 WorkflowRiskTracker 인스턴스**로 고정한다.

    켜졌을 때의 의미(모듈 docstring 과 대조):
    - entry_date 는 이 플러그인이 포지션을 **처음 관측한 날**로 고정되고, 이후 사이클에서
      덮어쓰지 않는다 → hold_days 가 실제로 자란다(수정 전엔 매번 오늘 → 영영 0).
    - 값은 ISO 문자열(YYYY-MM-DD) 로 저장되고 트래커의 'string' 타입으로 그대로 왕복한다.
    - 같은 DB 를 다시 연 새 트래커(재시작)에서도 entry_date 가 복원된다.
    - 포지션이 사라진 종목의 entry_date 는 정리된다(docstring 의 '자동 정리' 약속).
    """

    @staticmethod
    def _real_tracker(tmp_path, features=frozenset({"state"}), name="rt.db"):
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
    async def test_real_tracker_does_not_crash_and_pins_first_observation_date(self, tmp_path):
        """수정 전: AttributeError('WorkflowRiskTracker' object has no attribute 'get_state')."""
        tracker = self._real_tracker(tmp_path)
        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]

        with patch("programgarden_community.plugins.time_based_exit.date", _FakeDate):
            _FakeDate._today = date(2026, 9, 14)
            first = await time_based_exit_condition(
                positions=positions, fields={"max_hold_days": 5}, context=self._ctx(tracker),
            )
            # 하루 뒤 — entry_date 는 첫 관측일 그대로여야 한다(덮어쓰지 않는다)
            _FakeDate._today = date(2026, 9, 15)
            second = await time_based_exit_condition(
                positions=positions, fields={"max_hold_days": 5}, context=self._ctx(tracker),
            )

        assert first["symbol_results"][0]["hold_days"] == 0
        assert second["symbol_results"][0]["entry_date"] == "2026-09-14"
        assert second["symbol_results"][0]["hold_days"] == 1
        # 트래커에 실제로 남은 값: ISO 문자열 그대로('string' 타입 왕복)
        assert tracker.load_state("time_exit.AAPL.entry_date") == "2026-09-14"

    @pytest.mark.asyncio
    async def test_real_tracker_hold_days_grow_until_exit(self, tmp_path):
        """max_hold_days=5 → 6번째 날(hold_days=5)에 exit. 수정 전엔 영영 hold 였다."""
        tracker = self._real_tracker(tmp_path)
        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        actions, hold_days = [], []
        with patch("programgarden_community.plugins.time_based_exit.date", _FakeDate):
            for offset in range(6):
                _FakeDate._today = date(2026, 9, 14) + timedelta(days=offset)
                r = await time_based_exit_condition(
                    positions=positions, fields={"max_hold_days": 5, "warn_days": 2},
                    context=self._ctx(tracker),
                )
                sr = r["symbol_results"][0]
                actions.append(sr["action"])
                hold_days.append(sr["hold_days"])
        assert hold_days == [0, 1, 2, 3, 4, 5]
        assert actions == ["hold", "hold", "hold", "warn", "warn", "exit"], actions

    @pytest.mark.asyncio
    async def test_real_tracker_entry_date_survives_restart(self, tmp_path):
        """같은 DB 를 다시 연 새 트래커(워크플로우 재시작)에서 entry_date 가 복원된다."""
        positions = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        with patch("programgarden_community.plugins.time_based_exit.date", _FakeDate):
            _FakeDate._today = date(2026, 9, 14)
            await time_based_exit_condition(
                positions=positions, fields={"max_hold_days": 5},
                context=self._ctx(self._real_tracker(tmp_path)),
            )
            _FakeDate._today = date(2026, 9, 20)
            restarted = self._real_tracker(tmp_path)  # 같은 rt.db
            r = await time_based_exit_condition(
                positions=positions, fields={"max_hold_days": 5},
                context=self._ctx(restarted),
            )
        sr = r["symbol_results"][0]
        assert sr["entry_date"] == "2026-09-14"
        assert sr["hold_days"] == 6
        assert sr["action"] == "exit"

    @pytest.mark.asyncio
    async def test_real_tracker_closed_position_deletes_state(self, tmp_path):
        tracker = self._real_tracker(tmp_path)
        tracker.save_state("time_exit.AAPL.entry_date", "2026-01-01")
        r = await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": 0, "market_code": "82"}],
            fields={}, context=self._ctx(tracker),
        )
        assert r["symbol_results"][0]["action"] == "cleared"
        assert tracker.load_state("time_exit.AAPL.entry_date") is None

    @pytest.mark.asyncio
    async def test_real_tracker_sweeps_symbols_no_longer_in_positions(self, tmp_path):
        """전량 매도돼 positions 에서 **사라진** 종목의 entry_date 를 정리한다.

        정리하지 않으면 재매수 직후 옛 entry_date 로 hold_days 가 커져 거짓 exit 가 난다.
        """
        tracker = self._real_tracker(tmp_path)
        tracker.save_state("time_exit.AAPL.entry_date", "2026-01-01")
        tracker.save_state("time_exit.BRK.B.entry_date", "2026-01-01")  # 점 포함 심볼
        tracker.save_state("time_exit.NVDA.entry_date", "2026-01-01")
        r = await time_based_exit_condition(
            positions=[{"symbol": "NVDA", "qty": 10, "market_code": "82"}],
            fields={"max_hold_days": 5}, context=self._ctx(tracker),
        )
        assert tracker.load_state("time_exit.AAPL.entry_date") is None
        assert tracker.load_state("time_exit.BRK.B.entry_date") is None
        assert tracker.load_state("time_exit.NVDA.entry_date") == "2026-01-01"
        assert sorted(r["analysis"]["stale_state_cleared"]) == ["AAPL", "BRK.B"]

    @pytest.mark.asyncio
    async def test_real_tracker_sweeps_everything_when_account_is_flat(self, tmp_path):
        """positions 가 비면(전부 청산) 남은 entry_date 를 모두 정리한다."""
        tracker = self._real_tracker(tmp_path)
        tracker.save_state("time_exit.AAPL.entry_date", "2026-01-01")
        r = await time_based_exit_condition(positions=[], fields={}, context=self._ctx(tracker))
        assert r["result"] is False
        assert tracker.load_state("time_exit.AAPL.entry_date") is None

    @pytest.mark.asyncio
    async def test_real_tracker_reentry_after_full_exit_starts_fresh(self, tmp_path):
        """매도(사라짐) → 재매수 시 hold_days 가 0 부터 다시 센다 — 거짓 exit 없음."""
        tracker = self._real_tracker(tmp_path)
        aapl = [{"symbol": "AAPL", "qty": 100, "market_code": "82"}]
        with patch("programgarden_community.plugins.time_based_exit.date", _FakeDate):
            _FakeDate._today = date(2026, 9, 1)
            await time_based_exit_condition(positions=aapl, fields={"max_hold_days": 5}, context=self._ctx(tracker))
            _FakeDate._today = date(2026, 9, 3)
            await time_based_exit_condition(positions=[], fields={"max_hold_days": 5}, context=self._ctx(tracker))
            _FakeDate._today = date(2026, 9, 20)
            r = await time_based_exit_condition(positions=aapl, fields={"max_hold_days": 5}, context=self._ctx(tracker))
        sr = r["symbol_results"][0]
        assert sr["entry_date"] == "2026-09-20"
        assert sr["hold_days"] == 0
        assert sr["action"] == "hold"

    @pytest.mark.asyncio
    async def test_tracker_without_state_feature_degrades_to_stateless(self, tmp_path):
        """'state' feature 없는 실제 트래커: load_state→None, save_state→False — 크래시 없이 무상태."""
        tracker = self._real_tracker(tmp_path, features=frozenset())
        r = await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": 100, "market_code": "82"}],
            fields={"max_hold_days": 5}, context=self._ctx(tracker),
        )
        assert r["symbol_results"][0]["hold_days"] == 0
        assert tracker.load_state("time_exit.AAPL.entry_date") is None

    @pytest.mark.asyncio
    async def test_foreign_tracker_variant_degrades_instead_of_crashing(self):
        """load/save/delete_state 가 없는 트래커 변종 → 상태 경로를 켜지 않는다(크래시 금지)."""
        class Foreign:
            def get_state(self, key):  # 옛 이름 — 실제 트래커엔 없다
                raise AssertionError("must not be called")
        r = await time_based_exit_condition(
            positions=[{"symbol": "AAPL", "qty": 100, "market_code": "82"}],
            fields={"max_hold_days": 5}, context=MockContext(Foreign()),
        )
        assert r["symbol_results"][0]["hold_days"] == 0
