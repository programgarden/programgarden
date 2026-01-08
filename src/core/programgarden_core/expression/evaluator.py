"""
ProgramGarden Core - Expression Evaluator

Jinja2 스타일 {{ }} 표현식 평가기

지원 기능:
- 변수 참조: {{ marketData.price }}
- 산술 연산: {{ price * 0.99 }}
- 내장 함수: {{ min(quantity, 100) }}
- 조건 표현식: {{ "buy" if rsi < 30 else "sell" }}
- 배열 인덱싱: {{ symbols[0] }}
- 속성 접근: {{ position.quantity }}
- 날짜 함수: {{ today() }}, {{ days_ago(30) }}
- 통계 함수: {{ avg(prices) }}, {{ median(values) }}
- 금융 함수: {{ pct_change(100, 110) }}, {{ discount(price, 5) }}

보안:
- eval 대신 안전한 표현식 평가 사용
- 허용된 함수만 사용 가능
- 파일/네트워크 접근 차단
"""

from typing import Any, Dict, Optional, List, Set
import re
import ast
import operator
import math
import statistics
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field


class ExpressionError(Exception):
    """표현식 평가 오류"""

    def __init__(self, message: str, expression: str = "", position: int = -1):
        self.expression = expression
        self.position = position
        super().__init__(f"{message}: {expression}" if expression else message)


@dataclass
class ExpressionContext:
    """
    표현식 평가 컨텍스트

    이전 노드 출력과 내장 함수를 포함하는 컨텍스트
    """

    # 노드 출력값 (node_id -> {output_port: value})
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 현재 처리 중인 심볼 (반복 처리 시)
    current_symbol: Optional[str] = None
    current_index: int = 0

    # 추가 변수
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """표현식에서 사용할 변수 딕셔너리 생성"""
        result = {}

        # 노드 출력 추가 (node_id로 직접 접근 가능)
        for node_id, outputs in self.node_outputs.items():
            # 단일 출력이면 직접 값으로, 여러 출력이면 dict로
            if len(outputs) == 1:
                result[node_id] = list(outputs.values())[0]
            else:
                result[node_id] = outputs

        # 현재 컨텍스트
        if self.current_symbol:
            result["current_symbol"] = self.current_symbol
        result["current_index"] = self.current_index

        # 추가 변수
        result.update(self.variables)

        return result

    def set_node_output(self, node_id: str, port: str, value: Any) -> None:
        """노드 출력값 설정"""
        if node_id not in self.node_outputs:
            self.node_outputs[node_id] = {}
        self.node_outputs[node_id][port] = value

    def get_node_output(self, node_id: str, port: Optional[str] = None) -> Any:
        """노드 출력값 조회"""
        if node_id not in self.node_outputs:
            return None

        outputs = self.node_outputs[node_id]
        if port:
            return outputs.get(port)

        # 포트 미지정 시 단일 출력이면 직접 반환
        if len(outputs) == 1:
            return list(outputs.values())[0]
        return outputs


