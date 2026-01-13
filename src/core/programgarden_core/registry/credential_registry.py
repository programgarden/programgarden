"""
ProgramGarden Core - Credential Registry

Credential 타입 및 인스턴스 관리 레지스트리.
n8n 스타일의 credential 시스템 구현.

주의: 이 라이브러리는 평문 데이터만 다룹니다.
암호화/복호화는 외부(서버/KMS)에서 처리합니다.
"""

from typing import Dict, List, Optional, Any
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

from programgarden_core.models.credential import (
    Credential,
    CredentialTypeSchema,
    CredentialField,
    CredentialFieldType,
    BUILTIN_CREDENTIAL_SCHEMAS,
)


class CredentialTypeRegistry:
    """
    Credential 타입 레지스트리.
    어떤 credential 타입이 있는지, 각 타입에 필요한 필드가 무엇인지 관리.
    """
    
    def __init__(self):
        self._schemas: Dict[str, CredentialTypeSchema] = {}
        # Built-in 스키마 등록
        for type_id, schema in BUILTIN_CREDENTIAL_SCHEMAS.items():
            self._schemas[type_id] = schema
    
    def register(self, schema: CredentialTypeSchema) -> None:
        """새 credential 타입 등록 (플러그인용)"""
        self._schemas[schema.type_id] = schema
    
    def get(self, type_id: str) -> Optional[CredentialTypeSchema]:
        """특정 credential 타입 스키마 조회"""
        return self._schemas.get(type_id)
    
    def list_types(self) -> List[CredentialTypeSchema]:
        """모든 credential 타입 목록"""
        return list(self._schemas.values())
    
    def get_type_ids(self) -> List[str]:
        """모든 credential 타입 ID 목록"""
        return list(self._schemas.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """직렬화 (API 응답용)"""
        return {
            type_id: schema.model_dump()
            for type_id, schema in self._schemas.items()
        }


class CredentialStore:
    """
    Credential 저장소 (추상 베이스).
    
    참고: 암호화는 이 클래스에서 처리하지 않습니다.
    프로덕션에서는 서버가 외부 KMS를 통해 암호화/복호화 후
    이 저장소에 저장하거나 조회합니다.
    """
    
    def create(self, credential: Credential) -> Credential:
        raise NotImplementedError
    
    def get(self, credential_id: str) -> Optional[Credential]:
        raise NotImplementedError
    
    def list(self, user_id: str = "default", credential_type: Optional[str] = None) -> List[Credential]:
        raise NotImplementedError
    
    def update(self, credential_id: str, updates: Dict[str, Any]) -> Optional[Credential]:
        raise NotImplementedError
    
    def delete(self, credential_id: str) -> bool:
        raise NotImplementedError


class MemoryCredentialStore(CredentialStore):
    """
    메모리 기반 credential 저장소 (테스트/개발용).
    서버 재시작 시 데이터 소실.
    """
    
    def __init__(self):
        self._credentials: Dict[str, Credential] = {}
    
    def create(self, credential: Credential) -> Credential:
        if not credential.id:
            credential.id = str(uuid.uuid4())
        credential.created_at = datetime.utcnow()
        credential.updated_at = datetime.utcnow()
        self._credentials[credential.id] = credential
        return credential
    
    def get(self, credential_id: str) -> Optional[Credential]:
        return self._credentials.get(credential_id)
    
    def list(self, user_id: str = "default", credential_type: Optional[str] = None) -> List[Credential]:
        results = []
        for cred in self._credentials.values():
            if cred.user_id != user_id:
                continue
            if credential_type and cred.credential_type != credential_type:
                continue
            results.append(cred)
        return results
    
    def update(self, credential_id: str, updates: Dict[str, Any]) -> Optional[Credential]:
        cred = self._credentials.get(credential_id)
        if not cred:
            return None
        
        for key, value in updates.items():
            if hasattr(cred, key):
                setattr(cred, key, value)
        cred.updated_at = datetime.utcnow()
        return cred
    
    def delete(self, credential_id: str) -> bool:
        if credential_id in self._credentials:
            del self._credentials[credential_id]
            return True
        return False


class JsonFileCredentialStore(CredentialStore):
    """
    JSON 파일 기반 credential 저장소 (개발/테스트용).
    
    주의: 이 구현은 평문 저장입니다.
    암호화가 필요한 경우, 서버에서 암호화 후 저장하세요.
    """
    
    def __init__(self, file_path: str = "credentials.json"):
        self._file_path = Path(file_path)
        self._credentials: Dict[str, Credential] = {}
        self._load()
    
    def _load(self):
        """파일에서 credentials 로드"""
        if self._file_path.exists():
            try:
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cred_dict in data.get("credentials", []):
                        cred = Credential(**cred_dict)
                        self._credentials[cred.id] = cred
                print(f"📂 Loaded {len(self._credentials)} credentials from {self._file_path}")
            except Exception as e:
                print(f"Warning: Failed to load credentials from {self._file_path}: {e}")
    
    def _save(self):
        """credentials를 파일에 저장"""
        data = {
            "credentials": [
                cred.model_dump(mode='json')
                for cred in self._credentials.values()
            ]
        }
        with open(self._file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create(self, credential: Credential) -> Credential:
        if not credential.id:
            credential.id = str(uuid.uuid4())
        credential.created_at = datetime.utcnow()
        credential.updated_at = datetime.utcnow()
        self._credentials[credential.id] = credential
        self._save()
        return credential
    
    def get(self, credential_id: str) -> Optional[Credential]:
        return self._credentials.get(credential_id)
    
    def list(self, user_id: str = "default", credential_type: Optional[str] = None) -> List[Credential]:
        results = []
        for cred in self._credentials.values():
            if cred.user_id != user_id:
                continue
            if credential_type and cred.credential_type != credential_type:
                continue
            results.append(cred)
        return results
    
    def update(self, credential_id: str, updates: Dict[str, Any]) -> Optional[Credential]:
        cred = self._credentials.get(credential_id)
        if not cred:
            return None
        
        for key, value in updates.items():
            if hasattr(cred, key):
                setattr(cred, key, value)
        cred.updated_at = datetime.utcnow()
        self._save()
        return cred
    
    def delete(self, credential_id: str) -> bool:
        if credential_id in self._credentials:
            del self._credentials[credential_id]
            self._save()
            return True
        return False


# Global singleton instances
_credential_type_registry: Optional[CredentialTypeRegistry] = None
_credential_store: Optional[CredentialStore] = None


def get_credential_type_registry() -> CredentialTypeRegistry:
    """전역 CredentialTypeRegistry 인스턴스 반환"""
    global _credential_type_registry
    if _credential_type_registry is None:
        _credential_type_registry = CredentialTypeRegistry()
    return _credential_type_registry


def get_credential_store() -> CredentialStore:
    """전역 CredentialStore 인스턴스 반환"""
    global _credential_store
    if _credential_store is None:
        # 기본: 메모리 스토어 (테스트용)
        # 환경변수로 JSON 파일 스토어 활성화 가능
        store_path = os.environ.get("PROGRAMGARDEN_CREDENTIAL_STORE")
        if store_path:
            _credential_store = JsonFileCredentialStore(store_path)
        else:
            _credential_store = MemoryCredentialStore()
    return _credential_store


def set_credential_store(store: CredentialStore):
    """전역 CredentialStore 인스턴스 설정 (테스트/커스텀용)"""
    global _credential_store
    _credential_store = store
