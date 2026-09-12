"""
BetaHedge (베타 헷지) 플러그인 테스트

상태(strategy_state)·이벤트 경로 — 2026-09-12 수정
------------------------------------------------------------------------------------------
``FakeRiskTracker`` 는 실제 트래커 ``programgarden.database.workflow_risk_tracker.
WorkflowRiskTracker`` 의 **실제 시그니처**(``load_state``/``save_state``/``delete_state``/
``record_risk_event`` — 전부 동기)를 흉내낸다. 종전 목은 실제 클래스에 없는
``get_state``/``set_state``/``record_event`` 를 제공해, 테스트는 통과하는데 라이브에서는
except 가 AttributeError 를 삼켜 상태도 이벤트도 한 건도 기록되지 않았다.
``TestLiveStatePathIsAlive`` 가 **실제 트래커 인스턴스**로 그 사실을 고정한다.
"""

import pytest
from programgarden_community.plugins.beta_hedge import (
    beta_hedge_condition,
    BETA_HEDGE_SCHEMA,
    _calculate_beta,
    _calculate_returns,
)


class FakeRiskTracker:
    """실제 WorkflowRiskTracker 의 state/events 인터페이스와 같은 이름·동기 규약의 fake."""

    def __init__(self):
        self.state = {}
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
    def __init__(self):
        self.risk_tracker = FakeRiskTracker()


def _market_data():
    """SPY + 고베타(TSLA) + 저베타(JNJ) — 클래스 픽스처 mock_data_with_market 와 같은 데이터"""
    data = []
    spy_price, tsla_price, jnj_price = 450.0, 200.0, 160.0
    for i in range(130):
        market_move = 0.005 if i % 3 < 2 else -0.003
        spy_price *= (1 + market_move)
        tsla_price *= (1 + market_move * 2.0 + 0.001)
        jnj_price *= (1 + market_move * 0.5 + 0.0005)
        date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
        data.append({"symbol": "SPY", "exchange": "NYSE", "date": date, "close": round(spy_price, 2)})
        data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
        data.append({"symbol": "JNJ", "exchange": "NYSE", "date": date, "close": round(jnj_price, 2)})
    return data