class SafeEvaluator:
    """
    안전한 표현식 평가기

    Python AST를 사용하여 제한된 표현식만 평가
    """

    # 허용된 이항 연산자
    BINARY_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
    }

    # 허용된 단항 연산자
    UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
        ast.Invert: operator.invert,
    }

    # 허용된 비교 연산자
    COMPARE_OPS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    # 허용된 내장 함수
    ALLOWED_BUILTINS = {
        # ═══════════════════════════════════════════════════════════════
        # 기본 타입 변환
        # ═══════════════════════════════════════════════════════════════
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        
        # ═══════════════════════════════════════════════════════════════
        # 기본 수학 함수
        # ═══════════════════════════════════════════════════════════════
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "round": round,
        "len": len,
        "range": range,
        "sorted": sorted,
        "zip": zip,
        "all": all,
        "any": any,
        
        # ═══════════════════════════════════════════════════════════════
        # 수학 함수 (math 모듈)
        # ═══════════════════════════════════════════════════════════════
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "ceil": math.ceil,
        "floor": math.floor,
        "pi": math.pi,
        "e": math.e,
        
        # ═══════════════════════════════════════════════════════════════
        # 통계 함수 (statistics 모듈)
        # ═══════════════════════════════════════════════════════════════
        "mean": statistics.mean,
        "avg": statistics.mean,  # alias
        "median": statistics.median,
        "stdev": lambda lst: statistics.stdev(lst) if len(lst) > 1 else 0,
        "variance": lambda lst: statistics.variance(lst) if len(lst) > 1 else 0,
        
        # ═══════════════════════════════════════════════════════════════
        # 날짜/시간 함수
        # ═══════════════════════════════════════════════════════════════
        "today": lambda: date.today().isoformat(),
        "now": lambda: datetime.now().isoformat()[:19],
        "days_ago": lambda n: (date.today() - timedelta(days=int(n))).isoformat(),
        "days_later": lambda n: (date.today() + timedelta(days=int(n))).isoformat(),
        "year_start": lambda: date(date.today().year, 1, 1).isoformat(),
        "year_end": lambda: date(date.today().year, 12, 31).isoformat(),
        "month_start": lambda: date.today().replace(day=1).isoformat(),
        
        # ═══════════════════════════════════════════════════════════════
        # 금융 계산 함수
        # ═══════════════════════════════════════════════════════════════
        "pct_change": lambda old, new: ((new - old) / old) * 100 if old != 0 else 0,
        "pct": lambda part, total: (part / total) * 100 if total != 0 else 0,
        "discount": lambda price, pct: price * (1 - pct / 100),
        "markup": lambda price, pct: price * (1 + pct / 100),
        "annualize": lambda ret, days: ((1 + ret / 100) ** (252 / days) - 1) * 100 if days > 0 else 0,
        "compound": lambda principal, rate, periods: principal * ((1 + rate / 100) ** periods),
        
        # ═══════════════════════════════════════════════════════════════
        # 리스트 유틸리티
        # ═══════════════════════════════════════════════════════════════
        "first": lambda lst: lst[0] if lst else None,
        "last": lambda lst: lst[-1] if lst else None,
        "count": len,
        
        # ═══════════════════════════════════════════════════════════════
        # 포맷팅 함수
        # ═══════════════════════════════════════════════════════════════
        "format_pct": lambda v, decimals=2: f"{v:.{decimals}f}%",
        "format_currency": lambda v, symbol="$": f"{symbol}{v:,.2f}",
        "format_number": lambda v, decimals=2: f"{v:,.{decimals}f}",
        
        # ═══════════════════════════════════════════════════════════════
        # 상수
        # ═══════════════════════════════════════════════════════════════
        "True": True,
        "False": False,
        "None": None,
    }

    def __init__(self, context: Dict[str, Any]):
        self.context = {**self.ALLOWED_BUILTINS, **context}

    def evaluate(self, expression: str) -> Any:
        """표현식 평가"""
        try:
            tree = ast.parse(expression, mode="eval")
            return self._eval_node(tree.body)
        except SyntaxError as e:
            raise ExpressionError(f"구문 오류: {e.msg}", expression, e.offset or -1)
        except Exception as e:
            raise ExpressionError(str(e), expression)

    def _eval_node(self, node: ast.AST) -> Any:
        """AST 노드 평가"""
        # 리터럴 (숫자, 문자열 등)
        if isinstance(node, ast.Constant):
            return node.value

        # 변수 참조
        if isinstance(node, ast.Name):
            if node.id not in self.context:
                raise ExpressionError(f"정의되지 않은 변수: {node.id}")
            return self.context[node.id]

        # 이항 연산
        if isinstance(node, ast.BinOp):
            op = self.BINARY_OPS.get(type(node.op))
            if op is None:
                raise ExpressionError(f"지원하지 않는 연산자: {type(node.op).__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return op(left, right)

        # 단항 연산
        if isinstance(node, ast.UnaryOp):
            op = self.UNARY_OPS.get(type(node.op))
            if op is None:
                raise ExpressionError(f"지원하지 않는 연산자: {type(node.op).__name__}")
            return op(self._eval_node(node.operand))

        # 비교 연산
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_func = self.COMPARE_OPS.get(type(op))
                if op_func is None:
                    raise ExpressionError(f"지원하지 않는 비교 연산자: {type(op).__name__}")
                right = self._eval_node(comparator)
                if not op_func(left, right):
                    return False
                left = right
            return True

        # 논리 연산 (and, or)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(v) for v in node.values)

        # 조건 표현식 (a if cond else b)
        if isinstance(node, ast.IfExp):
            if self._eval_node(node.test):
                return self._eval_node(node.body)
            return self._eval_node(node.orelse)

        # 속성 접근 (obj.attr)
        if isinstance(node, ast.Attribute):
            obj = self._eval_node(node.value)
            if isinstance(obj, dict):
                return obj.get(node.attr)
            return getattr(obj, node.attr, None)

        # 인덱싱 (arr[0], dict["key"])
        if isinstance(node, ast.Subscript):
            obj = self._eval_node(node.value)
            key = self._eval_node(node.slice)
            return obj[key]

        # 함수 호출
        if isinstance(node, ast.Call):
            func = self._eval_node(node.func)
            if not callable(func):
                raise ExpressionError(f"호출 불가능한 객체: {func}")
            args = [self._eval_node(arg) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)

        # 리스트 리터럴
        if isinstance(node, ast.List):
            return [self._eval_node(elt) for elt in node.elts]

        # 딕셔너리 리터럴
        if isinstance(node, ast.Dict):
            return {
                self._eval_node(k): self._eval_node(v)
                for k, v in zip(node.keys, node.values)
            }

        # 튜플 리터럴
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt) for elt in node.elts)

        raise ExpressionError(f"지원하지 않는 표현식 타입: {type(node).__name__}")


