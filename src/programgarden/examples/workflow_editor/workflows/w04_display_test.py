"""
DisplayNode 테스트 워크플로우

다양한 차트 타입을 테스트:
- Line Chart: 주가 추이
- Candlestick: OHLC 캔들
- Bar Chart: 거래량
- Table: 종목 현재가

인라인 시각화 테스트용 워크플로우입니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parents[5]
load_dotenv(project_root / ".env")


def get_workflow():
    """Build display test workflow with various chart types."""
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        raise ValueError("APPKEY and APPSECRET must be set in .env file")
    
    return {
        "id": "display-node-test",
        "version": "1.0.0",
        "name": "DisplayNode 테스트",
        "description": "다양한 차트 타입의 인라인 시각화 테스트",
        "tags": ["display", "visualization", "test"],
        
        "nodes": [
            # =====================================================================
            # INFRA Layer
            # =====================================================================
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 50, "y": 300},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "appkey": appkey,
                "appsecret": appsecret,
                "paper_trading": True,
                "position": {"x": 200, "y": 300},
            },
            
            # =====================================================================
            # SYMBOL Layer
            # =====================================================================
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}, {"exchange": "NASDAQ", "symbol": "MSFT"}, {"exchange": "NASDAQ", "symbol": "GOOGL"}],
                "position": {"x": 400, "y": 300},
            },
            
            # =====================================================================
            # DATA Layer
            # =====================================================================
            {
                "id": "historicalData",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "interval": "1d",
                "position": {"x": 600, "y": 300},
            },
            
            # =====================================================================
            # DISPLAY Layer - Various Chart Types
            # =====================================================================
            
            # Line Chart - 종가 추이
            {
                "id": "display_line",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "line",
                "title": "종가 추이 (Line)",
                "x_label": "Date",
                "y_label": "Price ($)",
                "width": 400,
                "height": 250,
                "position": {"x": 900, "y": 50},
            },
            
            # Candlestick Chart - OHLC
            {
                "id": "display_candle",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "candlestick",
                "title": "OHLC 캔들스틱",
                "x_label": "Date",
                "y_label": "Price ($)",
                "width": 400,
                "height": 300,
                "position": {"x": 900, "y": 320},
            },
            
            # Bar Chart - 거래량
            {
                "id": "display_volume",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "bar",
                "title": "거래량 (Volume)",
                "x_label": "Date",
                "y_label": "Volume",
                "width": 400,
                "height": 200,
                "position": {"x": 900, "y": 640},
            },
            
            # Table - 현재가 요약
            {
                "id": "display_table",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "table",
                "title": "종목 현재가 요약",
                "width": 350,
                "height": 200,
                "position": {"x": 1350, "y": 200},
            },
        ],
        
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "historicalData"},
            {"from": "historicalData", "to": "display_line"},
            {"from": "historicalData", "to": "display_candle"},
            {"from": "historicalData", "to": "display_volume"},
            {"from": "watchlist", "to": "display_table"},
        ],
    }
