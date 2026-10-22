"""
ProgramGarden - Credential Tools

Broker authentication credential management tools
"""

from typing import Optional, List, Dict, Any

# In-memory storage (use encrypted DB in actual implementation)
_credentials: Dict[str, Dict[str, Any]] = {}


def list_credentials() -> List[Dict[str, Any]]:
    """
    List registered credentials (summary info only)

    Returns:
        List of credential summaries (ID, name, masked account)

    Example:
        >>> list_credentials()
        [{"credential_id": "cred-ls-001", "name": "LS Securities Main Account", ...}]
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
    Register new credential

    Args:
        name: Credential name (e.g., LS Securities Main Account)
        provider: Broker (currently only ls-sec.co.kr supported)
        app_key: OpenAPI app key
        app_secret: OpenAPI secret key
        accounts: Account list [{"account_number": "...", "product": "overseas_stock"}]

    Returns:
        Created credential_id

    Example:
        >>> create_credential(
        ...     name="LS Securities Overseas Stock",
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

    # Encrypt in actual implementation
    _credentials[credential_id] = {
        "credential_id": credential_id,
        "name": name,
        "provider": provider,
        "auth": {
            "app_key": f"***encrypted:{app_key[:4]}***",  # Actually encrypt
            "app_secret": f"***encrypted:{app_secret[:4]}***",
        },
        "accounts": accounts,
        "created_at": datetime.utcnow().isoformat(),
        "is_valid": True,
    }

    return credential_id


def delete_credential(credential_id: str) -> bool:
    """
    Delete credential

    Args:
        credential_id: Credential ID to delete

    Returns:
        Whether deletion was successful

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
    Get credential (internal use, not exposed to AI)

    Args:
        credential_id: Credential ID

    Returns:
        Credential (decrypted) or None
    """
    return _credentials.get(credential_id)
