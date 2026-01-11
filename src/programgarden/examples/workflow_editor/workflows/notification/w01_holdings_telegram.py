"""
notification/w01_holdings_telegram - 보유잔고 텔레그램 전송

해외주식 보유잔고를 조회하여 텔레그램으로 전송하는 워크플로우.

필요 Credential:
1. broker-credential: LS증권 appkey/appsecret
2. telegram-bot: Telegram bot_token, chat_id
"""


def get_workflow():
    """해외주식 보유잔고 텔레그램 전송 워크플로우"""
    
    return {
        "id": "holdings-telegram-notify",
        "version": "1.0.0",
        "name": "📱 해외주식 보유잔고 텔레그램 전송",
        "description": "LS증권 해외주식 보유잔고를 조회하여 텔레그램으로 알림",
        "tags": ["notification", "telegram", "holdings", "overseas_stock"],
        
        "nodes": [
            # =====================================================================
            # INFRA Layer - 시작 및 브로커 연결
            # =====================================================================
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "description": "워크플로우 시작점",
                "position": {"x": 100, "y": 200},
            },
            {
                "id": "broker",
                "type": "BrokerNode",
                "category": "infra",
                "provider": "ls-sec.co.kr",
                "product": "overseas_stock",
                "credential_id": "broker-credential",  # Credential로 연결
                "paper_trading": False,
                "description": "LS증권 해외주식 연결",
                "position": {"x": 300, "y": 200},
            },
            
            # =====================================================================
            # ACCOUNT Layer - 계좌 잔고 조회
            # =====================================================================
            {
                "id": "account",
                "type": "AccountNode",
                "category": "account",
                "description": "해외주식 보유잔고 조회",
                "position": {"x": 500, "y": 200},
            },
            
            # =====================================================================
            # EVENT Layer - 텔레그램 알림 (커뮤니티 노드)
            # =====================================================================
            {
                "id": "telegram",
                "type": "TelegramNode",
                "category": "event",
                "credential_id": "telegram-bot",  # bot_token, chat_id 모두 credential에서 가져옴
                "template": """📊 <b>해외주식 보유잔고</b>

{% for position in positions %}
• <b>{{ position.symbol }}</b>
  수량: {{ position.quantity }}주
  매수가: ${{ position.buy_price }}
  현재가: ${{ position.current_price }}
  수익률: {{ position.pnl_rate }}%
  손익: ${{ position.pnl_amount }}
{% endfor %}

💰 총 평가금액: ${{ total_value }}
📈 총 손익: ${{ total_pnl }} ({{ total_pnl_rate }}%)

⏰ {{ timestamp }}""",
                "parse_mode": "HTML",
                "on": ["account_updated"],
                "description": "텔레그램으로 보유잔고 전송",
                "position": {"x": 700, "y": 200},
            },
        ],
        
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "telegram"},
        ],
    }