class TestBetaHedgePlugin:
    """BetaHedge 플러그인 테스트"""

    @pytest.fixture
    def mock_data_with_market(self):
        """SPY + 고베타(TSLA) + 저베타(JNJ) 3종목"""
        data = []
        spy_price, tsla_price, jnj_price = 450.0, 200.0, 160.0
        for i in range(130):
            # SPY: 기본 시장 움직임
            market_move = 0.005 if i % 3 < 2 else -0.003
            spy_price *= (1 + market_move)
            # TSLA: 고베타 (시장의 2배 움직임)
            tsla_price *= (1 + market_move * 2.0 + 0.001)
            # JNJ: 저베타 (시장의 0.5배 움직임)
            jnj_price *= (1 + market_move * 0.5 + 0.0005)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "SPY", "exchange": "NYSE", "date": date, "close": round(spy_price, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla_price, 2)})
            data.append({"symbol": "JNJ", "exchange": "NYSE", "date": date, "close": round(jnj_price, 2)})
        return data

    @pytest.fixture
    def mock_data_no_market(self):
        """시장 심볼 없는 데이터"""
        data = []
        price = 150.0
        for i in range(130):
            price *= 1.005 if i % 2 == 0 else 0.995
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "AAPL", "exchange": "NASDAQ", "date": date, "close": round(price, 2)})
        return data

    @pytest.fixture
    def mock_positions(self):
        return [
            {"symbol": "TSLA", "current_price": 250.0, "qty": 100},
            {"symbol": "JNJ", "current_price": 165.0, "qty": 200},
        ]

    # === 스키마 테스트 ===
    def test_schema_id(self):
        assert BETA_HEDGE_SCHEMA.id == "BetaHedge"

    def test_schema_category(self):
        assert BETA_HEDGE_SCHEMA.category == "position"

    def test_schema_fields(self):
        fields = BETA_HEDGE_SCHEMA.fields_schema
        assert "market_symbol" in fields
        assert "target_beta" in fields
        assert "hedge_method" in fields
        assert fields["lookback"]["default"] == 120

    # === 헬퍼 함수 테스트 ===
    def test_calculate_returns(self):
        prices = [100, 105, 103, 108]
        returns = _calculate_returns(prices)
        assert len(returns) == 3
        assert abs(returns[0] - 0.05) < 0.001

    def test_calculate_returns_empty(self):
        assert _calculate_returns([]) == []
        assert _calculate_returns([100]) == []

    def test_calculate_beta_market_itself(self):
        """시장 자체의 베타 = 1.0"""
        market_returns = [0.01, -0.005, 0.008, -0.003, 0.012, -0.007, 0.005, 0.003, -0.01, 0.006]
        beta = _calculate_beta(market_returns, market_returns)
        assert abs(beta - 1.0) < 0.001

    def test_calculate_beta_high_beta(self):
        """고베타 주식 (시장의 2배 움직임)"""
        market_returns = [0.01, -0.005, 0.008, -0.003, 0.012, -0.007, 0.005, 0.003, -0.01, 0.006]
        stock_returns = [r * 2 for r in market_returns]
        beta = _calculate_beta(stock_returns, market_returns)
        assert abs(beta - 2.0) < 0.001

    def test_calculate_beta_insufficient(self):
        assert _calculate_beta([0.01], [0.01]) == 0.0

    # === 조건 평가 테스트 ===
    @pytest.mark.asyncio
    async def test_basic_beta_calculation(self, mock_data_with_market):
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={"lookback": 120, "market_symbol": "SPY"},
        )
        assert len(result["symbol_results"]) == 2  # TSLA, JNJ (SPY 제외)
        tsla = next(sr for sr in result["symbol_results"] if sr["symbol"] == "TSLA")
        jnj = next(sr for sr in result["symbol_results"] if sr["symbol"] == "JNJ")
        # TSLA 베타 > JNJ 베타
        assert tsla["beta"] > jnj["beta"]

    @pytest.mark.asyncio
    async def test_portfolio_beta_with_positions(self, mock_data_with_market, mock_positions):
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=mock_positions,
        )
        assert "portfolio_beta" in result["analysis"]
        assert result["analysis"]["portfolio_beta"] != 0

    @pytest.mark.asyncio
    async def test_hedge_needed_detection(self, mock_data_with_market):
        """목표 베타를 매우 낮게 설정 → 헷지 필요"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
            },
        )
        assert result["analysis"]["hedge_needed"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_no_hedge_needed(self, mock_data_with_market):
        """넓은 tolerance → 헷지 불필요"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 1.0, "beta_tolerance": 5.0,
            },
        )
        assert result["analysis"]["hedge_needed"] is False
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_inverse_etf_recommendation(self, mock_data_with_market):
        """인버스 ETF 헷지 추천"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
                "hedge_method": "long_inverse_etf", "inverse_etf_symbol": "SH",
            },
        )
        if result["analysis"]["hedge_needed"]:
            assert "hedge_recommendation" in result
            rec = result["hedge_recommendation"]
            assert rec["action"] == "buy_inverse_etf"
            assert rec["inverse_etf"] == "SH"
            assert rec["suggested_allocation_pct"] > 0

    @pytest.mark.asyncio
    async def test_reduce_high_beta_recommendation(self, mock_data_with_market):
        """고베타 종목 축소 추천"""
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
                "hedge_method": "reduce_high_beta",
            },
        )
        if result["analysis"]["hedge_needed"]:
            assert "hedge_recommendation" in result
            rec = result["hedge_recommendation"]
            assert rec["action"] == "reduce_high_beta"
            assert rec["target_symbol"] == "TSLA"  # 가장 높은 베타

    @pytest.mark.asyncio
    async def test_market_symbol_not_found(self, mock_data_no_market):
        """시장 심볼 누락 → 에러"""
        result = await beta_hedge_condition(
            data=mock_data_no_market,
            fields={"lookback": 120, "market_symbol": "SPY"},
        )
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_risk_event_recording(self, mock_data_with_market):
        ctx = MockContext()
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={
                "lookback": 120, "market_symbol": "SPY",
                "target_beta": 0.0, "beta_tolerance": 0.1,
            },
            context=ctx,
        )
        if result["analysis"]["hedge_needed"]:
            assert len(ctx.risk_tracker.events) > 0
            assert ctx.risk_tracker.events[0]["event_type"] == "beta_deviation"
            assert ctx.risk_tracker.state.get("portfolio_beta") is not None

    @pytest.mark.asyncio
    async def test_empty_data(self):
        result = await beta_hedge_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, mock_data_with_market):
        result = await beta_hedge_condition(
            data=mock_data_with_market,
            fields={"lookback": 120, "market_symbol": "SPY", "target_beta": 0.8},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "BetaHedge"
        assert analysis["market_symbol"] == "SPY"
        assert analysis["target_beta"] == 0.8
        assert "portfolio_beta" in analysis
        assert "hedge_needed" in analysis


class TestBetaHedgeFractionalPosition:
    """소수 포지션 회귀 — 구 ``int(pos["qty"])`` 절단 (X3 전수확인에서 발견).

    ⚠️ 이 분기(positions 인자)는 워크플로우 실행기 경로에서는 도달하지 않는다 —
    실행기의 data 기반 분기가 plugin_kwargs 에 ``positions`` 를 넣지 않기 때문이다.
    여기서 검증하는 것은 라이브러리 직접 호출 경로와 계산식 자체다.
    """

    @staticmethod
    def _bars(n=130):
        data = []
        spy, tsla = 450.0, 200.0
        for i in range(n):
            move = 0.005 if i % 3 < 2 else -0.003
            spy *= (1 + move)
            tsla *= (1 + move * 2.0 + 0.001)
            date = f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}"
            data.append({"symbol": "SPY", "exchange": "NYSE", "date": date, "close": round(spy, 2)})
            data.append({"symbol": "TSLA", "exchange": "NASDAQ", "date": date, "close": round(tsla, 2)})
        return data

    @pytest.mark.asyncio
    @pytest.mark.parametrize("qty,price", [(0.532, 150.0), (1, 150.0), (10, 150.0)])
    async def test_weight_keeps_fractional_quantity(self, qty, price):
        """0.532주 x 150달러 = 79.8 — 수정 전에는 int(0.532)=0 이라 weight 가 0.0 이었다."""
        result = await beta_hedge_condition(
            data=self._bars(),
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=[{"symbol": "TSLA", "current_price": price, "qty": qty}],
        )
        tsla = next(r for r in result["symbol_results"] if r["symbol"] == "TSLA")
        assert tsla["weight"] == pytest.approx(price * qty, abs=0.01)
        assert "weight_unavailable_reason" not in tsla

    @pytest.mark.asyncio
    async def test_fractional_position_still_weights_portfolio_beta(self):
        """소수 포지션만 있어도 포트폴리오 베타가 0 으로 접히지 않는다.

        수정 전에는 총 포지션 가치가 0 이라 ``total_value > 0`` 가 거짓이 되어
        portfolio_beta 가 0 으로 떨어졌다.
        """
        result = await beta_hedge_condition(
            data=self._bars(),
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=[{"symbol": "TSLA", "current_price": 150.0, "qty": 0.532}],
        )
        assert result["analysis"]["portfolio_beta"] != 0

    @pytest.mark.asyncio
    async def test_unreadable_quantity_leaves_reason_and_does_not_crash(self):
        """문자열 쓰레기 수량 — 구 int() 는 ValueError 로 죽었다. 이제 사유를 남긴다."""
        result = await beta_hedge_condition(
            data=self._bars(),
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=[{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}],
        )
        tsla = next(r for r in result["symbol_results"] if r["symbol"] == "TSLA")
        assert "weight" not in tsla
        assert "포지션 금액을 계산할 수 없음" in tsla["weight_unavailable_reason"]


class TestBetaContributionSymmetry:
    """Z2 — weight 와 beta_contribution 은 **같은 두 값**(수량·가격)에서 나온다.

    구 코드는 weight 만 '못 읽으면 사유' 로 바꾸고, 바로 옆 beta_contribution 은
    ``pos_value > 0`` 이 거짓이라는 이유로 0 을 지어냈다 — 같은 회차 안에서
    "금액은 못 읽었는데 기여도는 0" 이라는 모순이 나왔다.
    """

    _bars = staticmethod(TestBetaHedgeFractionalPosition._bars)

    async def _run(self, positions):
        return await beta_hedge_condition(
            data=self._bars(),
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=positions,
        )

    @pytest.mark.asyncio
    async def test_unreadable_position_omits_contribution_with_reason(self):
        result = await self._run([{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}])
        tsla = next(r for r in result["symbol_results"] if r["symbol"] == "TSLA")
        assert "beta_contribution" not in tsla, "읽지 못한 값에서 기여도를 지어냈다"
        assert "포지션 금액을 계산할 수 없음" in tsla["beta_contribution_unavailable_reason"]
        # weight 와 정확히 같은 사유를 쓴다 — 두 필드의 가용성이 갈라지지 않는다
        assert tsla["beta_contribution_unavailable_reason"] == tsla["weight_unavailable_reason"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad", [{"qty": "n/a"}, {"current_price": "-"}, {"qty": None}])
    async def test_weight_and_contribution_are_available_together(self, bad):
        pos = {"symbol": "TSLA", "current_price": 150.0, "qty": 3}
        pos.update(bad)
        result = await self._run([pos])
        tsla = next(r for r in result["symbol_results"] if r["symbol"] == "TSLA")
        assert ("weight" in tsla) == ("beta_contribution" in tsla)
        assert (
            "weight_unavailable_reason" in tsla
        ) == ("beta_contribution_unavailable_reason" in tsla)

    @pytest.mark.asyncio
    async def test_readable_position_still_reports_contribution(self):
        result = await self._run([{"symbol": "TSLA", "current_price": 150.0, "qty": 0.532}])
        tsla = next(r for r in result["symbol_results"] if r["symbol"] == "TSLA")
        assert tsla["weight"] == pytest.approx(79.8, abs=0.01)
        assert tsla["beta_contribution"] == pytest.approx(tsla["beta"] * 79.8, abs=0.05)
        assert "beta_contribution_unavailable_reason" not in tsla

    @pytest.mark.asyncio
    async def test_readable_zero_value_keeps_contribution_zero(self):
        """수량 0 은 **읽은 값**이다 — beta x 0 = 0 은 계산 결과이지 지어낸 값이 아니다."""
        result = await self._run([{"symbol": "TSLA", "current_price": 150.0, "qty": 0}])
        tsla = next(r for r in result["symbol_results"] if r["symbol"] == "TSLA")
        assert tsla["weight"] == 0
        assert tsla["beta_contribution"] == 0
        assert "beta_contribution_unavailable_reason" not in tsla

    def test_schema_declares_the_reason(self):
        assert "beta_contribution_unavailable_reason" in BETA_HEDGE_SCHEMA.output_fields


class TestPortfolioBetaIsNotFabricated:
    """Z2 — 읽힌 포지션이 하나도 없어 total_value 가 0 이면 portfolio 값도 지어내지 않는다.

    구 코드는 ``weighted_beta / total_value if total_value > 0 else 0`` 으로 0 을
    실었고, 그 0 이 ``beta_deviation = 0 - target_beta`` 를 지나
    ``hedge_needed=True`` 라는 **거짓 신호**까지 만들었다(target_beta 기본 1.0,
    tolerance 0.2 에서 |−1.0| > 0.2).
    """

    _bars = staticmethod(TestBetaHedgeFractionalPosition._bars)

    async def _run(self, positions, **fields):
        f = {"lookback": 120, "market_symbol": "SPY"}
        f.update(fields)
        return await beta_hedge_condition(data=self._bars(), fields=f, positions=positions)

    @pytest.mark.asyncio
    async def test_all_positions_unreadable_leaves_reason(self):
        result = await self._run([{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}])
        analysis = result["analysis"]
        assert "portfolio_beta" not in analysis, "계산되지 않은 베타를 0 으로 실었다"
        assert "가중치 합" in analysis["portfolio_beta_unavailable_reason"]
        assert "TSLA" in analysis["portfolio_beta_unavailable_reason"]
        assert analysis["hedge_needed_undetermined"] is True
        assert analysis["hedge_needed"] is False
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_no_fabricated_hedge_signal(self):
        """구 코드에서는 여기서 hedge_needed=True 가 나왔다 (portfolio_beta 0 발)."""
        result = await self._run(
            [{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}],
            target_beta=1.0, beta_tolerance=0.2,
        )
        assert result["analysis"]["hedge_needed"] is False
        assert result["passed_symbols"] == []

    @pytest.mark.asyncio
    async def test_unavailable_portfolio_beta_is_not_put_in_time_series(self):
        result = await self._run([{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}])
        for v in result["values"]:
            for row in v["time_series"]:
                assert "portfolio_beta" not in row

    @pytest.mark.asyncio
    async def test_unavailable_portfolio_beta_is_not_saved_to_state(self):
        ctx = MockContext()
        await beta_hedge_condition(
            data=self._bars(),
            fields={"lookback": 120, "market_symbol": "SPY"},
            positions=[{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}],
            context=ctx,
        )
        assert "portfolio_beta" not in ctx.risk_tracker.state

    @pytest.mark.asyncio
    async def test_readable_position_still_reports_portfolio_beta(self):
        result = await self._run([{"symbol": "TSLA", "current_price": 150.0, "qty": 0.532}])
        assert result["analysis"]["portfolio_beta"] != 0
        assert "portfolio_beta_unavailable_reason" not in result["analysis"]
        assert "hedge_needed_undetermined" not in result["analysis"]

    @pytest.mark.asyncio
    async def test_no_positions_still_uses_equal_weight(self):
        """positions 자체가 없으면 종전대로 동일 비중 가정 — 사유 분기가 아니다."""
        result = await beta_hedge_condition(
            data=self._bars(), fields={"lookback": 120, "market_symbol": "SPY"},
        )
        assert "portfolio_beta" in result["analysis"]
        assert "portfolio_beta_unavailable_reason" not in result["analysis"]


class TestLiveStatePathIsAlive:
    """상태·이벤트 경로가 **실제 트래커로 실제로 돈다**는 것을 고정한다 (2026-09-12 수정).

    수정 전엔 set_state/record_event(없는 이름) → except 삼킴 → 상태 0건·이벤트 0건.
    """

    _HEDGE_FIELDS = {"lookback": 120, "market_symbol": "SPY", "target_beta": 0.0, "beta_tolerance": 0.1}

    @staticmethod
    def _real_tracker(tmp_path, features=frozenset({"state", "events"})):
        mod = pytest.importorskip(
            "programgarden.database.workflow_risk_tracker",
            reason="engine package not installed; live-truth pin skipped",
        )
        return mod.WorkflowRiskTracker(
            db_path=str(tmp_path / "rt.db"),
            job_id="pin", product="overseas_stock", provider="ls",
            trading_mode="real", features=set(features),
        )

    @staticmethod
    def _ctx(tracker):
        class RealCtx:
            risk_tracker = tracker
        return RealCtx()

    @pytest.mark.asyncio
    async def test_real_tracker_persists_portfolio_beta_as_float(self, tmp_path):
        tracker = self._real_tracker(tmp_path)
        result = await beta_hedge_condition(
            data=_market_data(), fields=dict(self._HEDGE_FIELDS), context=self._ctx(tracker),
        )
        assert result["analysis"]["hedge_needed"] is True  # 전제 (동일비중 beta ≈ 1.25 > 0.1)
        saved = tracker.load_state("portfolio_beta")
        assert isinstance(saved, float)  # 'float' 타입 왕복
        assert saved == result["analysis"]["portfolio_beta"]

    @pytest.mark.asyncio
    async def test_real_tracker_records_beta_deviation_event(self, tmp_path):
        import json
        tracker = self._real_tracker(tmp_path)
        result = await beta_hedge_condition(
            data=_market_data(), fields=dict(self._HEDGE_FIELDS), context=self._ctx(tracker),
        )
        events = tracker.get_risk_events(event_type="beta_deviation")
        assert len(events) == 1
        assert events[0]["symbol"] == "PORTFOLIO"
        details = json.loads(events[0]["details"])
        assert details["portfolio_beta"] == result["analysis"]["portfolio_beta"]
        assert details["target_beta"] == 0.0
        assert details["hedge_method"] == "long_inverse_etf"

    @pytest.mark.asyncio
    async def test_real_tracker_no_event_when_hedge_not_needed(self, tmp_path):
        tracker = self._real_tracker(tmp_path)
        result = await beta_hedge_condition(
            data=_market_data(),
            fields={"lookback": 120, "market_symbol": "SPY", "target_beta": 1.25, "beta_tolerance": 1.0},
            context=self._ctx(tracker),
        )
        assert result["analysis"]["hedge_needed"] is False
        assert tracker.get_risk_events(event_type="beta_deviation") == []
        assert isinstance(tracker.load_state("portfolio_beta"), float)  # 상태는 헷지 여부와 무관하게 저장

    @pytest.mark.asyncio
    async def test_real_tracker_unavailable_portfolio_beta_is_not_saved(self, tmp_path):
        """읽을 수 없는 포지션 → portfolio_beta None → 실제 트래커에도 저장하지 않는다."""
        tracker = self._real_tracker(tmp_path)
        await beta_hedge_condition(
            data=_market_data(), fields={"lookback": 120, "market_symbol": "SPY"},
            positions=[{"symbol": "TSLA", "current_price": 150.0, "qty": "n/a"}],
            context=self._ctx(tracker),
        )
        assert tracker.load_state("portfolio_beta") is None

    @pytest.mark.asyncio
    async def test_tracker_without_features_warns_instead_of_swallowing(self, tmp_path, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        tracker = self._real_tracker(tmp_path, features=frozenset())
        result = await beta_hedge_condition(
            data=_market_data(), fields=dict(self._HEDGE_FIELDS), context=self._ctx(tracker),
        )
        assert result["analysis"]["hedge_needed"] is True  # 판정 자체는 그대로
        messages = [r.message for r in caplog.records]
        assert any("BetaHedge: 상태 저장 실패" in m for m in messages)
        assert any("BetaHedge: 위험 이벤트 기록 실패" in m for m in messages)

    @pytest.mark.asyncio
    async def test_foreign_tracker_variant_degrades_instead_of_crashing(self):
        class Foreign:
            def set_state(self, key, value):  # 옛 이름 — 실제 트래커엔 없다
                raise AssertionError("must not be called")

            def record_event(self, **kw):
                raise AssertionError("must not be called")

        class Ctx:
            risk_tracker = Foreign()

        result = await beta_hedge_condition(data=_market_data(), fields=dict(self._HEDGE_FIELDS), context=Ctx())
        assert result["analysis"]["hedge_needed"] is True
