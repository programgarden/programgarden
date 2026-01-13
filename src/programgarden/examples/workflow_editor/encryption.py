"""
로컬 개발용 Credential 암호화 유틸리티

프로덕션에서는 외부 KMS(AWS KMS, GCP KMS, Vault 등)를 사용합니다.
이 모듈은 로컬 테스트 환경에서 외부 KMS를 시뮬레이션합니다.

사용법:
    from encryption import encrypt_data, decrypt_data
    
    # 암호화
    encrypted = encrypt_data({"appkey": "xxx", "appsecret": "yyy"})
    
    # 복호화
    decrypted = decrypt_data(encrypted)
"""

import os
import json
import base64
from typing import Any, Optional


def _get_encryption_key() -> Optional[bytes]:
    """
    환경변수에서 암호화 키 로드.
    CREDENTIAL_ENCRYPTION_KEY: 32바이트(64자) hex string
    """
    key_hex = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
    if key_hex:
        try:
            key = bytes.fromhex(key_hex)
            if len(key) == 32:
                return key
            print(f"⚠️ CREDENTIAL_ENCRYPTION_KEY must be 32 bytes (64 hex chars), got {len(key)} bytes")
        except ValueError:
            print("⚠️ CREDENTIAL_ENCRYPTION_KEY is not valid hex")
    return None


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """XOR 기반 암호화 (로컬 테스트용)"""
    key_extended = (key * ((len(data) // len(key)) + 1))[:len(data)]
    return bytes(a ^ b for a, b in zip(data, key_extended))


def encrypt_data(data: Any) -> str:
    """
    데이터를 암호화하여 base64 문자열로 반환.
    
    암호화 키가 없으면 평문 JSON을 반환합니다 (개발 편의).
    
    Args:
        data: 암호화할 데이터 (dict, list 등 JSON 직렬화 가능한 객체)
        
    Returns:
        암호화된 base64 문자열 또는 평문 JSON
    """
    key = _get_encryption_key()
    json_str = json.dumps(data, ensure_ascii=False)
    
    if not key:
        # 키가 없으면 평문 반환 (개발 편의)
        return json_str
    
    encrypted = _xor_encrypt(json_str.encode('utf-8'), key)
    return "ENC:" + base64.urlsafe_b64encode(encrypted).decode('ascii')


def decrypt_data(encrypted: str) -> Any:
    """
    암호화된 문자열을 복호화하여 원본 데이터로 반환.
    
    Args:
        encrypted: 암호화된 base64 문자열 (ENC: 접두어) 또는 평문 JSON
        
    Returns:
        복호화된 데이터 (dict, list 등)
    """
    key = _get_encryption_key()
    
    # ENC: 접두어가 없으면 평문으로 간주
    if not encrypted.startswith("ENC:"):
        try:
            return json.loads(encrypted)
        except json.JSONDecodeError:
            return encrypted  # 이미 dict 등의 객체일 수 있음
    
    if not key:
        print("⚠️ Cannot decrypt: CREDENTIAL_ENCRYPTION_KEY not set")
        return {}
    
    try:
        encrypted_bytes = base64.urlsafe_b64decode(encrypted[4:])  # "ENC:" 제거
        decrypted = _xor_encrypt(encrypted_bytes, key)  # XOR은 대칭
        return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        print(f"⚠️ Decryption failed: {e}")
        return {}


def is_encryption_enabled() -> bool:
    """암호화가 활성화되어 있는지 확인"""
    return _get_encryption_key() is not None
