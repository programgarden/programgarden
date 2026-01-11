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

from typing import Literal, List, Optional, Dict, Any, ClassVar
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNotificationNode,
    OutputPort,
)


class TelegramNode(BaseNotificationNode):
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
    
    # credential에서 자동 주입됨 (exclude=True로 UI/스키마에서 제외)
    bot_token: Optional[str] = Field(default=None, exclude=True)
    chat_id: Optional[str] = Field(default=None, exclude=True)
    
    # BaseNotificationNode의 _outputs 확장
    _outputs: List[OutputPort] = [
        OutputPort(
            name="sent",
            type="signal",
            description="Message sent confirmation",
        ),
        OutputPort(
            name="message_id",
            type="string",
            description="Telegram message ID for reference",
        ),
    ]
    
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

