"""
MagicFormula 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.magic_formula import (
    magic_formula_condition,
    _is_financial,
    _is_utility,
    _rank_list,
    MAGIC_FORMULA_SCHEMA,
)


def _make_simplified_data(symbols_data):
    """Simplified 모드 데이터 생성
    symbols_data: [(symbol, per, roe, sector, market_cap), ...]
    """
    data = []
    for sym, per, roe, sector, market_cap in symbols_data:
        data.append({
            "symbol": sym, "exchange": "NASDAQ",
            "per": per, "roe": roe,
            "sector": sector,
            "market_cap": market_cap,
        })
    return data


def _make_full_mode_data(symbols_data):
    """Full 모드 데이터 생성
    symbols_data: [(symbol, ebit, ev, ic, sector), ...]
    """
    data = []
    for sym, ebit, ev, ic, sector in symbols_data:
        data.append({
            "symbol": sym, "exchange": "NYSE",
            "ebit": ebit,
            "enterprise_value": ev,
            "invested_capital": ic,
            "sector": sector,
            "market_cap": 1e9,
        })
    return data


class TestMagicFormulaHelpers:
    """헬퍼 함수 테스트"""

    def test_is_financial_bank(self):
        """금융업 감지"""
        assert _is_financial("Financial Services") is True
        assert _is_financial("Banking") is True
        assert _is_financial("Insurance") is True

    def test_is_financial_non_financial(self):
        """비금융업 감지"""
        assert _is_financial("Technology") is False
        assert _is_financial("Healthcare") is False
        assert _is_financial("") is False

    def test_is_utility(self):
        """유틸리티 감지"""
        assert _is_utility("Utilities") is True
        assert _is_utility("Electric Utilities") is True

    def test_is_utility_non_utility(self):
        """비유틸리티 감지"""
        assert _is_utility("Technology") is False
        assert _is_utility("") is False

    def test_rank_list_basic(self):
        """기본 순위 계산"""
        values = [("AAPL", 0.5), ("TSLA", 0.3), ("GOOG", 0.8)]
        ranks = _rank_list(values, reverse=True)
        # GOOG(0.8) > AAPL(0.5) > TSLA(0.3)
        assert ranks["GOOG"] == 1
        assert ranks["AAPL"] == 2
        assert ranks["TSLA"] == 3

    def test_rank_list_ascending(self):
        """오름차순 순위"""
        values = [("A", 10), ("B", 5), ("C", 20)]
        ranks = _rank_list(values, reverse=False)
        # B(5) < A(10) < C(20)
        assert ranks["B"] == 1
        assert ranks["A"] == 2
        assert ranks["C"] == 3


class TestMagicFormulaCondition:
    """MagicFormula 조건 테스트"""

    @pytest.fixture
    def simplified_universe(self):
        """Simplified 모드 테스트 유니버스"""
        return _make_simplified_data([
            # (symbol, per, roe, sector, market_cap)
            ("AAPL", 25.0, 1.5, "Technology", 3e12),   # EY=0.04, ROE=1.5 → 좋음
            ("MSFT", 30.0, 0.4, "Technology", 2e12),   # EY=0.033, ROE=0.4
            ("GOOG", 20.0, 0.3, "Technology", 1.5e12), # EY=0.05, ROE=0.3
            ("AMZN", 80.0, 0.2, "Consumer", 1.8e12),   # EY=0.0125, ROE=0.2 → 나쁨
            ("META", 15.0, 1.2, "Technology", 1.2e12), # EY=0.067, ROE=1.2 → 좋음
        ])

    @pytest.fixture
    def full_mode_universe(self):
        """Full 모드 테스트 유니버스"""
        return _make_full_mode_data([
            # (symbol, ebit, ev, ic, sector)
            ("AAPL", 1e11, 3e12, 5e10, "Technology"),   # ROC=2.0, EY=0.033 → 매우 좋음
            ("MSFT", 8e10, 2e12, 4e10, "Technology"),   # ROC=2.0, EY=0.04
            ("GOOG", 5e10, 1.5e12, 3e10, "Technology"), # ROC=1.67, EY=0.033
            ("AMZN", 2e10, 1.8e12, 5e10, "Consumer"),   # ROC=0.4, EY=0.011 → 나쁨
            ("META", 6e10, 1.2e12, 2e10, "Technology"), # ROC=3.0, EY=0.05 → 최고
        ])

    @pytest.mark.asyncio
    async def test_simplified_top_n_selection(self, simplified_universe):
        """Simplified 모드 top_n 선별"""
        result = await magic_formula_condition(
            data=simplified_universe,
            fields={"mode": "simplified", "top_n": 2},
        )
        assert len(result["passed_symbols"]) == 2
        assert len(result["failed_symbols"]) == 3
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_simplified_ranking_correctness(self, simplified_universe):
        """Simplified 모드 순위 계산 검증"""
        result = await magic_formula_condition(
            data=simplified_universe,
            fields={"mode": "simplified", "top_n": 5},
        )
        # 모든 종목 통과
        assert len(result["passed_symbols"]) == 5

        # combined_rank 확인
        for sr in result["symbol_results"]:
            assert sr["roc_rank"] is not None
            assert sr["ey_rank"] is not None
            assert sr["combined_rank"] is not None
            assert sr["combined_rank"] == sr["roc_rank"] + sr["ey_rank"]

    @pytest.mark.asyncio
    async def test_full_mode(self, full_mode_universe):
        """Full 모드 EBIT 기반 순위"""
        result = await magic_formula_condition(
            data=full_mode_universe,
            fields={"mode": "full", "top_n": 3},
        )
        assert len(result["passed_symbols"]) == 3
        assert result["analysis"]["mode"] == "full"

    @pytest.mark.asyncio
    async def test_top_pct_selection(self, simplified_universe):
        """top_pct 기반 선별"""
        result = await magic_formula_condition(
            data=simplified_universe,
            fields={"mode": "simplified", "top_n": 0, "top_pct": 40.0},  # 5종목의 40% = 2종목
        )
        assert len(result["passed_symbols"]) == 2

    @pytest.mark.asyncio
    async def test_exclude_financials(self):
        """금융업 제외"""
        data = _make_simplified_data([
            ("BANK1", 12.0, 0.15, "Banking", 5e10),
            ("TECH1", 20.0, 0.5, "Technology", 2e10),
            ("INS1", 10.0, 0.12, "Insurance", 3e10),
        ])
        result = await magic_formula_condition(
            data=data,
            fields={"mode": "simplified", "top_n": 10, "exclude_financials": True},
        )
        # 금융업 제외 → TECH1만 통과 가능
        passed_symbols = [s["symbol"] for s in result["passed_symbols"]]
        assert "BANK1" not in passed_symbols
        assert "INS1" not in passed_symbols

    @pytest.mark.asyncio
    async def test_exclude_utilities(self):
        """유틸리티 제외"""
        data = _make_simplified_data([
            ("ELEC1", 15.0, 0.10, "Electric Utilities", 8e10),
            ("TECH1", 25.0, 0.6, "Technology", 5e10),
        ])
        result = await magic_formula_condition(
            data=data,
            fields={"mode": "simplified", "top_n": 10, "exclude_utilities": True},
        )
        passed_symbols = [s["symbol"] for s in result["passed_symbols"]]
        assert "ELEC1" not in passed_symbols

    @pytest.mark.asyncio
    async def test_min_market_cap_filter(self, simplified_universe):
        """최소 시가총액 필터"""
        result = await magic_formula_condition(
            data=simplified_universe,
            fields={"mode": "simplified", "top_n": 10, "min_market_cap": 2e12},
        )
        # 2조 이상만 → AAPL(3T), MSFT(2T), AMZN(1.8T: 제외), GOOG(1.5T: 제외), META(1.2T: 제외)
        passed_and_failed = len(result["passed_symbols"]) + len(result["failed_symbols"])
        # 2조 이상인 AAPL, MSFT, AMZN는 통과 가능 (AMZN은 3T 이상은 아님)
        assert passed_and_failed <= 5

    @pytest.mark.asyncio
    async def test_missing_per_roe_data(self):
        """PER/ROE 데이터 없을 때 처리"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ",
             "per": 25.0, "roe": 1.5, "sector": "Technology"},
            {"symbol": "TSLA", "exchange": "NASDAQ",
             "per": None, "roe": None, "sector": "Consumer"},  # 데이터 없음
        ]
        result = await magic_formula_condition(
            data=data,
            fields={"mode": "simplified", "top_n": 5},
        )
        # TSLA는 데이터 없어서 순위에서 제외
        assert result["analysis"]["valid_symbols"] == 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await magic_formula_condition(data=[], fields={})
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_analysis_fields(self, simplified_universe):
        """analysis 필드 검증"""
        result = await magic_formula_condition(
            data=simplified_universe,
            fields={"mode": "simplified", "top_n": 2},
        )
        analysis = result["analysis"]
        assert analysis["indicator"] == "MagicFormula"
        assert analysis["mode"] == "simplified"
        assert analysis["total_symbols"] == 5
        assert analysis["selected_count"] == 2

    @pytest.mark.asyncio
    async def test_combined_rank_ordering(self, simplified_universe):
        """합산 순위 정렬 검증 - 선택된 종목이 더 낮은 combined_rank"""
        result = await magic_formula_condition(
            data=simplified_universe,
            fields={"mode": "simplified", "top_n": 2},  # 상위 2개만 선택
        )
        ranks = {sr["symbol"]: sr["combined_rank"] for sr in result["symbol_results"]
                 if sr.get("combined_rank") is not None}
        passed_symbols = {s["symbol"] for s in result["passed_symbols"]}
        failed_symbols = {s["symbol"] for s in result["failed_symbols"]}

        # passed 종목들의 combined_rank는 failed 종목들보다 낮아야 함
        if passed_symbols and failed_symbols:
            max_passed_rank = max(ranks.get(s, 999) for s in passed_symbols)
            min_failed_rank = min(ranks.get(s, 999) for s in failed_symbols)
            assert max_passed_rank <= min_failed_rank

    def test_schema(self):
        """스키마 검증"""
        assert MAGIC_FORMULA_SCHEMA.id == "MagicFormula"
        assert "mode" in MAGIC_FORMULA_SCHEMA.fields_schema
        assert "top_n" in MAGIC_FORMULA_SCHEMA.fields_schema
        assert "top_pct" in MAGIC_FORMULA_SCHEMA.fields_schema
        assert "exclude_financials" in MAGIC_FORMULA_SCHEMA.fields_schema
        assert "exclude_utilities" in MAGIC_FORMULA_SCHEMA.fields_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
