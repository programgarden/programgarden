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
    node_type = result.get("node_type", "")
    
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
    
    # Translate widget_schema (Flutter dynamic widget JSON)
    if "widget_schema" in result and isinstance(result["widget_schema"], dict):
        result["widget_schema"] = _translate_widget_schema(result["widget_schema"], loc, node_type)
    
    # Translate settings_widget_schema (SETTINGS 탭 위젯)
    if "settings_widget_schema" in result and isinstance(result["settings_widget_schema"], dict):
        result["settings_widget_schema"] = _translate_widget_schema(result["settings_widget_schema"], loc, node_type)

    # Translate display_data_schema (Display 노드 런타임 데이터 스키마)
    if "display_data_schema" in result and isinstance(result["display_data_schema"], dict):
        result["display_data_schema"] = _translate_i18n_strings(result["display_data_schema"], loc)

    # Translate config_schema (노드 설정 스키마)
    if "config_schema" in result and isinstance(result["config_schema"], dict):
        result["config_schema"] = _translate_config_schema(result["config_schema"], loc)

    return result


def _translate_i18n_strings(obj: Any, locale: str) -> Any:
    """Recursively translate all i18n: prefixed strings in a nested dict/list."""
    if isinstance(obj, str):
        if obj.startswith("i18n:"):
            return t(obj[5:], locale)
        return obj
    if isinstance(obj, dict):
        return {k: _translate_i18n_strings(v, locale) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_translate_i18n_strings(item, locale) for item in obj]
    return obj


def _translate_port(port: Dict[str, Any], locale: str) -> Dict[str, Any]:
    """Translate a port definition."""
    result = port.copy()
    for field in ("description", "display_name"):
        if field in result and isinstance(result[field], str):
            if result[field].startswith("i18n:"):
                result[field] = t(result[field][5:], locale)
    return result


def _translate_config_schema(config_schema: Dict[str, Any], locale: str) -> Dict[str, Any]:
    """
    Translate config_schema fields.

    Translates fields with i18n: prefix:
    - display_name
    - description
    - placeholder
    - help_text
    - enum_labels (dict values)

    Recursively handles nested structures like object_schema.
    """
    result = {}

    for field_name, field_def in config_schema.items():
        if not isinstance(field_def, dict):
            result[field_name] = field_def
            continue

        translated_field = field_def.copy()

        # Translate display_name
        if "display_name" in translated_field and isinstance(translated_field["display_name"], str):
            if translated_field["display_name"].startswith("i18n:"):
                translated_field["display_name"] = t(translated_field["display_name"][5:], locale)

        # Translate description
        if "description" in translated_field and isinstance(translated_field["description"], str):
            if translated_field["description"].startswith("i18n:"):
                translated_field["description"] = t(translated_field["description"][5:], locale)

        # Translate placeholder
        if "placeholder" in translated_field and isinstance(translated_field["placeholder"], str):
            if translated_field["placeholder"].startswith("i18n:"):
                translated_field["placeholder"] = t(translated_field["placeholder"][5:], locale)

        # Translate help_text
        if "help_text" in translated_field and isinstance(translated_field["help_text"], str):
            if translated_field["help_text"].startswith("i18n:"):
                translated_field["help_text"] = t(translated_field["help_text"][5:], locale)

        # Translate enum_labels (dict with i18n: prefix values)
        if "enum_labels" in translated_field and isinstance(translated_field["enum_labels"], dict):
            translated_labels = {}
            for enum_key, enum_label in translated_field["enum_labels"].items():
                if isinstance(enum_label, str) and enum_label.startswith("i18n:"):
                    translated_labels[enum_key] = t(enum_label[5:], locale)
                else:
                    translated_labels[enum_key] = enum_label
            translated_field["enum_labels"] = translated_labels

        # Translate nested structures (object_schema, sub_fields, ui_options)
        for nested_key in ("object_schema", "sub_fields"):
            if nested_key in translated_field and isinstance(translated_field[nested_key], list):
                translated_field[nested_key] = _translate_i18n_strings(translated_field[nested_key], locale)

        if "ui_options" in translated_field and isinstance(translated_field["ui_options"], dict):
            translated_field["ui_options"] = _translate_i18n_strings(translated_field["ui_options"], locale)

        result[field_name] = translated_field

    return result


