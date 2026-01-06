"""
ProgramGarden Core - Translator

Translation utility for i18n support.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Global locale setting
_current_locale: str = "en"
_translations: Dict[str, Dict[str, str]] = {}
_locales_dir: Path = Path(__file__).parent / "locales"


def _load_locale(locale: str) -> Dict[str, str]:
    """Load translation file for a locale."""
    if locale in _translations:
        return _translations[locale]
    
    locale_file = _locales_dir / f"{locale}.json"
    if not locale_file.exists():
        return {}
    
    with open(locale_file, "r", encoding="utf-8") as f:
        _translations[locale] = json.load(f)
    
    return _translations[locale]


def set_locale(locale: str) -> None:
    """Set the global locale."""
    global _current_locale
    _current_locale = locale
    _load_locale(locale)


def get_locale() -> str:
    """Get the current global locale."""
    return _current_locale


def get_available_locales() -> List[str]:
    """Get list of available locales."""
    locales = []
    for f in _locales_dir.glob("*.json"):
        locales.append(f.stem)
    return sorted(locales)


def t(key: str, locale: Optional[str] = None, **kwargs) -> str:
    """
    Translate a key to the specified locale.
    
    Args:
        key: Translation key (e.g., "nodes.WatchlistNode.description")
        locale: Locale code (default: current global locale)
        **kwargs: Format arguments for string interpolation
    
    Returns:
        Translated string, or the key itself if not found
    """
    loc = locale or _current_locale
    translations = _load_locale(loc)
    
    # Try exact key
    if key in translations:
        text = translations[key]
        if kwargs:
            return text.format(**kwargs)
        return text
    
    # Fallback to English
    if loc != "en":
        en_translations = _load_locale("en")
        if key in en_translations:
            text = en_translations[key]
            if kwargs:
                return text.format(**kwargs)
            return text
    
    # Return key as fallback
    return key


def translate_schema(schema: Dict[str, Any], locale: Optional[str] = None) -> Dict[str, Any]:
    """
    Translate all translatable fields in a schema dict.
    
    Looks for fields like 'description', 'name' that have translation keys.
    """
    loc = locale or _current_locale
    result = schema.copy()
    
    # Translate node_type (display name)
    if "node_type" in result:
        name_key = f"nodes.{result['node_type']}.name"
        result["display_name"] = t(name_key, loc)
    
    # Translate top-level description
    if "description" in result and isinstance(result["description"], str):
        key = result["description"]
        if key.startswith("i18n:"):
            result["description"] = t(key[5:], loc)
    
    # Translate inputs
    if "inputs" in result:
        result["inputs"] = [
            _translate_port(port, loc) for port in result["inputs"]
        ]
    
    # Translate outputs
    if "outputs" in result:
        result["outputs"] = [
            _translate_port(port, loc) for port in result["outputs"]
        ]
    
    # Translate config_schema
    if "config_schema" in result:
        result["config_schema"] = {
            k: _translate_field(v, loc)
            for k, v in result["config_schema"].items()
        }
    
    return result


def _translate_port(port: Dict[str, Any], locale: str) -> Dict[str, Any]:
    """Translate a port definition."""
    result = port.copy()
    if "description" in result and isinstance(result["description"], str):
        key = result["description"]
        if key.startswith("i18n:"):
            result["description"] = t(key[5:], locale)
    return result


def _translate_field(field: Dict[str, Any], locale: str) -> Dict[str, Any]:
    """Translate a field definition."""
    result = field.copy()
    if "description" in result and isinstance(result["description"], str):
        key = result["description"]
        if key.startswith("i18n:"):
            result["description"] = t(key[5:], locale)
    return result


class Translator:
    """
    Translator instance for specific locale.
    
    Useful when you need to pass a translator around.
    """
    
    def __init__(self, locale: str = "en"):
        self.locale = locale
        _load_locale(locale)
    
    def t(self, key: str, **kwargs) -> str:
        """Translate a key."""
        return t(key, self.locale, **kwargs)
    
    def translate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a schema dict."""
        return translate_schema(schema, self.locale)
