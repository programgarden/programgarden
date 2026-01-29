"""
ProgramGarden Core - Credential 모델

인증 정보 (Credential Layer)
자동 반복 credential 관리 시스템
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


# ============================================================
# Credential Type Schema (자동 반복)
# ============================================================

class CredentialTypeSchema(BaseModel):
    """
    Schema definition for a credential type.
    Defines what fields are needed for a specific service.
    """
    type_id: str = Field(..., description="Unique identifier (e.g., 'broker_ls_stock')")
    name: str = Field(..., description="Display name (e.g., 'LS Securities')")
    description: Optional[str] = Field(default=None)
    
    # json_dynamic_widget 형식의 폼 스키마 (필수)
    widget_schema: Dict[str, Any] = Field(
        ...,
        description="json_dynamic_widget 형식의 폼 스키마"
    )
    
    # For plugin-defined credentials
    plugin_id: Optional[str] = Field(default=None, description="Plugin that defines this type")


class Credential(BaseModel):
    """
    Stored credential instance (자동 반복).
    Contains encrypted credential data.
    """
    id: str = Field(..., description="Unique credential ID")
    user_id: str = Field(default="default", description="Owner user ID")
    name: str = Field(..., description="User-friendly name (e.g., '내 LS증권 계정')")
    credential_type: str = Field(..., description="Type ID (e.g., 'broker_ls')")
    
    # Encrypted data - in production, this would be encrypted with KMS
    # For testing, we store as plain dict (or base64 encoded)
    # For http_custom type, this can be a list of {type, key, value, label}
    data: Any = Field(default_factory=dict, description="Credential data")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )


# Built-in credential type schemas
# 디자인(레이아웃, 간격, 스타일) 요소는 포함하지 않음 - 클라이언트 개발자가 직접 구현
BUILTIN_CREDENTIAL_SCHEMAS: Dict[str, CredentialTypeSchema] = {
    # ============================================================
    # LS증권 해외주식 (overseas_stock) - 모의투자 미지원
    # ============================================================
    "broker_ls_stock": CredentialTypeSchema(
        type_id="broker_ls_stock",
        name="LS증권 해외주식",
        description="해외주식 OpenAPI 인증 정보",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-ls-stock-cred",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "appkey",
                    "type": "password",
                    "label": "App Key",
                    "description": "LS증권에서 발급받은 App Key",
                    "required": True
                },
                {
                    "key": "appsecret",
                    "type": "password",
                    "label": "App Secret",
                    "description": "LS증권에서 발급받은 App Secret",
                    "required": True
                }
            ]
        }
    ),
    # ============================================================
    # LS증권 해외선물 (overseas_futures) - 모의투자 지원
    # ============================================================
    "broker_ls_futures": CredentialTypeSchema(
        type_id="broker_ls_futures",
        name="LS증권 해외선물",
        description="해외선물 OpenAPI 인증 정보",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-ls-futures-cred",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "appkey",
                    "type": "password",
                    "label": "App Key",
                    "description": "LS증권에서 발급받은 App Key",
                    "required": True
                },
                {
                    "key": "appsecret",
                    "type": "password",
                    "label": "App Secret",
                    "description": "LS증권에서 발급받은 App Secret",
                    "required": True
                },
                {
                    "key": "paper_trading",
                    "type": "boolean",
                    "label": "모의투자",
                    "description": "실제 주문 없이 테스트 모드로 실행",
                    "default": False
                }
            ]
        }
    ),
    # ============================================================
    # Telegram Bot
    # ============================================================
    "telegram": CredentialTypeSchema(
        type_id="telegram",
        name="Telegram Bot",
        description="텔레그램 봇 알림 설정",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-telegram-bot",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "bot_token",
                    "type": "password",
                    "label": "Bot Token",
                    "description": "BotFather에서 발급받은 토큰",
                    "required": True
                },
                {
                    "key": "chat_id",
                    "type": "text",
                    "label": "Chat ID",
                    "description": "메시지를 보낼 채팅 ID",
                    "required": True
                }
            ]
        }
    ),
    # ============================================================
    # OpenAI
    # ============================================================
    "openai": CredentialTypeSchema(
        type_id="openai",
        name="OpenAI",
        description="OpenAI API 키",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-openai-key",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "api_key",
                    "type": "password",
                    "label": "API Key",
                    "description": "OpenAI API Key (sk-...)",
                    "required": True
                },
                {
                    "key": "organization",
                    "type": "text",
                    "label": "Organization ID",
                    "description": "조직 ID (선택)",
                    "required": False
                }
            ]
        }
    ),
    # ============================================================
    # Slack Webhook
    # ============================================================
    "slack": CredentialTypeSchema(
        type_id="slack",
        name="Slack Webhook",
        description="Slack Incoming Webhook",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-slack-webhook",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "webhook_url",
                    "type": "password",
                    "label": "Webhook URL",
                    "description": "Slack Incoming Webhook URL",
                    "required": True
                }
            ]
        }
    ),
    # ============================================================
    # Discord Webhook
    # ============================================================
    "discord": CredentialTypeSchema(
        type_id="discord",
        name="Discord Webhook",
        description="Discord Webhook 알림",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-discord-webhook",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "webhook_url",
                    "type": "password",
                    "label": "Webhook URL",
                    "description": "Discord Webhook URL",
                    "required": True
                }
            ]
        }
    ),
    # ============================================================
    # HTTP Authentication Types (HTTPRequestNode용)
    # ============================================================
    "http_bearer": CredentialTypeSchema(
        type_id="http_bearer",
        name="HTTP Bearer Token",
        description="Bearer Token 인증 (Authorization: Bearer <token>)",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-bearer-token",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "token",
                    "type": "password",
                    "label": "Bearer Token",
                    "description": "Bearer Token 값",
                    "required": True
                }
            ]
        }
    ),
    "http_header": CredentialTypeSchema(
        type_id="http_header",
        name="HTTP Header Auth",
        description="커스텀 헤더 인증 (X-API-Key 등)",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-api-key",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "header_name",
                    "type": "text",
                    "label": "Header Name",
                    "description": "헤더 이름 (예: X-API-Key, Authorization)",
                    "default": "X-API-Key",
                    "required": True
                },
                {
                    "key": "header_value",
                    "type": "password",
                    "label": "Header Value",
                    "description": "헤더 값 (API 키 등)",
                    "required": True
                }
            ]
        }
    ),
    "http_basic": CredentialTypeSchema(
        type_id="http_basic",
        name="HTTP Basic Auth",
        description="Basic Authentication (username:password)",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-basic-auth",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "username",
                    "type": "text",
                    "label": "Username",
                    "description": "사용자 이름",
                    "required": True
                },
                {
                    "key": "password",
                    "type": "password",
                    "label": "Password",
                    "description": "비밀번호",
                    "required": True
                }
            ]
        }
    ),
    "http_query": CredentialTypeSchema(
        type_id="http_query",
        name="HTTP Query Parameter Auth",
        description="쿼리 파라미터 인증 (?api_key=xxx)",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-query-auth",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                },
                {
                    "key": "param_name",
                    "type": "text",
                    "label": "Parameter Name",
                    "description": "쿼리 파라미터 이름",
                    "default": "api_key",
                    "required": True
                },
                {
                    "key": "param_value",
                    "type": "password",
                    "label": "Parameter Value",
                    "description": "쿼리 파라미터 값",
                    "required": True
                }
            ]
        }
    ),
    "http_custom": CredentialTypeSchema(
        type_id="http_custom",
        name="Custom HTTP Credential",
        description="커스텀 HTTP 인증 - Headers, Query Params, Body에 사용할 값들을 자유롭게 정의",
        widget_schema={
            "fields": [
                {
                    "key": "name",
                    "type": "text",
                    "label": "Credential 이름",
                    "hint": "my-custom-auth",
                    "description": "이 인증 정보를 식별할 이름",
                    "required": True
                }
            ],
            "dynamic": True,
            "dynamic_description": "커스텀 HTTP Credential은 동적으로 key-value 쌍을 정의할 수 있습니다. 서버 API를 통해 관리하세요."
        }
    ),
}


# ============================================================
# Legacy Models (기존 호환성 유지)
# ============================================================

class ProductType(str, Enum):
    """상품 유형"""

    OVERSEAS_STOCK = "overseas_stock"
    OVERSEAS_FUTURES = "overseas_futures"


class AccountInfo(BaseModel):
    """계좌 정보"""

    account_number: str = Field(..., description="계좌번호")
    product: ProductType = Field(..., description="상품 유형")
    alias: Optional[str] = Field(default=None, description="계좌 별칭")
    is_default: bool = Field(default=False, description="기본 계좌 여부")

    model_config = ConfigDict(use_enum_values=True)


class BrokerCredential(BaseModel):
    """
    증권사 인증 정보 (Credential Layer)

    OpenAPI 앱키/시크릿키, 계좌번호 등 인증 정보.
    암호화 저장되며, Definition에서 credential_id로만 참조.
    AI에게 실제 키 값은 노출되지 않음.
    """

    credential_id: str = Field(..., description="인증 정보 고유 ID")
    name: str = Field(..., description="인증 정보 이름 (예: LS증권 메인계좌)")
    provider: str = Field(
        default="ls-sec.co.kr",
        description="증권사 제공자 (현재 LS증권만 지원)",
    )

    # 인증 정보 (암호화 저장)
    auth: Dict[str, str] = Field(
        default_factory=dict,
        description="인증 정보 (app_key, app_secret - 암호화됨)",
    )

    # 연결된 계좌 목록
    accounts: List[AccountInfo] = Field(
        default_factory=list,
        description="연결된 계좌 목록",
    )

    # 메타데이터
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="생성 시간",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="수정 시간",
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="마지막 사용 시간",
    )

    # 상태
    is_valid: bool = Field(
        default=True,
        description="유효성 여부 (토큰 만료 등)",
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

    def get_default_account(self, product: ProductType = None) -> Optional[AccountInfo]:
        """기본 계좌 반환"""
        for account in self.accounts:
            if product and account.product != product:
                continue
            if account.is_default:
                return account
        # 기본 계좌 없으면 첫 번째 계좌 반환
        if product:
            matching = [a for a in self.accounts if a.product == product]
            return matching[0] if matching else None
        return self.accounts[0] if self.accounts else None

    def to_summary(self) -> Dict[str, Any]:
        """AI 에이전트용 요약 정보 (키 값 제외)"""
        return {
            "credential_id": self.credential_id,
            "name": self.name,
            "provider": self.provider,
            "accounts": [
                {
                    "account_number": f"***{acc.account_number[-4:]}",  # 마스킹
                    "product": acc.product,
                    "alias": acc.alias,
                }
                for acc in self.accounts
            ],
            "is_valid": self.is_valid,
        }


class DBType(str, Enum):
    """데이터베이스 유형"""

    POSTGRES = "postgres"
    MYSQL = "mysql"


class DBCredential(BaseModel):
    """
    데이터베이스 인증 정보 (Credential Layer)

    외부 DB 연결 정보 (PostgreSQL, MySQL 등).
    암호화 저장되며, Node에서 connection_id로 참조.
    
    사용자는 워크플로우 JSON에서 다음과 같이 참조:
    {{ secrets.mydb.host }}, {{ secrets.mydb.password }}
    """

    credential_id: str = Field(..., description="인증 정보 고유 ID")
    name: str = Field(..., description="인증 정보 이름 (예: Production DB)")
    db_type: DBType = Field(..., description="데이터베이스 유형")

    # 연결 정보 (암호화 저장)
    host: str = Field(..., description="DB 서버 호스트")
    port: int = Field(default=5432, description="DB 서버 포트")
    database: str = Field(..., description="데이터베이스 이름")
    username: str = Field(..., description="사용자명")
    password: str = Field(..., description="비밀번호 (암호화됨)")

    # SSL 설정
    ssl_enabled: bool = Field(default=False, description="SSL 사용 여부")
    ssl_verify: bool = Field(default=True, description="SSL 인증서 검증 여부")

    # 메타데이터
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="생성 시간",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="수정 시간",
    )

    # 상태
    is_valid: bool = Field(
        default=True,
        description="유효성 여부",
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
        use_enum_values=True
    )

    def to_summary(self) -> Dict[str, Any]:
        """AI 에이전트용 요약 정보 (민감정보 마스킹)"""
        return {
            "credential_id": self.credential_id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": "***",  # 마스킹
            "ssl_enabled": self.ssl_enabled,
            "is_valid": self.is_valid,
        }

    def get_connection_string(self) -> str:
        """연결 문자열 생성 (복호화된 password 필요)"""
        if self.db_type == DBType.POSTGRES:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == DBType.MYSQL:
            return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        raise ValueError(f"Unsupported db_type: {self.db_type}")
