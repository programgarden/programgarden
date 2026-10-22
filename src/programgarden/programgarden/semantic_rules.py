"""Public stub of the semantic-rule safety layer (platform-only; a no-op here)."""
RULE_ORDER_QTY_FROM_AI = "order_qty_from_ai"
RULE_STRUCTURED_OUTPUT_NO_SCHEMA = "structured_output_no_schema"
RULE_HARDCODED_ORDER_QTY = "hardcoded_order_qty"
RULE_ORDER_IGNORED_FIELD = "order_ignored_field"
ALL_RULES = ()
DEFAULT_SEMANTIC_SEVERITIES = {}
STRICT_SEMANTIC_SEVERITIES = {}
def analyze_workflow_semantics(*args, **kwargs):
    return []
def normalize_severities(severities=None, *args, **kwargs):
    return severities or {}
