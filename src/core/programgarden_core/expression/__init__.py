"""
ProgramGarden Core - Expression Package

Jinja2 스타일 표현식 평가 엔진

네임스페이스 함수:
- date: 날짜/시간 함수 (today, ago, later, months_ago, ...)
- finance: 금융 계산 (pct_change, discount, markup, annualize, compound)
- stats: 통계 함수 (mean, median, stdev, variance)
- format: 포맷팅 (pct, currency, number)
- lst: 리스트 유틸 (first, last, count, pluck, flatten)
"""

from programgarden_core.expression.evaluator import (
    ExpressionEvaluator,
    ExpressionContext,
    ExpressionError,
    DateNamespace,
    FinanceNamespace,
    StatsNamespace,
    FormatNamespace,
    ListNamespace,
)

__all__ = [
    "ExpressionEvaluator",
    "ExpressionContext",
    "ExpressionError",
    "DateNamespace",
    "FinanceNamespace",
    "StatsNamespace",
    "FormatNamespace",
    "ListNamespace",
]
