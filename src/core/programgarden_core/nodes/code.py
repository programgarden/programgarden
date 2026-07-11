"""ProgramGarden Core - CodeNode

Universal custom-Python node. The node config carries Python source text that
defines a single `async def execute(data, params, context)` function; the
runtime compiles it, screens it (AST denylist), and runs it inside a
credential-free subprocess with restricted builtins and a scrubbed read-only
context. Return dict → declared output ports.

This node replaces the removed `Dynamic_*` injection mechanism: instead of
registering a node TYPE + injecting a class, the user just drops code into a
regular node instance. Output ports are declared per-instance via `outputs`,
which keeps downstream `{{ nodes.<id>.<port> }}` typo-guarding intact.

Security is enforced entirely by the runtime (programgarden); this class only
declares config + ports + metadata. See `programgarden_core.code_node` for the
compile/screen pipeline and `CodeNodeExecutor` for subprocess isolation.
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, TYPE_CHECKING

from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)

# ── Single source of truth for the sandbox import whitelist ─────────────────
# The CodeNode sandbox's allowed-import set is owned by
# programgarden_core.code_node.DEFAULT_ALLOWED_IMPORTS. Every AI-facing rendering
# below (the `code` field help_text, _node_guide, _anti_patterns) is DERIVED from
# it here — never hand-copied — so the schema surface can never drift from the
# enforced whitelist. Guarded by test_codenode_allowed_imports_surface_no_drift.
# code_node.py is stdlib-only, so this top-level import introduces no cycle.
# NOTE: this reflects the SHIPPED default. An embedding host MAY widen the
# whitelist at call time via `allowed_imports=`; this static surface does not
# attempt to mirror host extensions (the shipped WorkflowExecutor pins the
# default, so it is authoritative for chatbot-generated workflows).
from programgarden_core.code_node import DEFAULT_ALLOWED_IMPORTS

_ALLOWED_IMPORTS_SORTED: List[str] = sorted(DEFAULT_ALLOWED_IMPORTS)
_ALLOWED_IMPORTS_CSV: str = ", ".join(_ALLOWED_IMPORTS_SORTED)


class CodeNode(BaseNode):
    """
    Custom Python code node.

    Runs a user-supplied `execute(data, params, context)` function inside a
    sandboxed subprocess (restricted builtins, AST denylist, credential-free
    scrubbed context). Use it for logic that no existing typed node covers —
    a bespoke indicator, a custom scoring formula, ad-hoc reshaping.

    Contract:
    - The `code` text must define `async def execute(data, params, context)`
      (a plain `def execute(...)` is also accepted and auto-wrapped).
    - `data` = the bound input value (often a whole upstream array — loop over
      it inside your function; CodeNode is not per-item auto-iterated so a batch
      is one subprocess call).
    - `params` = the `params` dict (expression-bindable).
    - `context` = a READ-ONLY scrubbed context: safe helper namespaces
      (`context.date/finance/stats/format/lst`), a risk-tracker read snapshot,
      and workflow meta. It exposes NO credentials, broker, or executor.
    - Return a dict; its keys map to the declared `outputs` ports. If `outputs`
      is omitted, the entire return value is exposed on a single `result` port.

    Example DSL:
        {
            "id": "zscore",
            "type": "CodeNode",
            "code": "import statistics\\n\\nasync def execute(data, params, context):\\n    xs = data or []\\n    m = statistics.mean(xs)\\n    sd = statistics.pstdev(xs) or 1.0\\n    return {\\"z\\": (xs[-1] - m) / sd}",
            "outputs": [{"name": "z", "type": "number"}],
            "data": "{{ nodes.hist.values }}"
        }
    """

    type: Literal["CodeNode"] = "CodeNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.CodeNode.description"
    _img_url: ClassVar[str] = ""

    # Python source text. Must define `execute`.
    code: str = Field(
        default="",
        description="Python source that defines async def execute(data, params, context).",
        json_schema_extra={
            "ui_component": "code_editor",
            "language": "python",
            "help_text": "i18n:fields.CodeNode.code",
        },
    )

    # Reserved for future languages; only "python" is supported today.
    language: Literal["python"] = Field(
        default="python",
        description="Source language. Only 'python' is supported.",
    )

    # Per-instance output port declarations. Empty → single 'result' port.
    outputs: List[Dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Output port declarations [{name, type}]. Empty → single 'result' port. "
            "Declared ports are consumed downstream by {{ nodes.<id>.<port> }} expressions, "
            "not by typed-port matching; declaring them enables static typo-guarding."
        ),
    )

    # Parameters passed to execute() as `params` (expression-bindable).
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to execute() as `params`.",
    )

    # Input data passed to execute() as `data` (expression-bindable).
    data: Optional[Any] = Field(
        default=None,
        description="Input data passed to execute() as `data` (bind the whole upstream value).",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Implement a bespoke indicator or scoring formula that no existing typed node provides",
            "Reshape or aggregate upstream data with custom Python logic before a downstream node",
            "Compute a derived signal from historical bars using stdlib math/statistics",
            "Prototype a strategy calculation quickly without writing a community plugin",
        ],
        "when_not_to_use": [
            "For logic an existing typed node already covers — use ConditionNode/FieldMappingNode/IfNode/PositionSizingNode instead of re-implementing them in code",
            "To access credentials, place orders directly, or call brokers — CodeNode has no credential/broker/network access by design",
            "To reach the network or filesystem — imports of os/socket/urllib/requests and open() are blocked",
            "For simple field renames — FieldMappingNode is declarative and safer",
        ],
        "typical_scenarios": [
            "Display/sink: HTTPRequestNode → CodeNode (parse + normalize custom JSON) → TableDisplayNode — any return shape works for a sink",
            "Typed node: ScreenerNode → CodeNode (custom rank/filter returning a [{symbol, exchange, ...}] list) → OverseasStockNewOrderNode — return the standard Symbol Data Format so the typed node reads it correctly",
            "Branch/condition: OverseasStockHistoricalDataNode → CodeNode (custom momentum score returning a scalar) → IfNode — bind the scalar to IfNode.left/right",
            "Terminal compute: OverseasStockMarketDataNode → CodeNode (weighted composite logged/stored) — no downstream consumer",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Runs arbitrary pure-Python compute via a single async def execute(data, params, context)",
        "Declared 'outputs' ports keep downstream {{ nodes.<id>.<port> }} typo-guarding intact",
        "Always sandboxed: subprocess isolation + restricted builtins + AST denylist + credential-free scrubbed context",
        "Safe helper namespaces available on context (date/finance/stats/format/lst) mirror expression bindings",
        "Batch-friendly: receives the whole upstream array in `data` (one subprocess call, loop in-code)",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Dumping logic that existing typed nodes already handle into a CodeNode (e.g. re-implementing RSI, field renames, order sizing, if/else branching)",
            "reason": "Typed nodes are declarative, validated, and readable; a CodeNode blob hides intent from the workflow graph and the validation layer.",
            "alternative": "Use ConditionNode (RSI etc.), FieldMappingNode (renames), PositionSizingNode (sizing), IfNode (branching). Reserve CodeNode for logic none of them cover.",
        },
        {
            "pattern": "Trying to read credentials or call the broker from inside execute() (e.g. context.get_credential(...))",
            "reason": "CodeNode receives a scrubbed context with no credential/broker/executor access, and runs in a credential-free subprocess — such calls raise AttributeError.",
            "alternative": "Keep order/broker logic in the typed order/account nodes; feed CodeNode only the data it needs to compute.",
        },
        {
            "pattern": "Declaring 'outputs' ports whose names the return dict never sets",
            "reason": "A declared port missing from the return maps to None with a warning — a silent-looking gap downstream.",
            "alternative": "Return a dict whose keys exactly match every declared output port name.",
        },
        {
            "pattern": "Feeding a CodeNode return of non-standard shape into a typed node (order node, ConditionNode)",
            "reason": "The binding layer checks port existence but never coerces shape; a wrong shape does not fail at the CodeNode — it fails downstream where the typed node reads it (e.g. order nodes expect the Symbol Data Format array of {symbol, exchange, ...}).",
            "alternative": "When feeding a typed market/order/condition node, return the standard shape: a list of {symbol, exchange, ...} dicts. When feeding a display/sink or If/Condition scalar, any shape works.",
        },
        {
            "pattern": "Importing a third-party numeric/data library — numpy, pandas, scipy, pandas-ta, TA-Lib, scikit-learn — inside execute()",
            "reason": f"The sandbox enforces an import whitelist of pure-computation stdlib only ({_ALLOWED_IMPORTS_CSV}); any other import is rejected before the code runs with CODE_NODE_FORBIDDEN, and these libraries are not available in the sandbox.",
            "alternative": "Hand-roll the calculation in pure Python using the allowed stdlib (math, statistics, collections, itertools, functools). E.g. a rolling mean via sum()/len over a slice, an RSI via a manual gain/loss loop, a covariance via statistics — no numpy/pandas needed.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Zero-config compute on the default 'result' port",
            "description": "No outputs declared: whatever execute() returns is exposed on a single 'result' port. Here it computes a z-score from params.",
            "workflow_snippet": {
                "id": "code_zscore_default",
                "name": "CodeNode Z-Score (default result port)",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {
                        "id": "calc",
                        "type": "CodeNode",
                        "code": (
                            "import statistics\n\n"
                            "async def execute(data, params, context):\n"
                            "    xs = params.get('prices', [])\n"
                            "    if not xs:\n"
                            "        return {'zscore': None}\n"
                            "    m = statistics.mean(xs)\n"
                            "    sd = statistics.pstdev(xs) or 1.0\n"
                            "    return {'zscore': (xs[-1] - m) / sd}"
                        ),
                        "params": {"prices": [10, 11, 12, 13, 20]},
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.calc.result }}"},
                ],
                "edges": [
                    {"from": "start", "to": "calc"},
                    {"from": "calc", "to": "display"},
                ],
                "credentials": [],
            },
            "expected_output": "result = {'zscore': 2.0} (the full return dict, since no outputs were declared).",
        },
        {
            "title": "Declared multi-port outputs feed downstream nodes",
            "description": "Declaring outputs [signal, score] lets downstream nodes bind {{ nodes.calc.signal }} / {{ nodes.calc.score }} with full typo-guarding. execute() returns a dict whose keys match the declared ports.",
            "workflow_snippet": {
                "id": "code_signal_ports",
                "name": "CodeNode Declared Ports",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {
                        "id": "calc",
                        "type": "CodeNode",
                        "outputs": [
                            {"name": "signal", "type": "string"},
                            {"name": "score", "type": "number"},
                        ],
                        "code": (
                            "async def execute(data, params, context):\n"
                            "    score = float(params.get('momentum', 0))\n"
                            "    signal = 'buy' if score > 0 else 'hold'\n"
                            "    return {'signal': signal, 'score': score}"
                        ),
                        "params": {"momentum": 1.5},
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.calc.signal }}"},
                ],
                "edges": [
                    {"from": "start", "to": "calc"},
                    {"from": "calc", "to": "display"},
                ],
                "credentials": [],
            },
            "expected_output": "signal = 'buy', score = 1.5 — each on its own declared output port.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind the whole upstream value to 'data' (e.g. \"{{ nodes.hist.values }}\") and loop over it inside execute() — CodeNode is not per-item auto-iterated. Pass fixed knobs via 'params'. Declare 'outputs' when you want named ports; omit it to use the single 'result' port.",
        "output_consumption": "Downstream nodes do NOT need a matching typed port. They consume a CodeNode output by writing a {{ nodes.<id>.<port> }} expression into their own generic input field (e.g. TableDisplayNode.data, IfNode.left/right, FieldMappingNode.data) — the binding layer resolves the dict key by name, it does not type-match ports. With no outputs declared, read {{ nodes.<id>.result }} (the whole return value). A declared output port that no node references is fine; a declared port absent from the return dict resolves to None with a warning. Because ports are declared, validate() typo-guards these references.",
        "common_combinations": [
            "CodeNode → TableDisplayNode / LineChartNode / TelegramNode (display or sink — any return shape works)",
            "CodeNode → OverseasStockNewOrderNode / ConditionNode (typed node — return the standard [{symbol, exchange, ...}] shape)",
            "CodeNode → IfNode / ConditionNode (return a scalar count/bool/ratio and bind it to left/right)",
            "OverseasStockHistoricalDataNode → CodeNode (terminal compute — no downstream consumer)",
        ],
        "pitfalls": [
            "execute() must be defined exactly with that name; a missing/renamed function is rejected before run (CODE_NODE_NO_EXECUTE).",
            f"Imports are whitelisted to pure-computation stdlib only — exactly: {_ALLOWED_IMPORTS_CSV}. "
            "ANY other import is rejected before run with CODE_NODE_FORBIDDEN: third-party numeric/data "
            "libraries (numpy, pandas, scipy, pandas-ta, TA-Lib, scikit-learn) are NOT available in the "
            "sandbox, and I/O/system stdlib (os, sys, socket, subprocess, urllib, http, requests, open) is "
            "blocked. Re-implement such functionality by hand in pure Python using the allowed stdlib.",
            "No credential/broker/network access — CodeNode cannot place orders or fetch data itself; feed it data from typed nodes.",
            "Declared output ports must all appear as keys in the returned dict, or they resolve to None.",
        ],
        # Structured, machine-consumable whitelist for the AI chatbot — DERIVED
        # from DEFAULT_ALLOWED_IMPORTS (single source of truth), never hand-listed.
        "allowed_imports": list(_ALLOWED_IMPORTS_SORTED),
        "import_policy": (
            "The sandbox enforces an import WHITELIST. Only the modules in 'allowed_imports' "
            "(pure-computation stdlib, shipped default) may be imported. Every non-stdlib "
            "library — numpy, pandas, scipy, pandas-ta, TA-Lib, scikit-learn, etc. — and "
            "every I/O/system stdlib module (os, sys, socket, subprocess, urllib, http, "
            "requests, open) is rejected before execution with CODE_NODE_FORBIDDEN. If you "
            "need such functionality, HAND-ROLL it in pure Python using only the allowed "
            "modules (e.g. compute an SMA/RSI/z-score with math + statistics + collections "
            "instead of importing pandas/numpy)."
        ),
    }

    _inputs: ClassVar[List[InputPort]] = [
        InputPort(name="data", type="any", description="i18n:ports.data", required=False),
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    # Static/default output port. Per-instance ports come from get_outputs().
    _outputs: ClassVar[List[OutputPort]] = [
        OutputPort(name="result", type="any", description="i18n:outputs.CodeNode.result"),
    ]

    _version: ClassVar[str] = "1.0.1"
    _updated_at: ClassVar[str] = "2026-07-11"
    _change_note: ClassVar[Optional[str]] = "Surface sandbox import whitelist (from DEFAULT_ALLOWED_IMPORTS) in help_text/node_guide + numpy/pandas anti-pattern."

    def get_outputs(self) -> List[OutputPort]:
        """Build output ports from the per-instance `outputs` declaration.

        Empty declaration → a single `result` port (whole return value).
        This per-instance shape is what the resolver reads to typo-guard
        `{{ nodes.<id>.<port> }}` bindings.
        """
        declared = self.outputs or []
        ports: List[OutputPort] = []
        for item in declared:
            if isinstance(item, dict) and item.get("name"):
                ports.append(
                    OutputPort(
                        name=str(item["name"]),
                        type=str(item.get("type", "any")),
                        description=item.get("description"),
                    )
                )
        if not ports:
            return [OutputPort(name="result", type="any", description="i18n:outputs.CodeNode.result")]
        return ports

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema,
            FieldType,
            FieldCategory,
            UIComponent,
            ExpressionMode,
        )
        return {
            "code": FieldSchema(
                name="code",
                type=FieldType.STRING,
                description="i18n:fields.CodeNode.code",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_CODE_EDITOR,
                example="async def execute(data, params, context):\n    return {'result': data}",
                expected_type="str",
                help_text=(
                    "Define async def execute(data, params, context). Sandboxed: no "
                    "credentials/network/filesystem. Imports are whitelisted to pure-"
                    f"computation stdlib only (shipped default): {_ALLOWED_IMPORTS_CSV}. "
                    "Any other import — numpy, pandas, scipy, pandas-ta, TA-Lib, os, sys, "
                    "socket, subprocess, urllib, requests, open — is rejected with "
                    "CODE_NODE_FORBIDDEN; hand-roll such logic in pure Python."
                ),
            ),
            "outputs": FieldSchema(
                name="outputs",
                type=FieldType.ARRAY,
                array_item_type=FieldType.OBJECT,
                description="i18n:fields.CodeNode.outputs",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default=[],
                example=[{"name": "signal", "type": "string"}, {"name": "score", "type": "number"}],
                expected_type="list[dict]",
                object_schema=[
                    {"name": "name", "type": "STRING", "required": True, "description": "Output port name"},
                    {"name": "type", "type": "STRING", "required": False, "description": "Port type hint (number/string/boolean/object/array/any)"},
                ],
            ),
            "params": FieldSchema(
                name="params",
                type=FieldType.OBJECT,
                description="i18n:fields.CodeNode.params",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                default={},
                example={"period": 14},
                expected_type="dict",
            ),
            "data": FieldSchema(
                name="data",
                type=FieldType.OBJECT,
                description="i18n:fields.CodeNode.data",
                required=False,
                expression_mode=ExpressionMode.EXPRESSION_ONLY,
                category=FieldCategory.PARAMETERS,
                example_binding="{{ nodes.hist.values }}",
                expected_type="any",
            ),
        }
