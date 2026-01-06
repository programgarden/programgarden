"""
예제 31: JSON 워크플로우 테스트 (JSON Workflow Test)

클라이언트가 전송하는 JSON 워크플로우 형태로 테스트:
- RSI 과매도 매수 전략
- MACD 골든크로스 전략
- 볼린저밴드 하단 돌파 전략
"""

import asyncio
import json

# ============================================================
# 워크플로우 1: RSI 과매도 매수 전략
# ============================================================
RSI_OVERSOLD_WORKFLOW = {
    "id": "rsi-oversold-buy",
    "name": "RSI 과매도 매수 전략",
    "description": "RSI가 30 이하로 떨어진 종목을 매수",
    "nodes": [
        {
            "id": "trigger-1",
            "type": "schedule",
            "fields": {
                "cron": "0 */15 9-16 * * mon-fri",
                "timezone": "America/New_York"
            }
        },
        {
            "id": "broker-1",
            "type": "broker",
            "fields": {
                "broker": "ls-sec",
                "market": "overseas-stock",
                "mode": "paper"
            }
        },
        {
            "id": "watchlist-1",
            "type": "watchlist",
            "fields": {
                "symbols": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL"]
            }
        },
        {
            "id": "condition-1",
            "type": "plugin",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 30,
                "direction": "below"
            }
        },
        {
            "id": "order-1",
            "type": "plugin",
            "plugin": "MarketOrder",
            "fields": {
                "side": "buy",
                "quantity": 10,
                "amount_type": "fixed"
            }
        }
    ],
    "edges": [
        {"from": "trigger-1", "to": "broker-1"},
        {"from": "broker-1", "to": "watchlist-1"},
        {"from": "watchlist-1", "to": "condition-1"},
        {"from": "condition-1", "to": "order-1"}
    ]
}

# ============================================================
# 워크플로우 2: MACD 골든크로스 매수 전략
# ============================================================
MACD_GOLDEN_CROSS_WORKFLOW = {
    "id": "macd-golden-cross",
    "name": "MACD 골든크로스 매수",
    "description": "MACD가 시그널선을 상향 돌파할 때 매수",
    "nodes": [
        {
            "id": "trigger-1",
            "type": "schedule",
            "fields": {
                "cron": "0 30 9 * * mon-fri",
                "timezone": "America/New_York"
            }
        },
        {
            "id": "broker-1",
            "type": "broker",
            "fields": {
                "broker": "ls-sec",
                "market": "overseas-stock",
                "mode": "live"
            }
        },
        {
            "id": "watchlist-1",
            "type": "watchlist",
            "fields": {
                "symbols": ["SPY", "QQQ", "IWM"]
            }
        },
        {
            "id": "condition-1",
            "type": "plugin",
            "plugin": "MACD",
            "fields": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "signal": "bullish_cross"
            }
        },
        {
            "id": "order-1",
            "type": "plugin",
            "plugin": "LimitOrder",
            "fields": {
                "side": "buy",
                "quantity": 5,
                "price": "{{ marketData.price * 0.995 }}",
                "price_type": "expression"
            }
        }
    ],
    "edges": [
        {"from": "trigger-1", "to": "broker-1"},
        {"from": "broker-1", "to": "watchlist-1"},
        {"from": "watchlist-1", "to": "condition-1"},
        {"from": "condition-1", "to": "order-1"}
    ]
}

