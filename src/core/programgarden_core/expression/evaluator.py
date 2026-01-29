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

네임스페이스 함수:
- 날짜: {{ date.today() }}, {{ date.ago(30, format='yyyymmdd') }}
- 통계: {{ stats.mean(prices) }}, {{ stats.median(values) }}
- 금융: {{ finance.pct_change(100, 110) }}, {{ finance.discount(price, 5) }}
- 포맷: {{ format.pct(0.12) }}, {{ format.currency(1234.56) }}
- 리스트: {{ list.first(items) }}, {{ list.pluck(data, 'a.b.c') }}

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


def _get_nested_value(obj: Any, path: str) -> Any:
    """
    객체에서 점 표기법 경로로 중첩 값 추출
    
    예: _get_nested_value({'a': {'b': {'c': 1}}}, 'a.b.c') → 1
    """
    keys = path.split('.')
    current = obj
    for key in keys:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current


def _pluck(lst: List[Any], path: str) -> List[Any]:
    """
    배열의 각 요소에서 특정 경로의 값을 추출

    지원 형식:
    - pluck(items, 'name') → 단일 키
    - pluck(items, 'details.price') → 다중 중첩 (점 표기법)

    예:
    >>> data = [{'a': {'b': 1}}, {'a': {'b': 2}}]
    >>> pluck(data, 'a.b')
    [1, 2]

    >>> values = [{'symbol': 'AAPL', 'time_series': [...]}, ...]
    >>> pluck(values, 'time_series')
    [[...], [...]]
    """
    # NodeOutputProxy인 경우 내부 배열 추출
    if hasattr(lst, '_get_array'):
        lst = lst._get_array()
    if not isinstance(lst, (list, tuple)):
        return []
    return [_get_nested_value(item, path) for item in lst]


def _flatten(lst: List[Any], nested_key: str) -> List[Any]:
    """
    배열의 각 요소에서 중첩 배열을 평탄화하면서 부모 필드를 유지

    예:
    >>> data = [
    ...     {'symbol': 'AAPL', 'time_series': [{'date': '20251224', 'rsi': 33.5}]},
    ...     {'symbol': 'TSLA', 'time_series': [{'date': '20251224', 'rsi': 62.1}]},
    ... ]
    >>> flatten(data, 'time_series')
    [
        {'symbol': 'AAPL', 'date': '20251224', 'rsi': 33.5},
        {'symbol': 'TSLA', 'date': '20251224', 'rsi': 62.1},
    ]
    """
    # NodeOutputProxy인 경우 내부 배열 추출
    if hasattr(lst, '_get_array'):
        lst = lst._get_array()
    if not isinstance(lst, (list, tuple)):
        return []
    
    result = []
    for item in lst:
        if not isinstance(item, dict):
            continue
        
        nested_rows = item.get(nested_key, [])
        if not isinstance(nested_rows, (list, tuple)):
            continue
        
        # 부모 필드 추출 (nested_key 제외)
        parent_fields = {k: v for k, v in item.items() if k != nested_key}
        
        # 각 중첩 행에 부모 필드 병합
        for row in nested_rows:
            if isinstance(row, dict):
                result.append({**parent_fields, **row})
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 함수 네임스페이스 클래스들
# ═══════════════════════════════════════════════════════════════════════════════


