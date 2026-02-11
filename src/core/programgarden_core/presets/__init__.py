"""
ProgramGarden Core - AI Agent 프리셋 시스템

프리셋은 AIAgentNode의 역할(페르소나)을 미리 정의한 JSON 템플릿입니다.
프리셋 선택 시 system_prompt, output_schema, default_config이 자동 채워집니다.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_PRESETS_DIR = Path(__file__).parent
_PRESET_CACHE: Dict[str, Dict[str, Any]] = {}


def _load_all() -> Dict[str, Dict[str, Any]]:
    """모든 프리셋 JSON 로드 (캐시)."""
    if _PRESET_CACHE:
        return _PRESET_CACHE

    for path in _PRESETS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            preset_id = data.get("id", path.stem)
            _PRESET_CACHE[preset_id] = data
        except (json.JSONDecodeError, OSError):
            continue

    return _PRESET_CACHE


class PresetLoader:
    """프리셋 선택 시 AIAgentNode config에 머지할 데이터를 제공."""

    @staticmethod
    def load_preset(preset_id: str) -> Optional[Dict[str, Any]]:
        """프리셋 JSON 로드.

        Returns:
            프리셋 dict 또는 None (custom이거나 존재하지 않는 경우)
        """
        if not preset_id or preset_id == "custom":
            return None
        presets = _load_all()
        return presets.get(preset_id)

    @staticmethod
    def apply_preset(preset_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """프리셋을 config에 적용. 사용자가 이미 설정한 값은 유지.

        적용 우선순위: 사용자 설정 > 프리셋 기본값
        - system_prompt: 프리셋 프롬프트 뒤에 사용자 프롬프트 병합
        - output_schema: 사용자 미설정 시 프리셋 스키마 적용
        - default_config: 사용자 미설정 시 프리셋 기본값 적용
        """
        preset = PresetLoader.load_preset(preset_id)
        if not preset:
            return config

        result = config.copy()

        # system_prompt: 프리셋 + 사용자 커스텀 병합
        preset_prompt = preset.get("system_prompt", "")
        user_prompt = config.get("system_prompt", "")
        if preset_prompt:
            if user_prompt:
                result["system_prompt"] = f"{preset_prompt}\n\n{user_prompt}"
            else:
                result["system_prompt"] = preset_prompt

        # output_schema: 사용자 미설정 시 프리셋 적용
        if not config.get("output_schema") and preset.get("output_schema"):
            result["output_schema"] = preset["output_schema"]

        # output_format: 사용자 미설정 시 프리셋 default_config 적용
        default_config = preset.get("default_config", {})
        for key, value in default_config.items():
            if key not in config or config[key] is None:
                result[key] = value

        return result

    @staticmethod
    def list_presets() -> List[Dict[str, str]]:
        """사용 가능한 프리셋 목록 (id, name, description, icon)."""
        presets = _load_all()
        return [
            {
                "id": p["id"],
                "name": p.get("name", p["id"]),
                "name_en": p.get("name_en", p["id"]),
                "description": p.get("description", ""),
                "description_en": p.get("description_en", ""),
                "icon": p.get("icon", ""),
                "suggested_tool_nodes": p.get("suggested_tool_nodes", []),
            }
            for p in presets.values()
        ]

    @staticmethod
    def get_preset_ids() -> List[str]:
        """등록된 프리셋 ID 목록."""
        return list(_load_all().keys())

    @staticmethod
    def clear_cache() -> None:
        """프리셋 캐시 초기화 (테스트용)."""
        _PRESET_CACHE.clear()
