"""Public stub of the CodeNode support module. The user-code screener and sandbox are
not part of the open-source build; CodeNode is declared so workflows parse and pass
structural validation, but execution refuses (see WorkflowExecutor)."""


class CodeScreenResult:
    """Structural-validation result. The open-source build performs no code screening."""

    def __init__(self):
        self.ok = True
        self.error_code = None
        self.message = None
        self.suggestion = None
        self.details = {}


def compile_code_node(code="", node_id="code", *args, **kwargs):
    return CodeScreenResult()


DEFAULT_ALLOWED_IMPORTS: frozenset = frozenset({
    "math", "cmath", "statistics", "decimal", "fractions", "numbers",
    "random", "json", "re", "datetime", "time", "calendar",
    "collections", "itertools", "functools",
    "string", "textwrap", "unicodedata",
    "heapq", "bisect", "array", "copy",
    "dataclasses", "enum", "typing",
    "hashlib", "hmac", "base64", "binascii", "zlib",
})
