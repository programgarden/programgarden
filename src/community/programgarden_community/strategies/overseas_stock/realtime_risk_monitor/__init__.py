"""
실시간 위험 관리 전략
====================

전략 ID: realtime_risk_monitor
버전: 1.0.0

설명
----
WebSocket을 통해 실시간 틱 데이터를 수신하며
수익률을 계산하고 위험 한도 초과 시 자동으로 청산합니다.

위험 관리 규칙
--------------
- 일일 손실 한도: -5%
- 단일 포지션 손실 한도: -3%
- 일일 거래 횟수 제한: 20회
- 연속 손실 제한: 3회 (3연패 시 거래 중단)

사용법
------
    from programgarden_community.strategies import get_strategy
    strategy = get_strategy("overseas_stock", "realtime_risk_monitor")
"""

REALTIME_RISK_MONITOR = {
    "id": "realtime-risk-monitor-strategy",
    "version": "1.0.0",
    "name": "실시간 위험 관리",
    "description": "실시간 틱 데이터 수신 → 수익률 계산 → 위험 한도 관리 → 자동 청산",
    "tags": ["risk-management", "realtime", "websocket", "P&L"],
    "author": "ProgramGarden Team",
    "inputs": {
        "symbols": {
            "type": "symbol_list",
            "default": ["SOXS"],
            "description": "모니터링 대상 종목",
        },
        "daily_loss_limit": {
            "type": "float",
            "default": -5,
            "description": "일일 손실 한도 (%)",
        },
        "position_loss_limit": {
            "type": "float",
            "default": -3,
            "description": "단일 포지션 손실 한도 (%)",
        },
        "max_daily_trades": {
            "type": "int",
            "default": 20,
            "description": "일일 최대 거래 횟수",
        },
        "max_consecutive_losses": {
            "type": "int",
            "default": 3,
            "description": "연속 손실 제한 (N연패 시 중단)",
        },
        "risk_check_interval": {
            "type": "int",
            "default": 1,
            "description": "위험 체크 간격 (초)",
        },
    },
    "nodes": [
        # === 인프라 설정 ===
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 300},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "broker": "ls_securities",
            "connection_mode": "websocket",  # 실시간 연결
            "position": {"x": 150, "y": 300},
        },
        {
            "id": "schedule",
            "type": "ScheduleNode",
            "category": "infra",
            "trigger": "realtime",  # 실시간 모드
            "reconnect_on_disconnect": True,
            "position": {"x": 300, "y": 300},
        },
        {
            "id": "tradingHours",
            "type": "TradingHoursFilterNode",
            "category": "infra",
            "exchange": "NASDAQ",
            "include_premarket": True,
            "include_afterhours": True,
            "position": {"x": 450, "y": 300},
        },
        
        # === 계좌 및 종목 설정 ===
        {
            "id": "realAccount",
            "type": "RealAccountNode",
            "category": "account",
            "currency": "USD",
            "position": {"x": 600, "y": 200},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": "{{ input.symbols }}",
            "position": {"x": 600, "y": 400},
        },
        
        # === 실시간 데이터 수신 ===
        {
            "id": "tickStream",
            "type": "RealMarketDataNode",
            "category": "data",
            "data_types": ["tick", "quote", "trade"],
            "position": {"x": 750, "y": 300},
        },
        
        # === 실시간 P&L 계산 ===
        {
            "id": "pnlCalculator",
            "type": "PnLCalculatorNode",
            "category": "calculation",
            "mode": "realtime",
            "include_unrealized": True,
            "position": {"x": 900, "y": 300},
        },
        
        # === 위험 관리 규칙 ===
        {
            "id": "dailyLossCheck",
            "type": "RiskConditionNode",
            "category": "risk",
            "rule": "daily_pnl",
            "threshold": "{{ input.daily_loss_limit }}",
            "operator": "<=",
            "description": "일일 손실이 한도를 초과하면 true",
            "position": {"x": 1050, "y": 150},
        },
        {
            "id": "positionLossCheck",
            "type": "RiskConditionNode",
            "category": "risk",
            "rule": "position_pnl",
            "threshold": "{{ input.position_loss_limit }}",
            "operator": "<=",
            "description": "포지션 손실이 한도를 초과하면 true",
            "position": {"x": 1050, "y": 300},
        },
        {
            "id": "dailyTradeCheck",
            "type": "RiskConditionNode",
            "category": "risk",
            "rule": "daily_trade_count",
            "threshold": "{{ input.max_daily_trades }}",
            "operator": ">=",
            "description": "일일 거래 횟수가 한도에 도달하면 true",
            "position": {"x": 1050, "y": 450},
        },
        {
            "id": "consecutiveLossCheck",
            "type": "RiskConditionNode",
            "category": "risk",
            "rule": "consecutive_losses",
            "threshold": "{{ input.max_consecutive_losses }}",
            "operator": ">=",
            "description": "연속 손실이 한도에 도달하면 true",
            "position": {"x": 1050, "y": 600},
        },
        
        # === 위험 로직 통합 ===
        {
            "id": "criticalRiskLogic",
            "type": "LogicNode",
            "category": "condition",
            "operator": "or",
            "description": "하나라도 위험 조건이 충족되면 청산",
            "position": {"x": 1200, "y": 300},
        },
        
        # === 청산 및 액션 ===
        {
            "id": "emergencyLiquidate",
            "type": "LiquidateNode",
            "category": "order",
            "mode": "all",  # 모든 포지션 청산
            "order_type": "market",
            "position": {"x": 1350, "y": 200},
        },
        {
            "id": "tradingHalt",
            "type": "TradingHaltNode",
            "category": "job",
            "duration_hours": 24,
            "description": "24시간 거래 중단",
            "position": {"x": 1350, "y": 400},
        },
        
        # === 알림 ===
        {
            "id": "riskAlert",
            "type": "AlertNode",
            "category": "event",
            "channels": ["slack", "push"],
            "priority": "critical",
            "template": "🚨 위험 한도 초과!\n{{triggered_rule}}\n현재 일일 P&L: {{daily_pnl}}%\n모든 포지션 청산됨",
            "position": {"x": 1500, "y": 200},
        },
        {
            "id": "statusAlert",
            "type": "AlertNode",
            "category": "event",
            "channels": ["slack"],
            "priority": "info",
            "interval_minutes": 30,
            "template": "📊 상태 보고\n일일 P&L: {{daily_pnl}}%\n포지션 P&L: {{position_pnl}}%\n거래 횟수: {{trade_count}}/{{max_trades}}",
            "position": {"x": 1500, "y": 400},
        },
        
        # === 대시보드 ===
        {
            "id": "riskDashboard",
            "type": "DisplayNode",
            "category": "display",
            "format": "dashboard",
            "refresh_rate_ms": "{{ input.risk_check_interval * 1000 }}",
            "widgets": [
                {
                    "type": "gauge",
                    "metric": "daily_pnl",
                    "thresholds": {"danger": -5, "warning": -3, "ok": 0},
                },
                {
                    "type": "counter",
                    "metric": "trade_count",
                    "max": "{{ input.max_daily_trades }}",
                },
                {
                    "type": "table",
                    "fields": ["symbol", "position", "avg_cost", "current_price", "pnl_percent"],
                },
            ],
            "position": {"x": 1500, "y": 600},
        },
    ],
    "edges": [
        # 인프라 연결
        {"from": "start.trigger", "to": "broker"},
        {"from": "broker.connection", "to": "schedule"},
        {"from": "schedule.tick", "to": "tradingHours"},
        
        # 계좌 및 종목
        {"from": "tradingHours.passed", "to": "realAccount"},
        {"from": "tradingHours.passed", "to": "watchlist"},
        {"from": "realAccount.account_info", "to": "tickStream.account"},
        {"from": "watchlist.symbols", "to": "tickStream.symbols"},
        
        # P&L 계산
        {"from": "tickStream.tick_data", "to": "pnlCalculator.tick_data"},
        {"from": "realAccount.positions", "to": "pnlCalculator.positions"},
        
        # 위험 체크
        {"from": "pnlCalculator.daily_pnl", "to": "dailyLossCheck.value"},
        {"from": "pnlCalculator.position_pnl", "to": "positionLossCheck.value"},
        {"from": "pnlCalculator.trade_count", "to": "dailyTradeCheck.value"},
        {"from": "pnlCalculator.consecutive_losses", "to": "consecutiveLossCheck.value"},
        
        # 위험 로직
        {"from": "dailyLossCheck.result", "to": "criticalRiskLogic.input"},
        {"from": "positionLossCheck.result", "to": "criticalRiskLogic.input"},
        {"from": "dailyTradeCheck.result", "to": "criticalRiskLogic.input"},
        {"from": "consecutiveLossCheck.result", "to": "criticalRiskLogic.input"},
        
        # 청산 및 중단
        {"from": "criticalRiskLogic.result", "to": "emergencyLiquidate.trigger"},
        {"from": "emergencyLiquidate.result", "to": "tradingHalt.trigger"},
        
        # 알림
        {"from": "emergencyLiquidate.result", "to": "riskAlert.data"},
        {"from": "pnlCalculator.summary", "to": "statusAlert.data"},
        
        # 대시보드
        {"from": "pnlCalculator.summary", "to": "riskDashboard.data"},
    ],
}


__all__ = ["REALTIME_RISK_MONITOR"]
