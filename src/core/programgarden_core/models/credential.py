"""
ProgramGarden Core - Credential 모델

인증 정보 (Credential Layer)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


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

    class Config:
        use_enum_values = True


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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        use_enum_values = True

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
