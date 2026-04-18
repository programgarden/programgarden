"""
ProgramGarden Community - TelegramNode

텔레그램 봇 API를 통한 메시지 전송 노드.

사용 예시:
    {
        "id": "telegram",
        "type": "TelegramNode",
        "credential_id": "telegram-bot-001",
        "template": "🎯 체결: {{symbol}} {{quantity}}주 @ {{price}}"
    }
    
    credential "telegram-bot-001":
        {"bot_token": "123456:ABC...", "chat_id": "880982510"}
"""

from typing import Literal, List, Optional, Dict, Any, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseMessagingNode,
    OutputPort,
)


class TelegramNode(BaseMessagingNode):
    """
    텔레그램 메시지 전송 노드
    
    Telegram Bot API를 통해 메시지를 전송합니다.
    
    Credential 자동 주입:
        credential_id를 설정하면 GenericNodeExecutor가 실행 전에
        credential의 bot_token, chat_id를 _bot_token, _chat_id에 자동 주입합니다.
        
    사용법:
        {
            "type": "TelegramNode",
            "credential_id": "telegram-bot-001",  # bot_token, chat_id 자동 주입
            "template": "메시지 내용",
        }
    """
    
    type: Literal["TelegramNode"] = "TelegramNode"
    description: str = "Send messages via Telegram Bot API"
    
    # 노드 아이콘 (텔레그램 로고)
    _img_url: ClassVar[str] = "https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Send a trade signal notification to an investor after a ConditionNode fires (e.g. RSI oversold buy alert)",
            "Notify on risk events such as trailing stop trigger, daily loss limit breach, or drawdown alert",
            "Confirm order execution by forwarding fill details (symbol, quantity, price) to a Telegram chat",
            "Deliver scheduled summary reports (portfolio PnL, open positions) at the end of a trading session",
        ],
        "when_not_to_use": [
            "As the primary data source — TelegramNode only sends outbound messages, it cannot receive or read messages",
            "For high-frequency per-tick notifications — combine with ThrottleNode or IfNode to limit message volume",
            "When no Telegram bot credential is available — credential_id with bot_token and chat_id is required",
        ],
        "typical_scenarios": [
            "ConditionNode (signal=True) → TelegramNode (alert with symbol and RSI value)",
            "OverseasStockNewOrderNode → TelegramNode (order fill confirmation)",
            "PortfolioNode → TelegramNode (daily PnL summary at session end)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Sends Telegram messages via Bot API using bot_token and chat_id injected from a 'telegram_bot' credential — no secrets in workflow JSON",
        "Supports Jinja2-style template variables (e.g. {{symbol}}, {{price}}) resolved at runtime from upstream node outputs",
        "HTML parse mode enabled by default — supports <b>, <i>, and <code> formatting in messages",
        "Built-in resilience with configurable retry and fallback (skip or error) for transient network failures",
        "Returns 'sent' (bool) and 'message_id' (str) output ports for downstream confirmation checks",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting TelegramNode directly after a real-time market data node without throttling",
            "reason": "Real-time nodes fire on every tick; sending a Telegram message per tick will quickly hit Bot API rate limits (30 messages/sec global, 1 message/sec per chat).",
            "alternative": "Insert ThrottleNode or IfNode between the real-time node and TelegramNode to gate messages to meaningful events only.",
        },
        {
            "pattern": "Embedding bot_token and chat_id directly in the workflow JSON fields instead of using credential_id",
            "reason": "Hard-coded secrets in workflow JSON are visible to anyone who exports the workflow and cannot be rotated centrally.",
            "alternative": "Always use credential_id pointing to a 'telegram_bot' credential entry in the credentials section.",
        },
        {
            "pattern": "Using TelegramNode as the only error reporter without a fallback",
            "reason": "If the Telegram API is unreachable, no error notification is delivered, silencing failures completely.",
            "alternative": "Set resilience.fallback.mode='skip' and additionally log errors via TableDisplayNode or on_log listener in your execution listener.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "RSI buy signal alert",
            "description": "When RSI drops below the oversold threshold, send a Telegram message with the symbol and RSI value.",
            "workflow_snippet": {
                "id": "telegram_rsi_alert",
                "name": "Telegram RSI Alert",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}], "period": "1d", "count": 20},
                    {"id": "condition", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}", "period": 14, "oversold": 30, "overbought": 70},
                    {
                        "id": "notify",
                        "type": "TelegramNode",
                        "credential_id": "tg_cred",
                        "template": "Buy signal: {{ nodes.condition.symbol }} RSI={{ nodes.condition.rsi }}",
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "historical"},
                    {"from": "historical", "to": "condition"},
                    {"from": "condition", "to": "notify"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "tg_cred",
                        "type": "telegram_bot",
                        "data": [
                            {"key": "bot_token", "value": "", "type": "password", "label": "Bot Token"},
                            {"key": "chat_id", "value": "", "type": "string", "label": "Chat ID"},
                        ],
                    },
                ],
            },
            "expected_output": "sent=True, message_id='<telegram_msg_id>' confirming the alert was delivered.",
        },
        {
            "title": "Risk alert — trailing stop triggered",
            "description": "After a TrailingStop plugin fires, notify the investor via Telegram before cancelling open orders.",
            "workflow_snippet": {
                "id": "telegram_risk_alert",
                "name": "Telegram Risk Alert",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "risk", "type": "ConditionNode", "plugin": "TrailingStop", "data": "{{ nodes.account.positions }}", "trail_pct": 5.0},
                    {
                        "id": "alert",
                        "type": "TelegramNode",
                        "credential_id": "tg_cred",
                        "template": "Trailing stop hit: {{ nodes.risk.symbol }} drawdown={{ nodes.risk.drawdown_pct }}%",
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "risk"},
                    {"from": "risk", "to": "alert"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "tg_cred",
                        "type": "telegram_bot",
                        "data": [
                            {"key": "bot_token", "value": "", "type": "password", "label": "Bot Token"},
                            {"key": "chat_id", "value": "", "type": "string", "label": "Chat ID"},
                        ],
                    },
                ],
            },
            "expected_output": "sent=True with the formatted risk alert message confirming Telegram delivery.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "TelegramNode has no mandatory data input port. The 'template' field accepts static text or {{ expression }} variables that reference upstream node outputs (e.g. {{ nodes.condition.rsi }}). The node resolves template variables at execution time using ExecutionContext.",
        "output_consumption": "Check 'sent' (bool) to confirm delivery. Use 'message_id' if you need to reference or delete the Telegram message later. On failure, 'sent' is False and an 'error' key describes the reason — handle with resilience.fallback or a downstream IfNode.",
        "common_combinations": [
            "ConditionNode (signal) → TelegramNode (alert)",
            "OverseasStockNewOrderNode → TelegramNode (fill confirmation)",
            "PortfolioNode → TelegramNode (PnL summary)",
            "IfNode (true branch) → TelegramNode + OverseasStockNewOrderNode in parallel",
        ],
        "pitfalls": [
            "Template variables must match actual output port names of upstream nodes — a typo (e.g. {{ nodes.cond.rsi }} vs {{ nodes.condition.rsi }}) silently resolves to an empty string.",
            "chat_id must be a string even if it looks like a number — set it as a string in the credential data.",
            "Telegram Bot API rejects messages longer than 4096 characters; truncate long summaries before passing to the template.",
        ],
    }

    # credential에서 자동 주입됨 (exclude=True로 UI/스키마에서 제외)
    bot_token: Optional[str] = Field(default=None, exclude=True)
    chat_id: Optional[str] = Field(default=None, exclude=True)
    
    # BaseNotificationNode의 _outputs 확장
    _outputs: List[OutputPort] = [
        OutputPort(
            name="sent",
            type="signal",
            description="Message sent confirmation",
            example={"sent": True, "chat_id": "123456789"},
        ),
        OutputPort(
            name="message_id",
            type="string",
            description="Telegram message ID for reference",
            example="1234",
        ),
    ]
    
    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """
        TelegramNode 필드 스키마 정의
        
        expression_mode:
        - template: BOTH (고정값 또는 {{ }} 표현식 모두 사용 가능)
        - credential_id: FIXED_ONLY (고정값만 허용)
        """
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            # === PARAMETERS: 핵심 설정 ===
            "template": FieldSchema(
                name="template",
                type=FieldType.STRING,
                description="메시지 템플릿. Jinja2 스타일 변수 사용 가능 (예: {{symbol}}, {{price}})",
                default="",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="🎯 체결: {{symbol}} {{quantity}}주 @ {{price}}",
                example="📈 {{symbol}} RSI: {{rsi}} → 매수 신호!",
                expected_type="str",
            ),
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.STRING,
                description="텔레그램 봇 credential ID. credentials 섹션에 {bot_token, chat_id} 정의 필요",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="telegram-bot-001",
                example="telegram-bot-001",
                expected_type="str",
            ),
        }
    
    async def execute(self, context: Any) -> Dict[str, Any]:
        """
        텔레그램 메시지 전송
        
        Note:
            credential_id가 설정되어 있으면 GenericNodeExecutor가 실행 전에
            bot_token, chat_id를 자동 주입합니다.
        
        Returns:
            {
                "sent": True/False,
                "message_id": "12345" (성공 시),
                "error": "..." (실패 시)
            }
        """
        import aiohttp
        
        # 1. 필수 필드 검증 (credential에서 자동 주입되어 있어야 함)
        if not self.bot_token:
            return {"sent": False, "error": "bot_token is required (set credential_id)"}
        
        if not self.chat_id:
            return {"sent": False, "error": "chat_id is required (set credential_id)"}
        
        try:
            # 2. 메시지 준비 (template이 있으면 사용, 없으면 기본 메시지)
            if self.template:
                # render_template이 있으면 사용, 없으면 그냥 template 사용
                if hasattr(context, "render_template"):
                    event_data = getattr(context, "event_data", {}) or {}
                    message = context.render_template(self.template, event_data)
                else:
                    message = self.template
            else:
                message = "ProgramGarden notification"
            
            # 빈 메시지 방지
            if not message or not message.strip():
                message = "ProgramGarden notification"
            
            # 3. Telegram API 호출
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_notification": False,
                "disable_web_page_preview": True,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    
                    if result.get("ok"):
                        return {
                            "sent": True,
                            "message_id": str(result["result"]["message_id"]),
                        }
                    else:
                        return {
                            "sent": False,
                            "error": result.get("description", "Unknown Telegram API error"),
                        }
        
        except aiohttp.ClientError as e:
            return {"sent": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"sent": False, "error": f"Unexpected error: {str(e)}"}