# ============================================================
# 워크플로우 3: 볼린저밴드 하단 터치 매수
# ============================================================
BOLLINGER_LOWER_WORKFLOW = {
    "id": "bollinger-lower-touch",
    "name": "볼린저밴드 하단 터치 매수",
    "description": "가격이 볼린저밴드 하단을 터치하면 반등 기대 매수",
    "nodes": [
        {
            "id": "trigger-1",
            "type": "schedule",
            "fields": {
                "cron": "0 0 * * * *",
                "timezone": "America/New_York"
            }
        },
        {
            "id": "broker-1",
            "type": "broker",
            "fields": {
                "broker": "ls-sec",
                "market": "overseas-stock",
                "mode": "paper"
            }
        },
        {
            "id": "watchlist-1",
            "type": "watchlist",
            "fields": {
                "symbols": ["AAPL", "MSFT"]
            }
        },
        {
            "id": "condition-1",
            "type": "plugin",
            "plugin": "BollingerBands",
            "fields": {
                "period": 20,
                "std": 2.0,
                "position": "below_lower"
            }
        },
        {
            "id": "order-1",
            "type": "plugin",
            "plugin": "MarketOrder",
            "fields": {
                "side": "buy",
                "quantity": "{{ position.max_size - position.current_size }}",
                "amount_type": "expression"
            }
        }
    ],
    "edges": [
        {"from": "trigger-1", "to": "broker-1"},
        {"from": "broker-1", "to": "watchlist-1"},
        {"from": "watchlist-1", "to": "condition-1"},
        {"from": "condition-1", "to": "order-1"}
    ]
}

# ============================================================
# 워크플로우 4: 복합 조건 - RSI + MACD 동시 충족
# ============================================================
RSI_MACD_COMBINED_WORKFLOW = {
    "id": "rsi-macd-combined",
    "name": "RSI + MACD 복합 조건 매수",
    "description": "RSI 과매도 + MACD 골든크로스 동시 충족 시 매수",
    "nodes": [
        {
            "id": "trigger-1",
            "type": "schedule",
            "fields": {
                "cron": "0 0 10 * * mon-fri",
                "timezone": "America/New_York"
            }
        },
        {
            "id": "broker-1",
            "type": "broker",
            "fields": {
                "broker": "ls-sec",
                "market": "overseas-stock",
                "mode": "paper"
            }
        },
        {
            "id": "watchlist-1",
            "type": "watchlist",
            "fields": {
                "symbols": ["AAPL", "NVDA", "TSLA"]
            }
        },
        {
            "id": "condition-rsi",
            "type": "plugin",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 35,
                "direction": "below"
            }
        },
        {
            "id": "condition-macd",
            "type": "plugin",
            "plugin": "MACD",
            "fields": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "signal": "bullish_cross"
            }
        },
        {
            "id": "logic-and",
            "type": "all_of",
            "fields": {
                "description": "RSI와 MACD 모두 충족"
            }
        },
        {
            "id": "order-1",
            "type": "plugin",
            "plugin": "MarketOrder",
            "fields": {
                "side": "buy",
                "quantity": 15,
                "amount_type": "fixed"
            }
        }
    ],
    "edges": [
        {"from": "trigger-1", "to": "broker-1"},
        {"from": "broker-1", "to": "watchlist-1"},
        {"from": "watchlist-1", "to": "condition-rsi"},
        {"from": "watchlist-1", "to": "condition-macd"},
        {"from": "condition-rsi", "to": "logic-and"},
        {"from": "condition-macd", "to": "logic-and"},
        {"from": "logic-and", "to": "order-1"}
    ]
}

# ============================================================
# 워크플로우 5: 손절/익절 전략
# ============================================================
STOP_LOSS_TAKE_PROFIT_WORKFLOW = {
    "id": "stop-loss-take-profit",
    "name": "손절/익절 자동화",
    "description": "보유 포지션에 대해 -5% 손절, +10% 익절",
    "nodes": [
        {
            "id": "trigger-1",
            "type": "schedule",
            "fields": {
                "cron": "0 */5 9-16 * * mon-fri",
                "timezone": "America/New_York"
            }
        },
        {
            "id": "broker-1",
            "type": "broker",
            "fields": {
                "broker": "ls-sec",
                "market": "overseas-stock",
                "mode": "live"
            }
        },
        {
            "id": "portfolio-1",
            "type": "portfolio",
            "fields": {
                "filter": "all"
            }
        },
        {
            "id": "condition-stoploss",
            "type": "plugin",
            "plugin": "StopLoss",
            "fields": {
                "loss_percent": 5.0,
                "trailing": False
            }
        },
        {
            "id": "condition-takeprofit",
            "type": "plugin",
            "plugin": "ProfitTarget",
            "fields": {
                "profit_percent": 10.0
            }
        },
        {
            "id": "logic-or",
            "type": "any_of",
            "fields": {
                "description": "손절 또는 익절 조건"
            }
        },
        {
            "id": "order-1",
            "type": "plugin",
            "plugin": "MarketOrder",
            "fields": {
                "side": "sell",
                "quantity": "{{ position.quantity }}",
                "amount_type": "expression"
            }
        }
    ],
    "edges": [
        {"from": "trigger-1", "to": "broker-1"},
        {"from": "broker-1", "to": "portfolio-1"},
        {"from": "portfolio-1", "to": "condition-stoploss"},
        {"from": "portfolio-1", "to": "condition-takeprofit"},
        {"from": "condition-stoploss", "to": "logic-or"},
        {"from": "condition-takeprofit", "to": "logic-or"},
        {"from": "logic-or", "to": "order-1"}
    ]
}


