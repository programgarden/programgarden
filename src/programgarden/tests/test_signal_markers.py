"""DisplayNode 시그널 마커 통합 테스트"""

import pytest
from programgarden.executor import DisplayNodeExecutor


@pytest.fixture
def executor():
    return DisplayNodeExecutor()


class TestExtractSignals:
    """_extract_signals 메서드 테스트"""

    def test_stock_signals_long_only(self, executor):
        """해외주식 RSI 시그널 (롱 전용, side 미지정)"""
        stock_data = [
            {"date": "20250110", "close": 185.0, "rsi": 45.0, "signal": None, "symbol": "AAPL"},
            {"date": "20250111", "close": 180.0, "rsi": 28.5, "signal": "buy", "symbol": "AAPL"},
            {"date": "20250112", "close": 190.0, "rsi": 55.0, "signal": None, "symbol": "AAPL"},
            {"date": "20250113", "close": 195.0, "rsi": 72.0, "signal": "sell", "symbol": "AAPL"},
            {"date": "20250114", "close": 192.0, "rsi": 60.0, "signal": None, "symbol": "AAPL"},
        ]

        signals = executor._extract_signals(
            data=stock_data,
            x_field="date",
            signal_field="signal",
            side_field=None,  # side 미지정 -> long 기본값
            series_key="symbol",
        )

        assert len(signals) == 2, f"Expected 2 signals, got {len(signals)}"
        assert signals[0]["marker"] == "[B:L]", f"Expected '[B:L]', got {signals[0]['marker']}"
        assert signals[0]["side"] == "long"
        assert signals[1]["marker"] == "[S:L]", f"Expected '[S:L]', got {signals[1]['marker']}"
        assert signals[1]["side"] == "long"

    def test_futures_signals_long_short_mixed(self, executor):
        """해외선물 MACD 시그널 (롱/숏 혼합)"""
        futures_data = [
            {"date": "20250110", "close": 21500, "signal": "buy", "side": "long", "symbol": "HSIG26"},
            {"date": "20250111", "close": 21800, "signal": None, "side": "long", "symbol": "HSIG26"},
            {"date": "20250112", "close": 21600, "signal": "sell", "side": "long", "symbol": "HSIG26"},
            {"date": "20250113", "close": 21400, "signal": "sell", "side": "short", "symbol": "HSIG26"},
            {"date": "20250114", "close": 21200, "signal": None, "side": "short", "symbol": "HSIG26"},
            {"date": "20250115", "close": 21500, "signal": "buy", "side": "short", "symbol": "HSIG26"},
        ]

        signals = executor._extract_signals(
            data=futures_data,
            x_field="date",
            signal_field="signal",
            side_field="side",
            series_key="symbol",
        )

        assert len(signals) == 4, f"Expected 4 signals, got {len(signals)}"
        assert signals[0]["marker"] == "[B:L]", "First should be buy_long"
        assert signals[1]["marker"] == "[S:L]", "Second should be sell_long"
        assert signals[2]["marker"] == "[S:S]", "Third should be sell_short"
        assert signals[3]["marker"] == "[B:S]", "Fourth should be buy_short"

    def test_multi_line_multiple_symbols(self, executor):
        """multi_line 다중 종목 시그널"""
        multi_data = [
            {"date": "20250110", "close": 185.0, "signal": "buy", "symbol": "AAPL"},
            {"date": "20250110", "close": 450.0, "signal": None, "symbol": "NVDA"},
            {"date": "20250111", "close": 190.0, "signal": None, "symbol": "AAPL"},
            {"date": "20250111", "close": 460.0, "signal": "buy", "symbol": "NVDA"},
            {"date": "20250112", "close": 195.0, "signal": "sell", "symbol": "AAPL"},
            {"date": "20250112", "close": 455.0, "signal": "sell", "symbol": "NVDA"},
        ]

        signals = executor._extract_signals(
            data=multi_data,
            x_field="date",
            signal_field="signal",
            side_field=None,
            series_key="symbol",
        )

        assert len(signals) == 4, f"Expected 4 signals, got {len(signals)}"
        
        aapl_signals = [s for s in signals if s["series"] == "AAPL"]
        nvda_signals = [s for s in signals if s["series"] == "NVDA"]
        
        assert len(aapl_signals) == 2, "AAPL should have 2 signals"
        assert len(nvda_signals) == 2, "NVDA should have 2 signals"

    def test_no_signal_field_returns_empty(self, executor):
        """signal_field 미지정 시 빈 배열 반환"""
        data = [
            {"date": "20250110", "close": 185.0, "symbol": "AAPL"},
            {"date": "20250111", "close": 190.0, "symbol": "AAPL"},
        ]

        signals = executor._extract_signals(
            data=data,
            x_field="date",
            signal_field=None,
            side_field=None,
            series_key="symbol",
        )

        assert len(signals) == 0, "Should return empty list when signal_field is None"

    def test_signal_markers_mapping(self, executor):
        """4종 마커 매핑 정확성 확인"""
        data = [
            {"date": "20250110", "signal": "buy", "side": "long", "symbol": "TEST"},
            {"date": "20250111", "signal": "sell", "side": "long", "symbol": "TEST"},
            {"date": "20250112", "signal": "sell", "side": "short", "symbol": "TEST"},
            {"date": "20250113", "signal": "buy", "side": "short", "symbol": "TEST"},
        ]

        signals = executor._extract_signals(
            data=data,
            x_field="date",
            signal_field="signal",
            side_field="side",
            series_key="symbol",
        )

        expected_markers = ["[B:L]", "[S:L]", "[S:S]", "[B:S]"]
        actual_markers = [s["marker"] for s in signals]
        
        assert actual_markers == expected_markers, f"Expected {expected_markers}, got {actual_markers}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
