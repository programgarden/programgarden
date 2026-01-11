# I18n Implementation Status

## ✅ Completed

### Infrastructure
- ✅ Created `i18n/translator.py` with full translation engine
- ✅ Created `i18n/__init__.py` module entry point
- ✅ Created `i18n/locales/en.json` with English translations
- ✅ Created `i18n/locales/ko.json` with Korean translations
- ✅ Updated NodeTypeRegistry to support locale parameter
- ✅ Implemented `get_schema(locale=...)` and `list_schemas(locale=...)` methods
- ✅ Implemented `list_categories(locale=...)` method with category translations
- ✅ Added `translate_category()` function
- ✅ Updated `_extract_config_schema()` to use `_field_schema` with i18n keys

### Node Translations (37/37 nodes)
- ✅ All node names translated (ko/en)
- ✅ All node descriptions translated (ko/en)
- ✅ All port descriptions use i18n keys

### Category Translations (15/15 categories)
- ✅ infra, realtime, data, account, symbol
- ✅ trigger, condition, risk, order, event
- ✅ display, group, backtest, job, calculation

### Field Schema i18n
- ✅ `nodes/infra.py` - BrokerNode fields
- ✅ `nodes/symbol.py` - WatchlistNode fields
- ✅ `nodes/trigger.py` - ScheduleNode fields
- ✅ `nodes/condition.py` - LogicNode fields
- ✅ `nodes/portfolio.py` - PortfolioNode fields

### Plugin i18n Support
- ✅ `PluginSchema` with `locales` field for multi-language support
- ✅ `get_localized_name()`, `get_localized_description()` methods
- ✅ `get_localized_field_description()` method
- ✅ `to_localized_dict()` method for API responses
- ✅ `list_plugins(locale=...)` method
- ✅ Example: RSI plugin with Korean translations

### Error Messages
- ✅ Common error codes translated (ko/en)
- ✅ Parameterized error messages support (e.g., `{node_id}`)

## Translation Key Format

All user-facing strings use the format: `"i18n:{key}"`

Examples:
```python
description: str = "i18n:nodes.StartNode.description"
OutputPort(name="symbols", description="i18n:ports.symbols")
FieldSchema(description="i18n:fields.BrokerNode.provider")
```

### Key Prefixes
| Prefix | Usage |
|--------|-------|
| `nodes.{NodeName}.name` | Node display name |
| `nodes.{NodeName}.description` | Node description |
| `ports.{portName}` | Port description |
| `categories.{category}.name` | Category display name |
| `categories.{category}.description` | Category description |
| `fields.{NodeName}.{fieldName}` | Field description |
| `enums.{enumType}.{value}` | Enum value label |
| `errors.{ERROR_CODE}` | Error message |

## Usage Examples

### Node Schema with Locale
```python
from programgarden_core.registry import NodeTypeRegistry

registry = NodeTypeRegistry()

# Get schema in Korean
schema_ko = registry.get_schema('BrokerNode', locale='ko')
print(schema_ko.config_schema['provider']['description'])
# Output: "브로커 제공자"

# Get schema in English
schema_en = registry.get_schema('BrokerNode', locale='en')
print(schema_en.config_schema['provider']['description'])
# Output: "Broker provider"
```

### Category List with Locale
```python
categories = registry.list_categories(locale='ko')
# Output: [{'id': 'infra', 'name': '인프라', 'description': '워크플로우 시작점과 브로커 연결', 'count': 2}, ...]
```

### Plugin with Locale
```python
from programgarden_core.registry import PluginRegistry

registry = PluginRegistry()
schema = registry.get_schema('RSI')

# Get localized data
localized = schema.to_localized_dict('ko')
print(localized['display_name'])  # "RSI (상대강도지수)"
print(localized['display_description'])  # "RSI 과매수/과매도 조건"
```

### Error Message Translation
```python
from programgarden_core.i18n import t

# Simple error
print(t('errors.LOGIN_ERROR', 'ko'))  # "로그인에 실패했습니다."

# With parameters
print(t('errors.NODE_NOT_FOUND', 'ko', node_id='condition_1'))
# Output: "노드를 찾을 수 없습니다: condition_1"
```

## Fallback Strategy

When a translation key is not found:
1. Try requested locale (e.g., 'ko')
2. Fallback to English ('en')
3. Return the key itself as last resort

## Plugin i18n for Community Developers

Community plugin developers can add translations by including a `locales` dict:

```python
PluginSchema(
    id="RSI",
    name="RSI (Relative Strength Index)",  # English default
    description="RSI overbought/oversold condition",  # English default
    fields_schema={
        "period": {"type": "int", "default": 14, "description": "RSI period"},
    },
    locales={
        "ko": {
            "name": "RSI (상대강도지수)",
            "description": "RSI 과매수/과매도 조건",
            "fields.period": "RSI 기간",
        },
    },
)
```

## Test Results

✅ Verified working:
- English translations display correctly
- Korean translations display correctly
- Port descriptions translate properly
- Node descriptions translate properly
- Category translations work
- Field descriptions translate properly
- Plugin localization works
- Error message translation works
- Fallback to English works when key missing
