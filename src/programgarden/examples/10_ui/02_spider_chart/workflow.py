"""
Spider Chart Portfolio Analysis Workflow

5종목의 기술적 지표(RSI, MA괴리율, 거래량, 변동성, 모멘텀)를 
레이더(스파이더) 차트로 비교 분석하는 워크플로우

Uses real LS Securities overseas stock API with credentials from .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parents[5]
load_dotenv(project_root / ".env")


def get_spider_chart_workflow():
    """Build spider chart portfolio analysis workflow."""
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        raise ValueError("APPKEY and APPSECRET must be set in .env file")
    
    return {
        "id": "spider-chart-portfolio-analysis",
        "version": "1.0.0",
        "name": "🕸️ 스파이더 차트 포트폴리오 분석",
        "description": "5종목의 기술적 지표(RSI, MA괴리율, 거래량, 변동성, 모멘텀)를 레이더 차트로 비교",
        "tags": ["visualization", "radar", "spider", "technical-analysis"],
        
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
                "paper_trading": False,
                "position": {"x": 200, "y": 300},
            },
            
            # =====================================================================
            # SYMBOL Layer
            # =====================================================================
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
                "position": {"x": 400, "y": 300},
            },
            
            # =====================================================================
            # DATA Layer
            # =====================================================================
            {
                "id": "historicalData",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "2025-10-01",
                "end_date": "2025-12-31",
                "interval": "1d",
                "position": {"x": 600, "y": 300},
            },
            
            # =====================================================================
            # CONDITION Layer - 지표 계산 (5개)
            # =====================================================================
            {
                "id": "rsiCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {
                    "period": 14,
                    "threshold": 50,
                    "direction": "any",
                },
                "position": {"x": 850, "y": 100},
            },
            {
                "id": "maCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "MovingAverageDeviation",
                "fields": {
                    "period": 20,
                    "threshold": 0,
                },
                "position": {"x": 850, "y": 200},
            },
            {
                "id": "volumeCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "VolumeRatio",
                "fields": {
                    "period": 20,
                    "threshold": 1.0,
                },
                "position": {"x": 850, "y": 300},
            },
            {
                "id": "volatilityCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "Volatility",
                "fields": {
                    "period": 20,
                    "annualize": True,
                },
                "position": {"x": 850, "y": 400},
            },
            {
                "id": "momentumCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "Momentum",
                "fields": {
                    "period": 20,
                },
                "position": {"x": 850, "y": 500},
            },
            
            # =====================================================================
            # DISPLAY Layer - Spider Chart
            # =====================================================================
            {
                "id": "spiderChart",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "radar",
                "title": "🕸️ 종목별 기술적 지표 비교",
                "options": {
                    "labels": ["RSI (0-100)", "MA괴리율 (%)", "거래량비율", "변동성 (%)", "모멘텀 (%)"],
                    "normalize": True,
                    "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444"],
                },
                "position": {"x": 1100, "y": 250},
            },
            
            # =====================================================================
            # DISPLAY Layer - Summary Table
            # =====================================================================
            {
                "id": "summaryTable",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "table",
                "title": "📋 지표 상세 값",
                "options": {
                    "columns": ["symbol", "rsi", "ma_deviation", "volume_ratio", "volatility", "momentum"],
                },
                "position": {"x": 1100, "y": 450},
            },
        ],
        
        "edges": [
            # 기본 연결
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "watchlist"},
            {"from": "watchlist.symbols", "to": "historicalData.symbols"},
            
            # HistoricalData → Conditions
            {"from": "historicalData.ohlcv_data", "to": "rsiCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "maCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "volumeCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "volatilityCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "momentumCondition.price_data"},
            
            # Conditions → Spider Chart (aggregated)
            {"from": "rsiCondition.metrics", "to": "spiderChart.data"},
            {"from": "maCondition.metrics", "to": "spiderChart.data"},
            {"from": "volumeCondition.metrics", "to": "spiderChart.data"},
            {"from": "volatilityCondition.metrics", "to": "spiderChart.data"},
            {"from": "momentumCondition.metrics", "to": "spiderChart.data"},
            
            # Conditions → Summary Table
            {"from": "rsiCondition.metrics", "to": "summaryTable.data"},
            {"from": "maCondition.metrics", "to": "summaryTable.data"},
            {"from": "volumeCondition.metrics", "to": "summaryTable.data"},
            {"from": "volatilityCondition.metrics", "to": "summaryTable.data"},
            {"from": "momentumCondition.metrics", "to": "summaryTable.data"},
        ],
    }


# For standalone testing - generate mock data
def get_mock_spider_data():
    """Generate mock data for testing radar chart without API calls."""
    return {
        "id": "spider-chart-mock-demo",
        "version": "1.0.0",
        "name": "🕸️ 스파이더 차트 데모 (Mock Data)",
        "description": "레이더 차트 렌더링 테스트용 Mock 데이터",
        "tags": ["demo", "mock", "radar"],
        
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 50, "y": 200},
            },
            {
                "id": "mockData",
                "type": "MockDataNode",
                "category": "data",
                "mock_output": {
                    "chart_type": "radar",
                    "title": "🕸️ 종목별 기술적 지표 비교",
                    "options": {
                        "labels": ["RSI", "MA괴리율", "거래량", "변동성", "모멘텀"],
                        "normalize": True,
                    },
                    "data": [
                        {"symbol": "AAPL", "values": [65.2, 2.1, 1.15, 18.5, 5.3]},
                        {"symbol": "MSFT", "values": [58.7, -1.2, 0.92, 15.2, 3.1]},
                        {"symbol": "GOOGL", "values": [71.3, 3.5, 1.45, 21.3, 8.2]},
                        {"symbol": "NVDA", "values": [45.2, -5.3, 2.10, 35.6, -2.1]},
                        {"symbol": "TSLA", "values": [52.8, 1.8, 1.78, 42.1, 4.5]},
                    ],
                },
                "position": {"x": 250, "y": 200},
            },
            {
                "id": "spiderChart",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "radar",
                "title": "🕸️ 종목별 기술적 지표 비교",
                "options": {
                    "labels": ["RSI", "MA괴리율", "거래량", "변동성", "모멘텀"],
                    "normalize": True,
                    "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444"],
                },
                "position": {"x": 500, "y": 200},
            },
        ],
        
        "edges": [
            {"from": "start.start", "to": "mockData"},
            {"from": "mockData.output", "to": "spiderChart.data"},
        ],
    }


# Export
SPIDER_CHART_WORKFLOW = None

def get_workflow():
    """Get workflow (lazy load)."""
    global SPIDER_CHART_WORKFLOW
    if SPIDER_CHART_WORKFLOW is None:
        SPIDER_CHART_WORKFLOW = get_spider_chart_workflow()
    return SPIDER_CHART_WORKFLOW
