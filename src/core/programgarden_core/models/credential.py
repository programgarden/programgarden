"""
ProgramGarden Core - Credential 모델

인증 정보 (Credential Layer)
n8n 스타일 credential 관리 시스템
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


# ============================================================
# Credential Type Schema (n8n 스타일)
# ============================================================

class CredentialFieldType(str, Enum):
    """Field input types for UI rendering"""
    STRING = "string"
    PASSWORD = "password"             # Masked input
    BOOLEAN = "boolean"
    NUMBER = "number"
    SELECT = "select"                 # Dropdown


class CredentialField(BaseModel):
    """Single field definition in a credential schema"""
    key: str = Field(..., description="Field key (e.g., 'appkey')")
    label: str = Field(..., description="Display label (e.g., 'App Key')")
    field_type: CredentialFieldType = Field(default=CredentialFieldType.STRING)
    required: bool = Field(default=True)
    default: Optional[Any] = Field(default=None)
    description: Optional[str] = Field(default=None)
    options: Optional[List[str]] = Field(default=None, description="Options for SELECT type")

    model_config = ConfigDict(use_enum_values=True)


class CredentialTypeSchema(BaseModel):
    """
    Schema definition for a credential type.
    Defines what fields are needed for a specific service.
    """
    type_id: str = Field(..., description="Unique identifier (e.g., 'broker_ls')")
    name: str = Field(..., description="Display name (e.g., 'LS Securities')")
    description: Optional[str] = Field(default=None)
    icon: Optional[str] = Field(default=None, description="Icon emoji or URL")
    fields: List[CredentialField] = Field(default_factory=list)
    
    # For plugin-defined credentials
    plugin_id: Optional[str] = Field(default=None, description="Plugin that defines this type")


class Credential(BaseModel):
    """
    Stored credential instance (n8n 스타일).
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
BUILTIN_CREDENTIAL_SCHEMAS: Dict[str, CredentialTypeSchema] = {
    "broker_ls": CredentialTypeSchema(
        type_id="broker_ls",
        name="LS Securities",
        description="LS증권 OpenAPI 인증 정보",
        icon="🏦",
        fields=[
            CredentialField(
                key="appkey",
                label="App Key",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="LS증권에서 발급받은 App Key"
            ),
            CredentialField(
                key="appsecret",
                label="App Secret",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="LS증권에서 발급받은 App Secret"
            ),
            CredentialField(
                key="paper_trading",
                label="Paper Trading",
                field_type=CredentialFieldType.BOOLEAN,
                required=False,
                default=True,
                description="모의투자 모드 사용"
            ),
        ]
    ),
    "telegram": CredentialTypeSchema(
        type_id="telegram",
        name="Telegram Bot",
        description="텔레그램 봇 알림 설정",
        icon="📱",
        fields=[
            CredentialField(
                key="bot_token",
                label="Bot Token",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="BotFather에서 발급받은 토큰"
            ),
            CredentialField(
                key="chat_id",
                label="Chat ID",
                field_type=CredentialFieldType.STRING,
                required=True,
                description="메시지를 보낼 채팅 ID"
            ),
        ]
    ),
    "openai": CredentialTypeSchema(
        type_id="openai",
        name="OpenAI",
        description="OpenAI API 키",
        icon="🤖",
        fields=[
            CredentialField(
                key="api_key",
                label="API Key",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="OpenAI API Key (sk-...)"
            ),
            CredentialField(
                key="organization",
                label="Organization ID",
                field_type=CredentialFieldType.STRING,
                required=False,
                description="조직 ID (선택)"
            ),
        ]
    ),
    "slack": CredentialTypeSchema(
        type_id="slack",
        name="Slack Webhook",
        description="Slack Incoming Webhook",
        icon="💬",
        fields=[
            CredentialField(
                key="webhook_url",
                label="Webhook URL",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="Slack Incoming Webhook URL"
            ),
        ]
    ),
    "discord": CredentialTypeSchema(
        type_id="discord",
        name="Discord Webhook",
        description="Discord Webhook 알림",
        icon="🎮",
        fields=[
            CredentialField(
                key="webhook_url",
                label="Webhook URL",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="Discord Webhook URL"
            ),
        ]
    ),
    "postgres": CredentialTypeSchema(
        type_id="postgres",
        name="PostgreSQL",
        description="PostgreSQL 데이터베이스 연결 정보",
        icon="🐘",
        fields=[
            CredentialField(
                key="host",
                label="Host",
                field_type=CredentialFieldType.STRING,
                required=True,
                description="데이터베이스 호스트 주소"
            ),
            CredentialField(
                key="port",
                label="Port",
                field_type=CredentialFieldType.NUMBER,
                required=False,
                default=5432,
                description="포트 번호"
            ),
            CredentialField(
                key="database",
                label="Database",
                field_type=CredentialFieldType.STRING,
                required=True,
                description="데이터베이스 이름"
            ),
            CredentialField(
                key="username",
                label="Username",
                field_type=CredentialFieldType.STRING,
                required=True,
                description="사용자 이름"
            ),
            CredentialField(
                key="password",
                label="Password",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="비밀번호"
            ),
            CredentialField(
                key="ssl_enabled",
                label="SSL Enabled",
                field_type=CredentialFieldType.BOOLEAN,
                required=False,
                default=False,
                description="SSL 연결 사용"
            ),
        ]
    ),
    # ============================================================
    # HTTP Authentication Types (HTTPRequestNode용)
    # ============================================================
    "http_bearer": CredentialTypeSchema(
        type_id="http_bearer",
        name="HTTP Bearer Token",
        description="Bearer Token 인증 (Authorization: Bearer <token>)",
        icon="🔑",
        fields=[
            CredentialField(
                key="token",
                label="Bearer Token",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="Bearer Token 값"
            ),
        ]
    ),
    "http_header": CredentialTypeSchema(
        type_id="http_header",
        name="HTTP Header Auth",
        description="커스텀 헤더 인증 (X-API-Key 등)",
        icon="📋",
        fields=[
            CredentialField(
                key="header_name",
                label="Header Name",
                field_type=CredentialFieldType.STRING,
                required=True,
                default="X-API-Key",
                description="헤더 이름 (예: X-API-Key, Authorization)"
            ),
            CredentialField(
                key="header_value",
                label="Header Value",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="헤더 값 (API 키 등)"
            ),
        ]
    ),
    "http_basic": CredentialTypeSchema(
        type_id="http_basic",
        name="HTTP Basic Auth",
        description="Basic Authentication (username:password)",
        icon="👤",
        fields=[
            CredentialField(
                key="username",
                label="Username",
                field_type=CredentialFieldType.STRING,
                required=True,
                description="사용자 이름"
            ),
            CredentialField(
                key="password",
                label="Password",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="비밀번호"
            ),
        ]
    ),
    "http_query": CredentialTypeSchema(
        type_id="http_query",
        name="HTTP Query Parameter Auth",
        description="쿼리 파라미터 인증 (?api_key=xxx)",
        icon="❓",
        fields=[
            CredentialField(
                key="param_name",
                label="Parameter Name",
                field_type=CredentialFieldType.STRING,
                required=True,
                default="api_key",
                description="쿼리 파라미터 이름"
            ),
            CredentialField(
                key="param_value",
                label="Parameter Value",
                field_type=CredentialFieldType.PASSWORD,
                required=True,
                description="쿼리 파라미터 값"
            ),
        ]
    ),
    "http_custom": CredentialTypeSchema(
        type_id="http_custom",
        name="Custom HTTP Credential",
        description="커스텀 HTTP 인증 - Headers, Query Params, Body에 사용할 값들을 자유롭게 정의. 워크플로우에는 credential_id만 저장되고, 실제 값은 서버에서 주입됩니다.",
        icon="⚙️",
        fields=[
            # 이 필드들은 UI 힌트용 - 실제 데이터는 동적 key-value로 저장
            CredentialField(
                key="_ui_type",
                label="UI Type",
                field_type=CredentialFieldType.STRING,
                required=False,
                default="dynamic_sections",
                description="UI 렌더링 타입 (internal)"
            ),
        ]
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