class DateNamespace:
    """
    날짜/시간 함수 네임스페이스

    사용 예시:
        {{ date.today() }}                    # "2026-01-29"
        {{ date.today(format='yyyymmdd') }}   # "20260129"
        {{ date.ago(30) }}                    # 30일 전 (ISO 형식)
        {{ date.ago(30, format='yyyymmdd') }} # 30일 전 (YYYYMMDD)
        {{ date.ago(30, format='%Y/%m/%d') }} # 30일 전 (사용자 정의)
    """

    FORMAT_PRESETS = {
        'yyyymmdd': '%Y%m%d',
        'iso': '%Y-%m-%d',
    }

    def _format_date(self, d: date, fmt: Optional[str] = None) -> str:
        """날짜를 지정된 포맷으로 변환"""
        if fmt is None:
            return d.isoformat()
        # 프리셋 또는 사용자 정의 strftime 형식
        strftime_fmt = self.FORMAT_PRESETS.get(fmt, fmt)
        return d.strftime(strftime_fmt)

    def today(self, format: Optional[str] = None) -> str:
        """오늘 날짜"""
        return self._format_date(date.today(), format)

    def now(self) -> str:
        """현재 시간 (ISO 형식)"""
        return datetime.now().isoformat()[:19]

    def ago(self, days: int, format: Optional[str] = None) -> str:
        """n일 전"""
        d = date.today() - timedelta(days=int(days))
        return self._format_date(d, format)

    def later(self, days: int, format: Optional[str] = None) -> str:
        """n일 후"""
        d = date.today() + timedelta(days=int(days))
        return self._format_date(d, format)

    def months_ago(self, months: int, format: Optional[str] = None) -> str:
        """n개월 전 (30일 기준)"""
        d = date.today() - timedelta(days=int(months) * 30)
        return self._format_date(d, format)

    def year_start(self, format: Optional[str] = None) -> str:
        """연초 (1월 1일)"""
        d = date(date.today().year, 1, 1)
        return self._format_date(d, format)

    def year_end(self, format: Optional[str] = None) -> str:
        """연말 (12월 31일)"""
        d = date(date.today().year, 12, 31)
        return self._format_date(d, format)

    def month_start(self, format: Optional[str] = None) -> str:
        """월초"""
        d = date.today().replace(day=1)
        return self._format_date(d, format)


class FinanceNamespace:
    """
    금융 계산 함수 네임스페이스

    사용 예시:
        {{ finance.pct_change(100, 110) }}    # 10.0 (%)
        {{ finance.discount(1000, 20) }}      # 800.0
        {{ finance.annualize(5, 30) }}        # 연률화 수익률
    """

    def pct_change(self, old: float, new: float) -> float:
        """변화율 (%) = ((new - old) / old) * 100"""
        if old == 0:
            return 0.0
        return ((new - old) / old) * 100

    def pct(self, part: float, total: float) -> float:
        """비율 (%) = (part / total) * 100"""
        if total == 0:
            return 0.0
        return (part / total) * 100

    def discount(self, price: float, pct: float) -> float:
        """할인가 = price * (1 - pct/100)"""
        return price * (1 - pct / 100)

    def markup(self, price: float, pct: float) -> float:
        """인상가 = price * (1 + pct/100)"""
        return price * (1 + pct / 100)

    def annualize(self, ret: float, days: int) -> float:
        """연률화 수익률 = ((1 + ret/100)^(252/days) - 1) * 100"""
        if days <= 0:
            return 0.0
        return ((1 + ret / 100) ** (252 / days) - 1) * 100

    def compound(self, principal: float, rate: float, periods: int) -> float:
        """복리 = principal * ((1 + rate/100)^periods)"""
        return principal * ((1 + rate / 100) ** periods)


class StatsNamespace:
    """
    통계 함수 네임스페이스

    사용 예시:
        {{ stats.mean([1, 2, 3, 4, 5]) }}     # 3.0
        {{ stats.median([1, 2, 3, 4, 5]) }}   # 3
        {{ stats.stdev([1, 2, 3, 4, 5]) }}    # 표준편차
    """

    def mean(self, values: List[float]) -> float:
        """평균"""
        if not values:
            return 0.0
        return statistics.mean(values)

    def avg(self, values: List[float]) -> float:
        """평균 (mean의 별칭)"""
        return self.mean(values)

    def median(self, values: List[float]) -> float:
        """중앙값"""
        if not values:
            return 0.0
        return statistics.median(values)

    def stdev(self, values: List[float]) -> float:
        """표준편차"""
        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)

    def variance(self, values: List[float]) -> float:
        """분산"""
        if len(values) < 2:
            return 0.0
        return statistics.variance(values)


