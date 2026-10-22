"""
PairTrading (페어 트레이딩) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.pair_trading import (
    pair_trading_condition,
    _pearson_correlation,
    _calculate_spread,
    PAIR_TRADING_SCHEMA,
    risk_features,
)


def _make_correlated_pair(days=70, correlation="high"):
    """상관 페어 데이터 생성"""
    data = []
    for i in range(days):
        close_a = 100 + i * 0.5 + (i % 3 - 1) * 0.3
        if correlation == "high":
            close_b = 200 + i * 1.0 + (i % 3 - 1) * 0.5
        elif correlation == "diverged":
            # 최근 스프레드 확대
            if i < days - 10:
                close_b = 200 + i * 1.0 + (i % 3 - 1) * 0.5
            else:
                close_b = 200 + i * 1.0 - (i - (days - 10)) * 3
        else:  # low
            close_b = 200 + (i % 7 - 3) * 5
        data.append({
            "symbol": "AAPL", "exchange": "NASDAQ",
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": close_a,
        })
        data.append({
            "symbol": "MSFT", "exchange": "NASDAQ",
            "date": f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}",
            "close": close_b,
        })
    return data


class TestPairTradingPlugin:
    """PairTrading 플러그인 테스트"""

    @pytest.fixture
    def correlated_data(self):
        """높은 상관 페어"""
        return _make_correlated_pair(70, "high")

    @pytest.fixture
    def diverged_data(self):
        """스프레드 확대 페어"""
        return _make_correlated_pair(70, "diverged")

    @pytest.fixture
    def uncorrelated_data(self):
        """낮은 상관 페어"""
        return _make_correlated_pair(70, "low")

    def test_pearson_correlation(self):
        """피어슨 상관계수"""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        corr = _pearson_correlation(x, y)
        assert abs(corr - 1.0) < 0.001

    def test_pearson_negative(self):
        """음의 상관"""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        corr = _pearson_correlation(x, y)
        assert abs(corr - (-1.0)) < 0.001

    def test_calculate_spread_ratio(self):
        """스프레드 계산 - ratio"""
        sp = _calculate_spread(100, 200, "ratio")
        assert sp == pytest.approx(0.5)

    def test_calculate_spread_log_ratio(self):
        """스프레드 계산 - log_ratio"""
        sp = _calculate_spread(100, 100, "log_ratio")
        assert sp == pytest.approx(0.0)

    def test_calculate_spread_difference(self):
        """스프레드 계산 - difference"""
        sp = _calculate_spread(100, 200, "difference")
        assert sp == pytest.approx(-100.0)

    @pytest.mark.asyncio
    async def test_correlated_pair(self, correlated_data):
        """상관 높은 페어 분석"""
        result = await pair_trading_condition(
            data=correlated_data,
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60},
        )
        assert "symbol_results" in result
        assert len(result["symbol_results"]) == 2
        assert result["symbol_results"][0]["correlation"] > 0.5

    @pytest.mark.asyncio
    async def test_auto_detect_symbols(self, correlated_data):
        """종목 자동 감지"""
        result = await pair_trading_condition(
            data=correlated_data,
            fields={"lookback": 60},  # symbol_a/b 미지정
        )
        assert "symbol_results" in result
        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_low_correlation_rejected(self, uncorrelated_data):
        """낮은 상관 페어 거부"""
        result = await pair_trading_condition(
            data=uncorrelated_data,
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60, "correlation_min": 0.8},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await pair_trading_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_output(self, correlated_data):
        """분석 결과 포맷"""
        result = await pair_trading_condition(
            data=correlated_data,
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60},
        )
        assert result["analysis"]["indicator"] == "PairTrading"
        assert "z_score" in result["analysis"]
        assert "correlation" in result["analysis"]

    def test_risk_features(self):
        """risk_features 선언"""
        assert "state" in risk_features

    def test_schema(self):
        """스키마 검증"""
        assert PAIR_TRADING_SCHEMA.id == "PairTrading"
        assert "symbol_a" in PAIR_TRADING_SCHEMA.fields_schema
        assert "symbol_b" in PAIR_TRADING_SCHEMA.fields_schema
        assert "entry_z" in PAIR_TRADING_SCHEMA.fields_schema
        assert "spread_method" in PAIR_TRADING_SCHEMA.fields_schema


class TestLiveStatePathIsAlive:
    """상태 경로가 **실제 트래커로 실제로 돈다**는 것을 고정한다 (2026-09-12 수정).

    수정 전에는 실제 트래커에 없는 ``set_state`` 를 불러 except 가 AttributeError 를
    삼켰고, 그래서 신호 이력이 **한 번도 저장되지 않았다**. 여기서는 실제
    ``WorkflowRiskTracker`` 인스턴스(sqlite, tmp_path)로 왕복해 저장·직렬화를 본다.
    """

    @staticmethod
    def _real_tracker(tmp_path, features=frozenset({"state"})):
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
    async def test_real_tracker_persists_last_signal_as_string(self, tmp_path):
        """entry_z=1.0 / exit_z=2.0 이면 z 가 무엇이든 신호가 난다 → 저장값 == analysis.signal."""
        tracker = self._real_tracker(tmp_path)
        result = await pair_trading_condition(
            data=_make_correlated_pair(70, "diverged"),
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60,
                    "entry_z": 1.0, "exit_z": 2.0, "correlation_min": 0.0},
            context=self._ctx(tracker),
        )
        signal = result["analysis"]["signal"]
        assert signal in {"short_a_long_b", "long_a_short_b", "exit"}
        saved = tracker.load_state("pair_AAPL_MSFT")
        assert saved == signal
        assert isinstance(saved, str)  # 'string' 타입 왕복

    @pytest.mark.asyncio
    async def test_real_tracker_overwrites_signal_on_next_cycle(self, tmp_path):
        tracker = self._real_tracker(tmp_path)
        tracker.save_state("pair_AAPL_MSFT", "stale_signal")
        await pair_trading_condition(
            data=_make_correlated_pair(70, "diverged"),
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60,
                    "entry_z": 1.0, "exit_z": 2.0, "correlation_min": 0.0},
            context=self._ctx(tracker),
        )
        assert tracker.load_state("pair_AAPL_MSFT") != "stale_signal"

    @pytest.mark.asyncio
    async def test_tracker_without_state_feature_warns_instead_of_swallowing(self, tmp_path, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        tracker = self._real_tracker(tmp_path, features=frozenset())
        result = await pair_trading_condition(
            data=_make_correlated_pair(70, "diverged"),
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60,
                    "entry_z": 1.0, "exit_z": 2.0, "correlation_min": 0.0},
            context=self._ctx(tracker),
        )
        assert result["analysis"]["signal"] is not None  # 판정 자체는 그대로
        assert tracker.load_state("pair_AAPL_MSFT") is None
        assert any("PairTrading: 상태 저장 실패" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_foreign_tracker_variant_degrades_instead_of_crashing(self):
        class Foreign:
            def set_state(self, key, value):  # 옛 이름 — 실제 트래커엔 없다
                raise AssertionError("must not be called")

        class Ctx:
            risk_tracker = Foreign()

        result = await pair_trading_condition(
            data=_make_correlated_pair(70, "diverged"),
            fields={"symbol_a": "AAPL", "symbol_b": "MSFT", "lookback": 60,
                    "entry_z": 1.0, "exit_z": 2.0, "correlation_min": 0.0},
            context=Ctx(),
        )
        assert result["analysis"]["signal"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
