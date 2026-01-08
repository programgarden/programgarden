"""
Demo workflow for Flow Visualizer.

멀티 전략 백테스트 비교:
- 5가지 전략 (개별 3개 + 조합 2개)
- 5종목 (AAPL, MSFT, GOOGL, AMZN, NVDA)
- 시각화 5종 (Line, Radar, Histogram, Bar, Table)

Uses real LS Securities overseas stock API with credentials from .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parents[5]
load_dotenv(project_root / ".env")


def get_workflow():
    """Build multi-strategy backtest workflow."""
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        raise ValueError("APPKEY and APPSECRET must be set in .env file")
    
    return {
        "id": "backtest-multi-strategy-comparison",
        "version": "1.0.0",
        "name": "멀티 전략 백테스트 비교",
        "description": "5가지 전략(개별3+조합2)의 1년 백테스트 성과 비교",
        "tags": ["backtest", "multi-strategy", "comparison", "visualization"],
        
        "nodes": [
            # =====================================================================
            # INFRA Layer
            # =====================================================================
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 50, "y": 400},
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
                "position": {"x": 200, "y": 400},
            },
            
            # =====================================================================
            # SYMBOL Layer
            # =====================================================================
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
                "position": {"x": 400, "y": 400},
            },
            
            # =====================================================================
            # DATA Layer
            # =====================================================================
            {
                "id": "historicalData",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "interval": "1d",
                "position": {"x": 600, "y": 400},
            },
            
            # =====================================================================
            # CONDITION Layer - 개별 전략 (6개 노드)
            # =====================================================================
            
            # 전략 1: RSI 역추세 (매수)
            {
                "id": "rsiBuyCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {
                    "period": 14,
                    "threshold": 30,
                    "direction": "below",
                },
                "position": {"x": 850, "y": 100},
            },
            # 전략 1: RSI 역추세 (매도)
            {
                "id": "rsiSellCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {
                    "period": 14,
                    "threshold": 70,
                    "direction": "above",
                },
                "position": {"x": 850, "y": 200},
            },
            
            # 전략 2: 골든크로스 (매수)
            {
                "id": "goldenCrossCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "MovingAverageCross",
                "fields": {
                    "short_period": 5,
                    "long_period": 20,
                    "cross_type": "golden",
                },
                "position": {"x": 850, "y": 300},
            },
            # 전략 2: 데드크로스 (매도)
            {
                "id": "deadCrossCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "MovingAverageCross",
                "fields": {
                    "short_period": 5,
                    "long_period": 20,
                    "cross_type": "dead",
                },
                "position": {"x": 850, "y": 400},
            },
            
            # 전략 3: 듀얼모멘텀
            {
                "id": "dualMomentumCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "DualMomentum",
                "fields": {
                    "lookback_period": 252,
                    "absolute_threshold": 0,
                    "use_relative": True,
                    "relative_benchmark": "SHY",
                },
                "position": {"x": 850, "y": 500},
            },
            
            # 전략 5용: MACD (조합용)
            {
                "id": "macdCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "MACD",
                "fields": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "signal_type": "bullish_cross",
                },
                "position": {"x": 850, "y": 600},
            },
            
            # =====================================================================
            # CONDITION Layer - 전략 조합 (2개)
            # =====================================================================
            
            # 전략 4: RSI AND 골든크로스
            {
                "id": "rsiAndGoldenLogic",
                "type": "LogicNode",
                "category": "condition",
                "operator": "all",
                "position": {"x": 1100, "y": 200},
            },
            
            # 전략 5: RSI OR MACD
            {
                "id": "rsiOrMacdLogic",
                "type": "LogicNode",
                "category": "condition",
                "operator": "any",
                "position": {"x": 1100, "y": 550},
            },
            
            # =====================================================================
            # BACKTEST Layer - 전략별 백테스트 실행 (5개)
            # =====================================================================
            
            # 백테스트 1: RSI 역추세
            {
                "id": "rsiBacktest",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 100000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "strategy_name": "RSI 역추세",
                "position": {"x": 1350, "y": 150},
            },
            
            # 백테스트 2: 골든크로스
            {
                "id": "goldenCrossBacktest",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 100000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "strategy_name": "골든크로스",
                "position": {"x": 1350, "y": 300},
            },
            
            # 백테스트 3: 듀얼모멘텀
            {
                "id": "dualMomentumBacktest",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 100000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "strategy_name": "듀얼모멘텀",
                "position": {"x": 1350, "y": 450},
            },
            
            # 백테스트 4: RSI AND 골든크로스
            {
                "id": "combinedAndBacktest",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 100000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "strategy_name": "RSI+골든(AND)",
                "position": {"x": 1350, "y": 600},
            },
            
            # 백테스트 5: RSI OR MACD
            {
                "id": "combinedOrBacktest",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 100000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "strategy_name": "RSI|MACD(OR)",
                "position": {"x": 1350, "y": 750},
            },
            
            # =====================================================================
            # DISPLAY Layer - Level 1: 포트폴리오 레벨 (3개)
            # =====================================================================
            
            # 1️⃣ Line Chart: 5개 전략 Equity Curve 비교
            {
                "id": "equityCurveDisplay",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "line",
                "title": "📈 전략별 Equity Curve 비교",
                "x_label": "날짜",
                "y_label": "포트폴리오 가치 ($)",
                "options": {
                    "multi_series": True,
                    "series_names": [
                        "RSI 역추세",
                        "골든크로스",
                        "듀얼모멘텀",
                        "RSI+골든(AND)",
                        "RSI|MACD(OR)",
                    ],
                    "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444"],
                },
                "position": {"x": 1600, "y": 200},
            },
            
            # 2️⃣ Radar Chart: 성과 지표 비교
            {
                "id": "performanceRadar",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "radar",
                "title": "🕸️ 전략별 성과 지표 비교",
                "options": {
                    "metrics": ["total_return", "sharpe_ratio", "max_drawdown", "win_rate"],
                    "labels": ["수익률", "샤프비율", "MDD", "승률"],
                    "normalize": True,
                },
                "position": {"x": 1600, "y": 400},
            },
            
            # 3️⃣ Bar Chart: 수익률 분포 (히스토그램)
            {
                "id": "returnDistribution",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "bar",
                "title": "📊 일별 수익률 분포",
                "options": {
                    "histogram": True,
                    "bins": 30,
                },
                "position": {"x": 1600, "y": 600},
            },
            
            # =====================================================================
            # DISPLAY Layer - Level 2: 종목 기여도 (2개)
            # =====================================================================
            
            # 4️⃣ Bar Chart: 종목별 기여도
            {
                "id": "symbolContribution",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "bar",
                "title": "📊 종목별 수익 기여도",
                "options": {
                    "top_n": 10,
                    "horizontal": True,
                },
                "position": {"x": 1850, "y": 300},
            },
            
            # 5️⃣ Table: 거래 통계 요약
            {
                "id": "tradeSummary",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "table",
                "title": "📋 전략별 거래 통계",
                "options": {
                    "columns": ["strategy_name", "total_trades", "win_rate", "total_return", "sharpe_ratio"],
                    "sort_by": "total_return",
                },
                "position": {"x": 1850, "y": 500},
            },
        ],
        
        "edges": [
            # =====================================================================
            # 기본 연결: Start → Broker → Watchlist → HistoricalData
            # =====================================================================
            {"from": "start.start", "to": "broker"},
            {"from": "broker.connection", "to": "watchlist"},
            {"from": "watchlist.symbols", "to": "historicalData.symbols"},
            
            # =====================================================================
            # HistoricalData → 모든 Condition 노드
            # =====================================================================
            {"from": "historicalData.ohlcv_data", "to": "rsiBuyCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "rsiSellCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "goldenCrossCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "deadCrossCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "dualMomentumCondition.price_data"},
            {"from": "historicalData.ohlcv_data", "to": "macdCondition.price_data"},
            
            # =====================================================================
            # 전략 조합: LogicNode 입력
            # =====================================================================
            {"from": "rsiBuyCondition.result", "to": "rsiAndGoldenLogic.input"},
            {"from": "goldenCrossCondition.result", "to": "rsiAndGoldenLogic.input"},
            {"from": "rsiBuyCondition.result", "to": "rsiOrMacdLogic.input"},
            {"from": "macdCondition.result", "to": "rsiOrMacdLogic.input"},
            
            # =====================================================================
            # Condition → BacktestEngine
            # =====================================================================
            {"from": "rsiBuyCondition.signals", "to": "rsiBacktest.buy_signal"},
            {"from": "rsiSellCondition.signals", "to": "rsiBacktest.sell_signal"},
            {"from": "historicalData.ohlcv_data", "to": "rsiBacktest.ohlcv_data"},
            
            {"from": "goldenCrossCondition.signals", "to": "goldenCrossBacktest.buy_signal"},
            {"from": "deadCrossCondition.signals", "to": "goldenCrossBacktest.sell_signal"},
            {"from": "historicalData.ohlcv_data", "to": "goldenCrossBacktest.ohlcv_data"},
            
            {"from": "dualMomentumCondition.signals", "to": "dualMomentumBacktest.buy_signal"},
            {"from": "historicalData.ohlcv_data", "to": "dualMomentumBacktest.ohlcv_data"},
            
            {"from": "rsiAndGoldenLogic.result", "to": "combinedAndBacktest.buy_signal"},
            {"from": "historicalData.ohlcv_data", "to": "combinedAndBacktest.ohlcv_data"},
            
            {"from": "rsiOrMacdLogic.result", "to": "combinedOrBacktest.buy_signal"},
            {"from": "historicalData.ohlcv_data", "to": "combinedOrBacktest.ohlcv_data"},
            
            # =====================================================================
            # BacktestEngine → Display (Level 1)
            # =====================================================================
            {"from": "rsiBacktest.equity_curve", "to": "equityCurveDisplay.data"},
            {"from": "goldenCrossBacktest.equity_curve", "to": "equityCurveDisplay.data"},
            {"from": "dualMomentumBacktest.equity_curve", "to": "equityCurveDisplay.data"},
            {"from": "combinedAndBacktest.equity_curve", "to": "equityCurveDisplay.data"},
            {"from": "combinedOrBacktest.equity_curve", "to": "equityCurveDisplay.data"},
            
            {"from": "rsiBacktest.metrics", "to": "performanceRadar.data"},
            {"from": "goldenCrossBacktest.metrics", "to": "performanceRadar.data"},
            {"from": "dualMomentumBacktest.metrics", "to": "performanceRadar.data"},
            {"from": "combinedAndBacktest.metrics", "to": "performanceRadar.data"},
            {"from": "combinedOrBacktest.metrics", "to": "performanceRadar.data"},
            
            {"from": "rsiBacktest.summary", "to": "returnDistribution.data"},
            {"from": "goldenCrossBacktest.summary", "to": "returnDistribution.data"},
            {"from": "dualMomentumBacktest.summary", "to": "returnDistribution.data"},
            {"from": "combinedAndBacktest.summary", "to": "returnDistribution.data"},
            {"from": "combinedOrBacktest.summary", "to": "returnDistribution.data"},
            
            # =====================================================================
            # BacktestEngine → Display (Level 2)
            # =====================================================================
            {"from": "rsiBacktest.trades", "to": "symbolContribution.data"},
            {"from": "rsiBacktest.summary", "to": "tradeSummary.data"},
            {"from": "goldenCrossBacktest.summary", "to": "tradeSummary.data"},
            {"from": "dualMomentumBacktest.summary", "to": "tradeSummary.data"},
            {"from": "combinedAndBacktest.summary", "to": "tradeSummary.data"},
            {"from": "combinedOrBacktest.summary", "to": "tradeSummary.data"},
        ],
    }


# Export workflow
DEMO_WORKFLOW = None  # Lazy loaded

def get_workflow():
    """Get workflow (lazy load)."""
    global DEMO_WORKFLOW
    if DEMO_WORKFLOW is None:
        DEMO_WORKFLOW = get_demo_workflow()
    return DEMO_WORKFLOW
