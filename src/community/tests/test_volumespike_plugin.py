"""
VolumeSpike 플러그인 테스트

새 형식(data-based) 테스트
"""

import asyncio
import pytest

from programgarden_community.plugins.volume_spike import (
    volume_spike_condition,
    VOLUME_SPIKE_SCHEMA,
)


class TestVolumeSpikePlugin:
    """VolumeSpike 플러그인 테스트"""

    @pytest.fixture
    def mock_symbols(self):
        """테스트용 종목 리스트"""
        return [
            {"symbol": "AAPL", "exchange": "NASDAQ"},
            {"symbol": "NVDA", "exchange": "NASDAQ"},
            {"symbol": "TSLA", "exchange": "NASDAQ"},
            {"symbol": "MSFT", "exchange": "NASDAQ"},
        ]

    @pytest.fixture
    def mock_data_spike(self):
        """평탄화된 배열 - 일부 종목이 급증"""
        data = []
        # AAPL: 평균 100만, 마지막일 250만 (2.5배) -> 급증
        for i in range(21):
            vol = 2500000 if i == 20 else 1000000
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}", "volume": vol, "close": 180 + i
            })
        # NVDA: 평균 200만, 마지막일 500만 (2.5배) -> 급증
        for i in range(21):
            vol = 5000000 if i == 20 else 2000000
            data.append({
                "symbol": "NVDA", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}", "volume": vol, "close": 450 + i
            })
        # TSLA: 평균 300만, 마지막일 400만 (1.33배) -> 정상
        for i in range(21):
            vol = 4000000 if i == 20 else 3000000
            data.append({
                "symbol": "TSLA", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}", "volume": vol, "close": 250 + i
            })
        # MSFT: 평균 150만, 마지막일 150만 (1.0배) -> 정상
        for i in range(21):
            data.append({
                "symbol": "MSFT", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}", "volume": 1500000, "close": 400 + i
            })
        return data

    @pytest.fixture
    def mock_data_no_spike(self):
        """모든 종목 정상 거래량"""
        data = []
        for sym, base_vol in [("AAPL", 1000000), ("NVDA", 2000000), ("TSLA", 3000000), ("MSFT", 1500000)]:
            for i in range(21):
                vol = int(base_vol * 1.1) if i == 20 else base_vol
                data.append({
                    "symbol": sym, "exchange": "NASDAQ",
                    "date": f"202501{i+1:02d}", "volume": vol, "close": 100 + i
                })
        return data

    @pytest.fixture  
    def mock_data_all_spike(self):
        """모든 종목 급증"""
        data = []
        for sym, base_vol in [("AAPL", 1000000), ("NVDA", 2000000), ("TSLA", 3000000), ("MSFT", 1500000)]:
            for i in range(21):
                vol = base_vol * 3 if i == 20 else base_vol
                data.append({
                    "symbol": sym, "exchange": "NASDAQ",
                    "date": f"202501{i+1:02d}", "volume": vol, "close": 100 + i
                })
        return data

    @pytest.mark.asyncio
    async def test_partial_spike(self, mock_symbols, mock_data_spike):
        """일부 종목만 거래량 급증"""
        result = await volume_spike_condition(
            data=mock_data_spike,
            symbols=mock_symbols,
            fields={"period": 20, "multiplier": 2.0},
        )

        passed_syms = [s["symbol"] for s in result["passed_symbols"]]
        failed_syms = [s["symbol"] for s in result["failed_symbols"]]
        
        assert "AAPL" in passed_syms
        assert "NVDA" in passed_syms
        assert "TSLA" in failed_syms
        assert "MSFT" in failed_syms
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_no_spike(self, mock_symbols, mock_data_no_spike):
        """모든 종목 정상"""
        result = await volume_spike_condition(
            data=mock_data_no_spike,
            symbols=mock_symbols,
            fields={"period": 20, "multiplier": 2.0},
        )

        assert len(result["passed_symbols"]) == 0
        assert len(result["failed_symbols"]) == 4
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_all_spike(self, mock_symbols, mock_data_all_spike):
        """모든 종목 급증"""
        result = await volume_spike_condition(
            data=mock_data_all_spike,
            symbols=mock_symbols,
            fields={"period": 20, "multiplier": 2.0},
        )

        assert len(result["passed_symbols"]) == 4
        assert len(result["failed_symbols"]) == 0
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_symbol_results_format(self, mock_symbols, mock_data_spike):
        """symbol_results 형식 확인"""
        result = await volume_spike_condition(
            data=mock_data_spike,
            symbols=mock_symbols,
            fields={"period": 20, "multiplier": 2.0},
        )

        for sr in result["symbol_results"]:
            assert "symbol" in sr
            assert "exchange" in sr
            assert "current_volume" in sr
            assert "avg_volume" in sr
            assert "ratio" in sr
            assert "passed" in sr

    @pytest.mark.asyncio
    async def test_values_time_series_format(self, mock_symbols, mock_data_spike):
        """values의 time_series 형식 확인"""
        result = await volume_spike_condition(
            data=mock_data_spike,
            symbols=mock_symbols,
            fields={"period": 20, "multiplier": 1.5},
        )

        assert len(result["values"]) == 4
        for val in result["values"]:
            assert "symbol" in val
            assert "exchange" in val
            assert "time_series" in val
            assert len(val["time_series"]) == 21
            
            for row in val["time_series"]:
                assert "date" in row
                assert "volume" in row
                assert "avg_volume" in row
                assert "ratio" in row
                assert "spike" in row

    @pytest.mark.asyncio
    async def test_auto_extract_symbols(self, mock_data_spike):
        """symbols 없이 data에서 자동 추출"""
        result = await volume_spike_condition(
            data=mock_data_spike,
            fields={"period": 20, "multiplier": 2.0},
        )

        assert len(result["symbol_results"]) == 4

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await volume_spike_condition(
            data=[],
            fields={"period": 20, "multiplier": 2.0},
        )

        assert len(result["passed_symbols"]) == 0
        assert result["result"] is False

    def test_schema(self):
        """스키마 검증"""
        assert VOLUME_SPIKE_SCHEMA.id == "VolumeSpike"
        assert VOLUME_SPIKE_SCHEMA.version == "3.0.0"
        assert "period" in VOLUME_SPIKE_SCHEMA.fields_schema
        assert "multiplier" in VOLUME_SPIKE_SCHEMA.fields_schema