class FormatNamespace:
    """
    포맷팅 함수 네임스페이스

    사용 예시:
        {{ format.pct(0.1234) }}              # "12.34%"
        {{ format.currency(1234.56) }}        # "$1,234.56"
        {{ format.number(1234567.89, 1) }}    # "1,234,567.9"
    """

    def pct(self, value: float, decimals: int = 2) -> str:
        """퍼센트 포맷 (값 * 100 하지 않음, 이미 % 값이라고 가정)"""
        return f"{value:.{decimals}f}%"

    def currency(self, value: float, symbol: str = "$", decimals: int = 2) -> str:
        """통화 포맷"""
        return f"{symbol}{value:,.{decimals}f}"

    def number(self, value: float, decimals: int = 2) -> str:
        """숫자 포맷 (천 단위 콤마)"""
        return f"{value:,.{decimals}f}"


class ListNamespace:
    """
    리스트 유틸리티 네임스페이스

    사용 예시:
        {{ list.first([1, 2, 3]) }}           # 1
        {{ list.last([1, 2, 3]) }}            # 3
        {{ list.pluck(items, 'name') }}       # 필드 추출
    """

    def first(self, items: List[Any]) -> Optional[Any]:
        """첫 번째 요소"""
        if hasattr(items, '_get_array'):
            items = items._get_array()
        return items[0] if items else None

    def last(self, items: List[Any]) -> Optional[Any]:
        """마지막 요소"""
        if hasattr(items, '_get_array'):
            items = items._get_array()
        return items[-1] if items else None

    def count(self, items: List[Any]) -> int:
        """요소 개수"""
        if hasattr(items, '_get_array'):
            items = items._get_array()
        return len(items) if items else 0

    def pluck(self, items: List[Any], path: str) -> List[Any]:
        """배열에서 특정 필드 값 추출 (점 표기법 지원)"""
        return _pluck(items, path)

    def flatten(self, items: List[Any], nested_key: str) -> List[Any]:
        """중첩 배열 평탄화 (부모 필드 유지)"""
        return _flatten(items, nested_key)


# ═══════════════════════════════════════════════════════════════════════════════
# 예외 및 프록시 클래스들
# ═══════════════════════════════════════════════════════════════════════════════


class ExpressionError(Exception):
    """표현식 평가 오류"""

    def __init__(self, message: str, expression: str = "", position: int = -1):
        self.expression = expression
        self.position = position
        super().__init__(f"{message}: {expression}" if expression else message)