def _translate_widget_schema(widget: Dict[str, Any], locale: str, node_type: str = "") -> Dict[str, Any]:
    """
    Translate widget_schema recursively.
    
    Translates:
    - decoration.labelText: fieldNames.{NodeType}.{field_id} or Title Case fallback
    - decoration.helperText: fields.{NodeType}.{field_id} or i18n: prefix
    - itemLabels: i18n: prefix for dropdown options
    - Recursively handles children arrays
    """
    result = widget.copy()
    
    # Try multiple field_id sources (different widgets use different keys)
    field_id = (
        widget.get("field_key_of_pydantic") 
        or (widget.get("args", {}).get("fieldKey"))
        or (widget.get("args", {}).get("decoration", {}).get("fieldId"))
    )
    
    # Translate args.decoration
    if "args" in result and isinstance(result["args"], dict):
        args = result["args"].copy()
        
        if "decoration" in args and isinstance(args["decoration"], dict):
            decoration = args["decoration"].copy()
            
            # Translate labelText (display name)
            if "labelText" in decoration:
                label = decoration["labelText"]
                if isinstance(label, str) and label.startswith("i18n:"):
                    decoration["labelText"] = t(label[5:], locale)
                elif field_id and node_type:
                    auto_key = f"fieldNames.{node_type}.{field_id}"
                    translated = t(auto_key, locale)
                    if translated != auto_key:
                        decoration["labelText"] = translated
                # Otherwise keep original or Title Case already applied
            
            # Translate helperText (description)
            if "helperText" in decoration:
                helper = decoration["helperText"]
                if isinstance(helper, str):
                    if helper.startswith("i18n:"):
                        decoration["helperText"] = t(helper[5:], locale)
                    elif field_id and node_type:
                        # Try auto-generated key
                        auto_key = f"fields.{node_type}.{field_id}"
                        translated = t(auto_key, locale)
                        if translated != auto_key:
                            decoration["helperText"] = translated
            
            args["decoration"] = decoration
        
        # Translate text widget's text (e.g., group card title "i18n:groups.*.field_mapping")
        if "text" in args and isinstance(args["text"], str) and args["text"].startswith("i18n:"):
            args["text"] = t(args["text"][5:], locale)

        # Translate itemLabels (dropdown option labels)
        if "itemLabels" in args and isinstance(args["itemLabels"], dict):
            item_labels = args["itemLabels"].copy()
            for key, label in item_labels.items():
                if isinstance(label, str) and label.startswith("i18n:"):
                    item_labels[key] = t(label[5:], locale)
            args["itemLabels"] = item_labels
        
        # Recursively translate children array
        if "children" in args and isinstance(args["children"], list):
            args["children"] = [
                _translate_widget_schema(child, locale, node_type) 
                if isinstance(child, dict) else child
                for child in args["children"]
            ]
        
        # Translate conditional widget's child/onTrue
        if "onTrue" in args and isinstance(args["onTrue"], dict):
            args["onTrue"] = _translate_widget_schema(args["onTrue"], locale, node_type)
        if "child" in args and isinstance(args["child"], dict):
            args["child"] = _translate_widget_schema(args["child"], locale, node_type)
        
        # Translate custom_expression_toggle's fixedWidget/expressionWidget
        if "fixedWidget" in args and isinstance(args["fixedWidget"], dict):
            args["fixedWidget"] = _translate_widget_schema(args["fixedWidget"], locale, node_type)
        if "expressionWidget" in args and isinstance(args["expressionWidget"], dict):
            args["expressionWidget"] = _translate_widget_schema(args["expressionWidget"], locale, node_type)
        
        # Translate label and helperText at args level (for custom widgets like custom_expression_toggle)
        if "label" in args and isinstance(args["label"], str):
            label = args["label"]
            if label.startswith("i18n:"):
                args["label"] = t(label[5:], locale)
            elif field_id and node_type:
                # Try auto-generated key for label (same as labelText)
                auto_key = f"fieldNames.{node_type}.{field_id}"
                translated = t(auto_key, locale)
                if translated != auto_key:
                    args["label"] = translated
        
        # Translate labelText at args level (for checkbox widgets)
        if "labelText" in args and isinstance(args["labelText"], str):
            label_text = args["labelText"]
            if label_text.startswith("i18n:"):
                args["labelText"] = t(label_text[5:], locale)
            elif field_id and node_type:
                auto_key = f"fieldNames.{node_type}.{field_id}"
                translated = t(auto_key, locale)
                if translated != auto_key:
                    args["labelText"] = translated
        
        if "helperText" in args and isinstance(args["helperText"], str):
            helper = args["helperText"]
            if helper.startswith("i18n:"):
                args["helperText"] = t(helper[5:], locale)
            elif field_id and node_type:
                auto_key = f"fields.{node_type}.{field_id}"
                translated = t(auto_key, locale)
                if translated != auto_key:
                    args["helperText"] = translated
        
        # Translate fixedHelperText and expressionHelperText (for custom_expression_toggle)
        if "fixedHelperText" in args and isinstance(args["fixedHelperText"], str):
            helper = args["fixedHelperText"]
            if helper.startswith("i18n:"):
                args["fixedHelperText"] = t(helper[5:], locale)
            elif field_id and node_type:
                auto_key = f"fields.{node_type}.{field_id}"
                translated = t(auto_key, locale)
                if translated != auto_key:
                    args["fixedHelperText"] = translated
        
        if "expressionHelperText" in args and isinstance(args["expressionHelperText"], str):
            helper = args["expressionHelperText"]
            if helper.startswith("i18n:"):
                args["expressionHelperText"] = t(helper[5:], locale)
        
        result["args"] = args
    
    return result


def translate_category(category: str, locale: Optional[str] = None) -> Dict[str, str]:
    """
    Translate a category to the specified locale.
    
    Args:
        category: Category ID (e.g., "infra", "condition")
        locale: Locale code (default: current global locale)
    
    Returns:
        Dict with id, name, and description
    """
    loc = locale or _current_locale
    return {
        "id": category,
        "name": t(f"categories.{category}.name", loc),
        "description": t(f"categories.{category}.description", loc),
    }


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