def run_quick_test():
    """빠른 테스트 실행"""
    print("=" * 60)
    print("VolumeSpike 플러그인 테스트")
    print("=" * 60)

    async def _test():
        # 테스트 데이터 생성
        data = []
        for sym, base_vol, spike_vol in [
            ("AAPL", 1000000, 2500000),
            ("NVDA", 2000000, 5000000),
            ("TSLA", 3000000, 4000000),
            ("MSFT", 1500000, 1500000),
        ]:
            for i in range(21):
                vol = spike_vol if i == 20 else base_vol
                data.append({
                    "symbol": sym, "exchange": "NASDAQ",
                    "date": f"202501{i+1:02d}", "volume": vol, "close": 100 + i
                })
        
        symbols = [
            {"symbol": "AAPL", "exchange": "NASDAQ"},
            {"symbol": "NVDA", "exchange": "NASDAQ"},
            {"symbol": "TSLA", "exchange": "NASDAQ"},
            {"symbol": "MSFT", "exchange": "NASDAQ"},
        ]
        
        print("\n[테스트] multiplier=2.0")
        print("-" * 40)
        
        result = await volume_spike_condition(
            data=data,
            symbols=symbols,
            fields={"period": 20, "multiplier": 2.0},
        )
        
        passed = [s["symbol"] for s in result["passed_symbols"]]
        failed = [s["symbol"] for s in result["failed_symbols"]]
        print(f"✅ 급증: {passed}")
        print(f"❌ 정상: {failed}")
        
        print("\n📊 symbol_results:")
        for sr in result["symbol_results"]:
            status = "📈" if sr["passed"] else "📊"
            print(f"  {sr['symbol']}: {sr['current_volume']:,} / {sr['avg_volume']:,.0f} = {sr['ratio']}배 {status}")
        
        print("\n📈 time_series (AAPL 마지막 3일):")
        aapl_values = next((v for v in result["values"] if v["symbol"] == "AAPL"), None)
        if aapl_values:
            for row in aapl_values["time_series"][-3:]:
                spike_mark = "🔥" if row["spike"] else ""
                print(f"  {row['date']}: vol={row['volume']:,}, ratio={row['ratio']} {spike_mark}")
        
        print("\n" + "=" * 60)
        print("✅ 완료!")
        print("=" * 60)

    asyncio.run(_test())


if __name__ == "__main__":
    run_quick_test()