class NodeOutputProxy:
    """
    노드 출력 프록시 (메서드 체이닝 지원)

    nodes.nodeId로 접근하면 이 프록시 객체가 반환됩니다.
    체이닝 메서드를 통해 데이터를 조작할 수 있습니다.

    Example:
        {{ nodes.account.all() }}                      # 전체 배열
        {{ nodes.account.first() }}                    # 첫 번째 아이템
        {{ nodes.account.filter('pnl > 0') }}          # 조건 필터링
        {{ nodes.account.map('symbol') }}              # 필드 추출
        {{ nodes.account.filter('pnl > 0').sum('quantity') }}  # 체이닝
    """

    def __init__(self, data: Any):
        """
        Args:
            data: 노드 출력 데이터 (dict 또는 list)
        """
        self._data = data

    def _get_array(self) -> List[Any]:
        """내부 데이터를 배열로 변환"""
        if isinstance(self._data, list):
            return self._data
        elif isinstance(self._data, dict):
            # dict인 경우 values 또는 기본 출력 포트 찾기
            # positions, symbols, values, data, items 등 배열 출력 포트 확인
            for key in ["positions", "symbols", "values", "data", "items", "array", "results"]:
                if key in self._data and isinstance(self._data[key], list):
                    return self._data[key]
            # 단일 dict는 [dict]로 반환
            return [self._data]
        return []

    # === 기본 메서드 ===

    def all(self) -> List[Any]:
        """전체 배열 반환"""
        return self._get_array()

    def first(self) -> Optional[Any]:
        """첫 번째 아이템 반환"""
        arr = self._get_array()
        return arr[0] if arr else None

    def last(self) -> Optional[Any]:
        """마지막 아이템 반환"""
        arr = self._get_array()
        return arr[-1] if arr else None

    def count(self) -> int:
        """아이템 개수 반환"""
        return len(self._get_array())

    # === 데이터 조작 메서드 (체이닝 가능) ===

    def filter(self, condition: str) -> "NodeOutputProxy":
        """
        조건에 맞는 아이템만 필터링

        Args:
            condition: 조건 문자열 (예: "pnl > 0", "quantity >= 10")

        Returns:
            NodeOutputProxy: 필터링된 결과 (체이닝 가능)
        """
        arr = self._get_array()
        filtered = _filter_data(arr, condition)
        return NodeOutputProxy(filtered)

    def map(self, field: str) -> "NodeOutputProxy":
        """
        각 아이템에서 특정 필드 추출

        Args:
            field: 추출할 필드명 (점 표기법 지원: "nested.field")

        Returns:
            NodeOutputProxy: 추출된 값 배열 (체이닝 가능)
        """
        arr = self._get_array()
        mapped = [_get_nested_value(item, field) for item in arr if isinstance(item, dict)]
        return NodeOutputProxy(mapped)

    def sum(self, field: str) -> float:
        """
        특정 필드의 합계

        Args:
            field: 합계를 구할 필드명

        Returns:
            float: 합계
        """
        arr = self._get_array()
        return sum(
            _get_nested_value(item, field) or 0
            for item in arr
            if isinstance(item, dict)
        )

    def avg(self, field: str) -> float:
        """
        특정 필드의 평균

        Args:
            field: 평균을 구할 필드명

        Returns:
            float: 평균
        """
        arr = self._get_array()
        values = [
            _get_nested_value(item, field)
            for item in arr
            if isinstance(item, dict) and _get_nested_value(item, field) is not None
        ]
        return sum(values) / len(values) if values else 0

    def flatten(self, nested_key: str) -> "NodeOutputProxy":
        """
        중첩 배열 평탄화 (부모 필드 유지)

        Args:
            nested_key: 평탄화할 중첩 배열 필드명

        Returns:
            NodeOutputProxy: 평탄화된 결과 (체이닝 가능)
        """
        arr = self._get_array()
        flattened = _flatten(arr, nested_key)
        return NodeOutputProxy(flattened)

    # === 속성 접근 ===

    def __getattr__(self, name: str) -> Any:
        """
        속성 접근 (dict 키 또는 출력 포트)

        nodes.account.positions → positions 포트 값
        """
        if isinstance(self._data, dict):
            if name in self._data:
                value = self._data[name]
                # 배열이면 프록시로 감싸서 체이닝 지원
                if isinstance(value, list):
                    return NodeOutputProxy(value)
                return value
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __getitem__(self, key: Any) -> Any:
        """인덱스 접근"""
        arr = self._get_array()
        if isinstance(key, int):
            return arr[key] if 0 <= key < len(arr) else None
        elif isinstance(self._data, dict):
            return self._data.get(key)
        return None

    def __repr__(self) -> str:
        return f"NodeOutputProxy({self._data!r})"


class NodesProxy:
    """
    nodes 객체 프록시

    {{ nodes.nodeId }} 형태로 접근하면 NodeOutputProxy를 반환합니다.
    """

    def __init__(self, node_outputs: Dict[str, Dict[str, Any]]):
        self._outputs = node_outputs

    def __getattr__(self, node_id: str) -> NodeOutputProxy:
        """nodes.nodeId 접근"""
        if node_id in self._outputs:
            return NodeOutputProxy(self._outputs[node_id])
        raise AttributeError(f"Node '{node_id}' not found in outputs")

    def __getitem__(self, node_id: str) -> NodeOutputProxy:
        """nodes["node-id"] 접근 (특수문자 노드 ID 지원)"""
        if node_id in self._outputs:
            return NodeOutputProxy(self._outputs[node_id])
        raise KeyError(f"Node '{node_id}' not found in outputs")

    def __repr__(self) -> str:
        return f"NodesProxy({list(self._outputs.keys())})"


