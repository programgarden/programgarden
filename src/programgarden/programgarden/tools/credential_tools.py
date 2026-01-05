"""
ProgramGarden - Credential Tools

증권사 인증 정보 관리 도구
"""

from typing import Optional, List, Dict, Any

# 인메모리 저장소 (실제 구현에서는 암호화된 DB 사용)
_credentials: Dict[str, Dict[str, Any]] = {}


def list_credentials() -> List[Dict[str, Any]]:
    """
    등록된 인증 정보 목록 조회 (요약 정보만)

    Returns:
        인증 정보 요약 목록 (ID, 이름, 계좌 마스킹)

    Example:
        >>> list_credentials()
        [{"credential_id": "cred-ls-001", "name": "LS증권 메인계좌", ...}]
    """
    from programgarden_core import BrokerCredential

    result = []
    for cred_id, data in _credentials.items():
        cred = BrokerCredential(**data)
        result.append(cred.to_summary())

    return result


def create_credential(
    name: str,
    provider: str,
    app_key: str,
    app_secret: str,
    accounts: List[Dict[str, Any]],
) -> str:
    """
    새 인증 정보 등록

    Args:
        name: 인증 정보 이름 (예: LS증권 메인계좌)
        provider: 증권사 (현재 ls-sec.co.kr만 지원)
        app_key: OpenAPI 앱키
        app_secret: OpenAPI 시크릿키
        accounts: 계좌 목록 [{"account_number": "...", "product": "overseas_stock"}]

    Returns:
        생성된 credential_id

    Example:
        >>> create_credential(
        ...     name="LS증권 해외주식",
        ...     provider="ls-sec.co.kr",
        ...     app_key="xxx",
        ...     app_secret="xxx",
        ...     accounts=[{"account_number": "50123456-01", "product": "overseas_stock"}]
        ... )
        "cred-abc123"
    """
    import uuid
    from datetime import datetime

    credential_id = f"cred-{uuid.uuid4().hex[:8]}"

    # 실제 구현에서는 암호화 저장
    _credentials[credential_id] = {
        "credential_id": credential_id,
        "name": name,
        "provider": provider,
        "auth": {
            "app_key": f"***encrypted:{app_key[:4]}***",  # 실제로는 암호화
            "app_secret": f"***encrypted:{app_secret[:4]}***",
        },
        "accounts": accounts,
        "created_at": datetime.utcnow().isoformat(),
        "is_valid": True,
    }

    return credential_id


def delete_credential(credential_id: str) -> bool:
    """
    인증 정보 삭제

    Args:
        credential_id: 삭제할 인증 정보 ID

    Returns:
        삭제 성공 여부

    Example:
        >>> delete_credential("cred-abc123")
        True
    """
    if credential_id in _credentials:
        del _credentials[credential_id]
        return True
    return False


def get_credential(credential_id: str) -> Optional[Dict[str, Any]]:
    """
    인증 정보 조회 (내부용, AI에게 노출 안 함)

    Args:
        credential_id: 인증 정보 ID

    Returns:
        인증 정보 (복호화됨) 또는 None
    """
    return _credentials.get(credential_id)
