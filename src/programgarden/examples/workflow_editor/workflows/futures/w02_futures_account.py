"""10_futures/w02_futures_account - 해외선물 잔고 조회"""


def get_workflow():
    return {
        "id": "futures-02-account",
        "version": "1.0.0",
        "name": "해외선물 잔고 조회",
        "description": "해외선물 계좌 잔고 및 포지션 실시간 조회",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 100, "y": 150},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "paper_trading": True,
                "position": {"x": 300, "y": 150},
            },
            {
                "id": "realAccount",
                "type": "RealAccountNode",
                "category": "realtime",
                "stay_connected": True,
                "sync_interval_sec": 30,  # 30초마다 잔고 동기화
                "position": {"x": 500, "y": 150},
            },
            {
                "id": "positionDisplay",
                "type": "DisplayNode",
                "category": "display",
                "format": "table",
                "title": "포지션 현황",
                "fields": ["symbol", "is_long", "qty", "entry_price", "current_price", "pnl_amount"],
                "position": {"x": 700, "y": 100},
            },
            {
                "id": "balanceDisplay",
                "type": "DisplayNode",
                "category": "display",
                "format": "card",
                "title": "계좌 잔고",
                "fields": ["deposit", "orderable_amount", "margin", "pnl_amount"],
                "position": {"x": 700, "y": 250},
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "realAccount"},
            {"from": "realAccount", "to": "positionDisplay"},
            {"from": "realAccount", "to": "balanceDisplay"},
        ],
    }