def print_workflow(workflow: dict):
    """워크플로우를 보기 좋게 출력"""
    print(f"\n{'='*60}")
    print(f"워크플로우: {workflow['name']}")
    print(f"ID: {workflow['id']}")
    print(f"설명: {workflow['description']}")
    print(f"{'='*60}")
    
    print("\n[노드 목록]")
    for node in workflow['nodes']:
        node_type = node.get('plugin', node['type'])
        fields_str = json.dumps(node.get('fields', {}), ensure_ascii=False, indent=2)
        print(f"  • {node['id']} ({node_type})")
        for line in fields_str.split('\n'):
            print(f"      {line}")
    
    print("\n[실행 흐름]")
    for edge in workflow['edges']:
        print(f"  {edge['from']} → {edge['to']}")
    
    print()


def validate_workflow(workflow: dict) -> list[str]:
    """워크플로우 유효성 검사"""
    errors = []
    
    # 필수 필드 검사
    if 'id' not in workflow:
        errors.append("워크플로우 ID가 없습니다")
    if 'nodes' not in workflow:
        errors.append("노드 목록이 없습니다")
    if 'edges' not in workflow:
        errors.append("엣지 목록이 없습니다")
    
    # 노드 ID 중복 검사
    node_ids = [n['id'] for n in workflow.get('nodes', [])]
    if len(node_ids) != len(set(node_ids)):
        errors.append("중복된 노드 ID가 있습니다")
    
    # 엣지 참조 검사
    for edge in workflow.get('edges', []):
        if edge['from'] not in node_ids:
            errors.append(f"존재하지 않는 노드 참조: {edge['from']}")
        if edge['to'] not in node_ids:
            errors.append(f"존재하지 않는 노드 참조: {edge['to']}")
    
    # 트리거 노드 존재 검사
    trigger_types = ['schedule', 'webhook', 'manual']
    has_trigger = any(
        n.get('type') in trigger_types 
        for n in workflow.get('nodes', [])
    )
    if not has_trigger:
        errors.append("트리거 노드가 없습니다")
    
    return errors


def main():
    """모든 워크플로우 출력 및 검증"""
    workflows = [
        RSI_OVERSOLD_WORKFLOW,
        MACD_GOLDEN_CROSS_WORKFLOW,
        BOLLINGER_LOWER_WORKFLOW,
        RSI_MACD_COMBINED_WORKFLOW,
        STOP_LOSS_TAKE_PROFIT_WORKFLOW,
    ]
    
    print("\n" + "="*60)
    print("  ProgramGarden JSON 워크플로우 테스트")
    print("="*60)
    
    all_valid = True
    
    for workflow in workflows:
        print_workflow(workflow)
        
        # 유효성 검사
        errors = validate_workflow(workflow)
        if errors:
            print("❌ 검증 실패:")
            for err in errors:
                print(f"   - {err}")
            all_valid = False
        else:
            print("✅ 검증 통과")
        
        # JSON 출력 (디버그용)
        print("\n[JSON 출력]")
        print(json.dumps(workflow, ensure_ascii=False, indent=2)[:500] + "...")
    
    print("\n" + "="*60)
    if all_valid:
        print("✅ 모든 워크플로우 검증 완료!")
    else:
        print("❌ 일부 워크플로우에 오류가 있습니다")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
