"""
Demo workflow for Flow Visualizer (BACKUP - Original Version).

Real holdings portfolio tracker with backtest:
1. Start → Broker → Account (1회 실행)
2. Account.symbols → HistoricalData → ConditionNode(RSI) → BacktestEngine → Display (백테스트)
3. Schedule → RealMarket → DisplayPnL (반복)

Uses real LS Securities overseas stock API with credentials from .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parents[5]
load_dotenv(project_root / ".env")


def get_demo_workflow():
    """Build demo workflow with credentials from environment."""
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        raise ValueError("APPKEY and APPSECRET must be set in .env file")
    
    return {
        "id": "holdings-backtest-tracker",
        "version": "1.0.0",
        "name": "Holdings Portfolio Tracker with Backtest",
        "description": "Real holdings PnL tracking + RSI backtest",
        "nodes": [
            # ============================================
            # Layer 1: Infra (1회 실행)
            # ============================================
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 50, "y": 150},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "company": "ls",
                "product": "overseas_stock",
                "appkey": appkey,
                "appsecret": appsecret,
                "paper_trading": False,
                "position": {"x": 200, "y": 150},
            },
            # ============================================
            # Layer 2: Account - 보유종목 실시간 조회
            # ============================================
            {
                "id": "account",
                "type": "RealAccountNode",
                "category": "realtime",
                "stay_connected": True,
                "position": {"x": 350, "y": 150},
            },
            # ============================================
            # Layer 3-A: Backtest 브랜치 (1회 실행)
            # HistoricalData → BacktestEngine → Display
            # ============================================
            {
                "id": "historicalData",
                "type": "HistoricalDataNode",
                "category": "data",
                "start_date": "dynamic:months_ago(3)",
                "end_date": "dynamic:today()",
                "interval": "1d",
                "position": {"x": 500, "y": 50},
            },
            {
                "id": "backtestEngine",
                "type": "BacktestEngineNode",
                "category": "backtest",
                "initial_capital": 10000,
                "commission_rate": 0.001,
                "slippage": 0.0005,
                "position": {"x": 700, "y": 50},
            },
            {
                "id": "displayBacktest",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "line",
                "title": "📈 Backtest Result (Buy & Hold 3M)",
                "options": {
                    "x_axis": "date",
                    "y_axis": "value",
                },
                "position": {"x": 900, "y": 50},
            },
            # ============================================
            # Layer 3-B: Realtime PnL 브랜치 (반복)
            # ============================================
            {
                "id": "schedule",
                "type": "ScheduleNode",
                "category": "trigger",
                "cron": "*/10 * * * * *",
                "count": 5,
                "position": {"x": 500, "y": 250},
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "category": "realtime",
                "fields": ["price", "change", "change_rate"],
                "position": {"x": 650, "y": 250},
            },
            {
                "id": "displayPnL",
                "type": "DisplayNode",
                "category": "display",
                "chart_type": "table",
                "title": "💰 Real-time Holdings PnL",
                "options": {
                    "columns": ["symbol", "qty", "avg_price", "current_price", "pnl_rate", "pnl_amount"],
                    "highlight": {"positive": "green", "negative": "red"},
                },
                "position": {"x": 800, "y": 250},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "historicalData"},
            {"from": "historicalData", "to": "backtestEngine"},
            {"from": "backtestEngine", "to": "displayBacktest"},
            {"from": "broker", "to": "schedule"},
            {"from": "schedule", "to": "realMarket"},
            {"from": "account", "to": "realMarket"},
            {"from": "realMarket", "to": "displayPnL"},
            {"from": "account", "to": "displayPnL"},
        ],
    }


# Export workflow (lazy loaded)
DEMO_WORKFLOW = get_demo_workflow()