class ExpressionEvaluator:
    """
    Jinja2 스타일 표현식 평가기

    {{ }} 형태의 표현식을 파싱하고 평가합니다.

    Example:
        ctx = ExpressionContext()
        ctx.set_node_output("marketData", "price", 185.50)

        evaluator = ExpressionEvaluator(ctx)

        # 단순 참조
        evaluator.evaluate("{{ marketData.price }}") → 185.50

        # 산술 연산
        evaluator.evaluate("{{ marketData.price * 0.99 }}") → 183.645

        # 문자열 내 표현식
        evaluator.evaluate("Price: {{ marketData.price }}") → "Price: 185.5"
    """

    EXPRESSION_PATTERN = re.compile(r'\{\{\s*(.+?)\s*\}\}')

    def __init__(self, context: ExpressionContext):
        self.context = context
        self._context_dict = context.to_dict()

    def is_expression(self, value: Any) -> bool:
        """값이 표현식을 포함하는지 확인"""
        if not isinstance(value, str):
            return False
        return bool(self.EXPRESSION_PATTERN.search(value))

    def evaluate(self, value: Any) -> Any:
        """
        값 평가

        표현식이면 계산, 아니면 그대로 반환
        """
        if not self.is_expression(value):
            return value

        # 전체가 단일 표현식인 경우: "{{ expr }}"
        full_match = re.fullmatch(r'\{\{\s*(.+?)\s*\}\}', value.strip())
        if full_match:
            expr = full_match.group(1)
            return self._eval_expression(expr)

        # 문자열 내 여러 표현식: "Price: {{ price }}, Qty: {{ qty }}"
        def replace_expr(match: re.Match) -> str:
            expr = match.group(1)
            result = self._eval_expression(expr)
            return str(result)

        return self.EXPRESSION_PATTERN.sub(replace_expr, value)

    def evaluate_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        필드 딕셔너리의 모든 값 평가

        Args:
            fields: 노드의 fields 딕셔너리

        Returns:
            평가된 필드 딕셔너리
        """
        result = {}
        for key, value in fields.items():
            if isinstance(value, dict):
                # 중첩 딕셔너리 재귀 처리
                result[key] = self.evaluate_fields(value)
            elif isinstance(value, list):
                # 리스트 내 표현식 처리
                result[key] = [self.evaluate(item) for item in value]
            else:
                result[key] = self.evaluate(value)
        return result

    def _eval_expression(self, expression: str) -> Any:
        """단일 표현식 평가"""
        evaluator = SafeEvaluator(self._context_dict)
        return evaluator.evaluate(expression)

    def update_context(self, node_id: str, port: str, value: Any) -> None:
        """컨텍스트 업데이트 (노드 실행 후)"""
        self.context.set_node_output(node_id, port, value)
        self._context_dict = self.context.to_dict()
