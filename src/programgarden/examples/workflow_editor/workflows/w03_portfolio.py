"""
03. Portfolio Backtest Example

PortfolioNode를 활용한 계층적 멀티 전략 백테스트 예제.

구조:
- Master Portfolio: 전체 자본 관리, risk_parity 배분
  - Tech Portfolio (60%): 기술주 전략들
    - RSI Strategy: NVDA, AAPL
    - MA Strategy: MSFT, GOOGL  
  - Value Portfolio (40%): 가치주 전략들
    - Value Strategy: JNJ, PG
    - Momentum Strategy: AMZN
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parents[5]
load_dotenv(project_root / ".env")


def get_workflow():
    """계층적 포트폴리오 백테스트 워크플로우 생성."""
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        raise ValueError("APPKEY and APPSECRET must be set in .env file")
    
    return {
        "id": "portfolio-hierarchical-backtest",
        "version": "1.0.0",
        "name": "계층적 포트폴리오 백테스트",
        "description": "PortfolioNode를 활용한 멀티 전략 자본 배분 및 리밸런싱",
        "tags": ["portfolio", "backtest", "rebalancing", "multi-strategy"],
        
        "inputs": {
            "total_capital": {
                "type": "number",
                "default": 100000,
                "description": "총 투자 자본금 ($)",
            },
            "start_date": {
                "type": "string",
                "default": "2025-01-01",
                "description": "백테스트 시작일",
            },
            "end_date": {
                "type": "string",
                "default": "2025-12-31",
                "description": "백테스트 종료일",
            },
        },
        
        "nodes": [
            # ═══════════════════════════════════════════════════════════════
            # INFRA Layer
            # ═══════════════════════════════════════════════════════════════
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
            
            # ═══════════════════════════════════════════════════════════════
            # SYMBOL Layer - 4개 그룹
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "techGrowth",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["NVDA", "AAPL"],
                "position": {"x": 400, "y": 100},
            },
            {
                "id": "techStable",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["MSFT", "GOOGL"],
                "position": {"x": 400, "y": 300},
            },
            {
                "id": "valueStocks",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["JNJ", "PG"],
                "position": {"x": 400, "y": 500},
            },
            {
                "id": "momentumStocks",
                "type": "WatchlistNode",
                "category": "symbol",
                "symbols": ["AMZN"],
                "position": {"x": 400, "y": 700},
            },
            
            # ═══════════════════════════════════════════════════════════════
            # DATA Layer - 4개 HistoricalData
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "histTechGrowth",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "{{ input.start_date }}",
                "end_date": "{{ input.end_date }}",
                "interval": "1d",
                "position": {"x": 600, "y": 100},
            },
            {
                "id": "histTechStable",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "{{ input.start_date }}",
                "end_date": "{{ input.end_date }}",
                "interval": "1d",
                "position": {"x": 600, "y": 300},
            },
            {
                "id": "histValue",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "{{ input.start_date }}",
                "end_date": "{{ input.end_date }}",
                "interval": "1d",
                "position": {"x": 600, "y": 500},
            },
            {
                "id": "histMomentum",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "{{ input.start_date }}",
                "end_date": "{{ input.end_date }}",
                "interval": "1d",
                "position": {"x": 600, "y": 700},
            },
            
            # ═══════════════════════════════════════════════════════════════
            # CONDITION Layer - 4개 전략 조건
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "rsiCondition",
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
            {
                "id": "maCondition",
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
            {
                "id": "valueCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "RSI",
                "fields": {
                    "period": 14,
                    "threshold": 40,
                    "direction": "below",
                },
                "position": {"x": 850, "y": 500},
            },
            {
                "id": "momentumCondition",
                "type": "ConditionNode",
                "category": "condition",
                "plugin": "MACD",
                "fields": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "signal_type": "bullish_cross",
                },
                "position": {"x": 850, "y": 700},
            },
            
            # ═══════════════════════════════════════════════════════════════
            # BACKTEST Layer - 4개 전략 백테스트 (확장 옵션 사용)
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "btRSI",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 25000,  # 상위 포트폴리오에서 자동 계산됨
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "position_sizing": "kelly",
                "position_sizing_config": {
                    "kelly_fraction": 0.25,
                    "max_position_percent": 20,
                },
                "exit_rules": {
                    "stop_loss_percent": 5,
                    "take_profit_percent": 15,
                },
                "strategy_name": "RSI 역추세",
                "position": {"x": 1100, "y": 100},
            },
            {
                "id": "btMA",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 25000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "position_sizing": "equal_weight",
                "exit_rules": {
                    "stop_loss_percent": 3,
                    "trailing_stop_percent": 5,
                },
                "strategy_name": "골든크로스",
                "position": {"x": 1100, "y": 300},
            },
            {
                "id": "btValue",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 25000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "position_sizing": "fixed_percent",
                "position_sizing_config": {
                    "fixed_percent": 10,
                    "max_position_percent": 25,
                },
                "exit_rules": {
                    "stop_loss_percent": 5,
                    "take_profit_percent": 10,
                },
                "strategy_name": "가치투자",
                "position": {"x": 1100, "y": 500},
            },
            {
                "id": "btMomentum",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 25000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "position_sizing": "kelly",
                "position_sizing_config": {
                    "kelly_fraction": 0.5,
                    "max_position_percent": 30,
                },
                "exit_rules": {
                    "stop_loss_percent": 7,
                    "trailing_stop_percent": 10,
                },
                "strategy_name": "모멘텀",
                "position": {"x": 1100, "y": 700},
            },
            
            # ═══════════════════════════════════════════════════════════════
            # PORTFOLIO Layer - Level 2: 자산군별 포트폴리오
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "techPortfolio",
                "type": "PortfolioNode",
                "category": "risk",
                "total_capital": 60000,  # 마스터에서 60% 배분
                "allocation_method": "momentum",
                "rebalance_rule": "drift",
                "drift_threshold": 10.0,
                "capital_sharing": True,
                "reserve_percent": 0,
                "position": {"x": 1400, "y": 200},
            },
            {
                "id": "valuePortfolio",
                "type": "PortfolioNode",
                "category": "risk",
                "total_capital": 40000,  # 마스터에서 40% 배분
                "allocation_method": "equal",
                "rebalance_rule": "periodic",
                "rebalance_frequency": "monthly",
                "capital_sharing": False,
                "reserve_percent": 5.0,
                "position": {"x": 1400, "y": 600},
            },
            
            # ═══════════════════════════════════════════════════════════════
            # PORTFOLIO Layer - Level 3: 마스터 포트폴리오
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "masterPortfolio",
                "type": "PortfolioNode",
                "category": "risk",
                "total_capital": "{{ input.total_capital }}",
                "allocation_method": "custom",
                "custom_allocations": {
                    "techPortfolio": 0.6,
                    "valuePortfolio": 0.4,
                },
                "rebalance_rule": "drift",
                "drift_threshold": 5.0,
                "capital_sharing": True,
                "reserve_percent": 0,
                "position": {"x": 1700, "y": 400},
            },
            
            # ═══════════════════════════════════════════════════════════════
            # DISPLAY Layer - 시각화
            # ═══════════════════════════════════════════════════════════════
            {
                "id": "equityDisplay",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "line",
                "title": "📈 포트폴리오 Equity Curve 비교",
                "x_label": "날짜",
                "y_label": "포트폴리오 가치 ($)",
                "options": {
                    "multi_series": True,
                    "series_names": ["Tech", "Value", "Master"],
                    "colors": ["#3b82f6", "#22c55e", "#8b5cf6"],
                    "show_legend": True,
                },
                "position": {"x": 2000, "y": 200},
            },
            {
                "id": "allocationDisplay",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "pie",
                "title": "🥧 자본 배분 현황",
                "options": {
                    "show_percent": True,
                    "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444"],
                },
                "position": {"x": 2000, "y": 400},
            },
            {
                "id": "metricsDisplay",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "table",
                "title": "📋 성과 지표 비교",
                "options": {
                    "columns": [
                        "portfolio",
                        "total_return",
                        "max_drawdown",
                        "sharpe_ratio",
                    ],
                    "column_labels": ["포트폴리오", "수익률 (%)", "MDD (%)", "샤프"],
                },
                "position": {"x": 2000, "y": 600},
            },
        ],
        
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "techGrowth"},
            {"from": "broker", "to": "techStable"},
            {"from": "broker", "to": "valueStocks"},
            {"from": "broker", "to": "momentumStocks"},
            {"from": "techGrowth", "to": "histTechGrowth"},
            {"from": "techStable", "to": "histTechStable"},
            {"from": "valueStocks", "to": "histValue"},
            {"from": "momentumStocks", "to": "histMomentum"},
            {"from": "histTechGrowth", "to": "rsiCondition"},
            {"from": "histTechStable", "to": "maCondition"},
            {"from": "histValue", "to": "valueCondition"},
            {"from": "histMomentum", "to": "momentumCondition"},
            {"from": "histTechGrowth", "to": "btRSI"},
            {"from": "rsiCondition", "to": "btRSI"},
            {"from": "histTechStable", "to": "btMA"},
            {"from": "maCondition", "to": "btMA"},
            {"from": "histValue", "to": "btValue"},
            {"from": "valueCondition", "to": "btValue"},
            {"from": "histMomentum", "to": "btMomentum"},
            {"from": "momentumCondition", "to": "btMomentum"},
            {"from": "btRSI", "to": "techPortfolio"},
            {"from": "btMA", "to": "techPortfolio"},
            {"from": "btValue", "to": "valuePortfolio"},
            {"from": "btMomentum", "to": "valuePortfolio"},
            {"from": "techPortfolio", "to": "masterPortfolio"},
            {"from": "valuePortfolio", "to": "masterPortfolio"},
            {"from": "techPortfolio", "to": "equityDisplay"},
            {"from": "valuePortfolio", "to": "equityDisplay"},
            {"from": "masterPortfolio", "to": "equityDisplay"},
            {"from": "masterPortfolio", "to": "allocationDisplay"},
            {"from": "techPortfolio", "to": "metricsDisplay"},
            {"from": "valuePortfolio", "to": "metricsDisplay"},
            {"from": "masterPortfolio", "to": "metricsDisplay"},
        ],
    }


# Export
PORTFOLIO_WORKFLOW = None


def load_workflow():
    """워크플로우 로드 (환경변수 필요)."""
    global PORTFOLIO_WORKFLOW
    PORTFOLIO_WORKFLOW = get_portfolio_workflow()
    return PORTFOLIO_WORKFLOW


if __name__ == "__main__":
    import json
    workflow = get_portfolio_workflow()
    print(json.dumps(workflow, indent=2, ensure_ascii=False))