def _filter_data(data: List[Any], condition: str) -> List[Any]:
    """
    조건에 맞는 아이템 필터링

    지원 조건:
    - "field > value"
    - "field >= value"
    - "field < value"
    - "field <= value"
    - "field == value"
    - "field != value"
    """
    import re
    match = re.match(r"(\w+(?:\.\w+)*)\s*(>|<|>=|<=|==|!=)\s*(.+)", condition.strip())
    if not match:
        return data

    field_path, op, value_str = match.groups()
    value = _parse_value(value_str.strip())

    ops = {
        '>': lambda a, b: a is not None and a > b,
        '<': lambda a, b: a is not None and a < b,
        '>=': lambda a, b: a is not None and a >= b,
        '<=': lambda a, b: a is not None and a <= b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
    }

    op_func = ops.get(op)
    if not op_func:
        return data

    return [
        item for item in data
        if isinstance(item, dict) and op_func(_get_nested_value(item, field_path), value)
    ]


def _parse_value(value_str: str) -> Any:
    """문자열 값을 적절한 타입으로 변환"""
    # 문자열 리터럴
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1]
    # 불리언
    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    # None
    if value_str.lower() == 'none':
        return None
    # 숫자
    try:
        return int(value_str)
    except ValueError:
        try:
            return float(value_str)
        except ValueError:
            return value_str


@dataclass
class ExpressionContext:
    """
    표현식 평가 컨텍스트

    이전 노드 출력과 내장 함수를 포함하는 컨텍스트

    자동 반복 실행 지원:
    - item: 현재 반복 중인 아이템 (직전 노드 출력)
    - index: 현재 반복 인덱스 (0부터 시작)
    - total: 전체 아이템 개수
    """

    # 노드 출력값 (node_id -> {output_port: value})
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # === 반복 컨텍스트 ===
    # 현재 반복 중인 아이템 (직전 노드 출력의 단일 요소)
    item: Optional[Any] = None
    # 현재 반복 인덱스 (0부터 시작)
    index: int = 0
    # 전체 아이템 개수
    total: int = 0

    # 현재 처리 중인 심볼 (레거시, 호환성 유지)
    current_symbol: Optional[str] = None
    current_index: int = 0

    # 추가 변수
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """표현식에서 사용할 변수 딕셔너리 생성"""
        result = {}

        # 노드 출력 추가 (NodesProxy로 감싸서 메서드 체이닝 지원)
        # nodes.account.all(), nodes.account.filter('pnl > 0') 등 지원
        result["nodes"] = NodesProxy(self.node_outputs)

        # === 반복 컨텍스트 ===
        # item: 현재 반복 중인 아이템
        if self.item is not None:
            result["item"] = self.item
        # index: 현재 반복 인덱스
        result["index"] = self.index
        # total: 전체 아이템 개수
        result["total"] = self.total

        # 레거시 호환성
        if self.current_symbol:
            result["current_symbol"] = self.current_symbol
        result["current_index"] = self.current_index

        # 추가 변수
        result.update(self.variables)

        return result

    def set_iteration_context(self, item: Any, index: int, total: int) -> None:
        """반복 컨텍스트 설정 (자동 반복 실행 시 Executor가 호출)"""
        self.item = item
        self.index = index
        self.total = total

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
        # 함수 네임스페이스
        # ═══════════════════════════════════════════════════════════════
        "date": DateNamespace(),
        "finance": FinanceNamespace(),
        "stats": StatsNamespace(),
        "format": FormatNamespace(),
        # "list"는 기본 타입 변환 함수로 이미 사용 중이므로 "lst" 사용
        "lst": ListNamespace(),

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
        NodeOutputProxy는 자동으로 unwrap하여 실제 데이터 반환
        """
        if not self.is_expression(value):
            return value

        # 전체가 단일 표현식인 경우: "{{ expr }}"
        full_match = re.fullmatch(r'\{\{\s*(.+?)\s*\}\}', value.strip())
        if full_match:
            expr = full_match.group(1)
            result = self._eval_expression(expr)
            # NodeOutputProxy는 자동으로 unwrap
            if isinstance(result, NodeOutputProxy):
                return result._get_array()
            return result

        # 문자열 내 여러 표현식: "Price: {{ price }}, Qty: {{ qty }}"
        def replace_expr(match: re.Match) -> str:
            expr = match.group(1)
            result = self._eval_expression(expr)
            # NodeOutputProxy는 자동으로 unwrap
            if isinstance(result, NodeOutputProxy):
                result = result._get_array()
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
