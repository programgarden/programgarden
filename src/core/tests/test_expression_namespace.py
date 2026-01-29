"""
표현식 네임스페이스 테스트

테스트 대상:
- DateNamespace: 날짜/시간 함수
- FinanceNamespace: 금융 계산 함수
- StatsNamespace: 통계 함수
- FormatNamespace: 포맷팅 함수
- ListNamespace: 리스트 유틸리티
"""

import pytest
from datetime import date, timedelta

from programgarden_core.expression.evaluator import (
    ExpressionContext,
    ExpressionEvaluator,
    DateNamespace,
    FinanceNamespace,
    StatsNamespace,
    FormatNamespace,
    ListNamespace,
)


class TestDateNamespace:
    """날짜 네임스페이스 테스트"""

    def test_today_default_format(self):
        """date.today() - 기본 ISO 형식"""
        ns = DateNamespace()
        result = ns.today()
        assert result == date.today().isoformat()

    def test_today_yyyymmdd_format(self):
        """date.today(format='yyyymmdd')"""
        ns = DateNamespace()
        result = ns.today(format='yyyymmdd')
        assert result == date.today().strftime('%Y%m%d')

    def test_today_custom_format(self):
        """date.today(format='%Y/%m/%d')"""
        ns = DateNamespace()
        result = ns.today(format='%Y/%m/%d')
        assert result == date.today().strftime('%Y/%m/%d')

    def test_ago_default_format(self):
        """date.ago(30) - 30일 전"""
        ns = DateNamespace()
        result = ns.ago(30)
        expected = (date.today() - timedelta(days=30)).isoformat()
        assert result == expected

    def test_ago_yyyymmdd_format(self):
        """date.ago(30, format='yyyymmdd')"""
        ns = DateNamespace()
        result = ns.ago(30, format='yyyymmdd')
        expected = (date.today() - timedelta(days=30)).strftime('%Y%m%d')
        assert result == expected

    def test_later_default_format(self):
        """date.later(7) - 7일 후"""
        ns = DateNamespace()
        result = ns.later(7)
        expected = (date.today() + timedelta(days=7)).isoformat()
        assert result == expected

    def test_months_ago(self):
        """date.months_ago(3) - 3개월 전"""
        ns = DateNamespace()
        result = ns.months_ago(3)
        expected = (date.today() - timedelta(days=90)).isoformat()
        assert result == expected

    def test_year_start(self):
        """date.year_start() - 연초"""
        ns = DateNamespace()
        result = ns.year_start()
        expected = date(date.today().year, 1, 1).isoformat()
        assert result == expected

    def test_year_end(self):
        """date.year_end() - 연말"""
        ns = DateNamespace()
        result = ns.year_end()
        expected = date(date.today().year, 12, 31).isoformat()
        assert result == expected

    def test_month_start(self):
        """date.month_start() - 월초"""
        ns = DateNamespace()
        result = ns.month_start()
        expected = date.today().replace(day=1).isoformat()
        assert result == expected

    def test_now(self):
        """date.now() - 현재 시간"""
        ns = DateNamespace()
        result = ns.now()
        # ISO 형식 (초 단위까지)
        assert len(result) == 19
        assert 'T' in result


class TestFinanceNamespace:
    """금융 네임스페이스 테스트"""

    def test_pct_change(self):
        """finance.pct_change(100, 110) = 10%"""
        ns = FinanceNamespace()
        result = ns.pct_change(100, 110)
        assert result == 10.0

    def test_pct_change_negative(self):
        """finance.pct_change(100, 90) = -10%"""
        ns = FinanceNamespace()
        result = ns.pct_change(100, 90)
        assert result == -10.0

    def test_pct_change_zero_old(self):
        """finance.pct_change(0, 100) = 0 (division by zero 방지)"""
        ns = FinanceNamespace()
        result = ns.pct_change(0, 100)
        assert result == 0.0

    def test_pct(self):
        """finance.pct(25, 100) = 25%"""
        ns = FinanceNamespace()
        result = ns.pct(25, 100)
        assert result == 25.0

    def test_discount(self):
        """finance.discount(1000, 20) = 800"""
        ns = FinanceNamespace()
        result = ns.discount(1000, 20)
        assert result == 800.0

    def test_markup(self):
        """finance.markup(1000, 20) = 1200"""
        ns = FinanceNamespace()
        result = ns.markup(1000, 20)
        assert result == 1200.0

    def test_compound(self):
        """finance.compound(1000, 10, 3) = 1000 * 1.1^3"""
        ns = FinanceNamespace()
        result = ns.compound(1000, 10, 3)
        assert abs(result - 1331.0) < 0.01


class TestStatsNamespace:
    """통계 네임스페이스 테스트"""

    def test_mean(self):
        """stats.mean([1, 2, 3, 4, 5]) = 3.0"""
        ns = StatsNamespace()
        result = ns.mean([1, 2, 3, 4, 5])
        assert result == 3.0

    def test_mean_empty(self):
        """stats.mean([]) = 0.0"""
        ns = StatsNamespace()
        result = ns.mean([])
        assert result == 0.0

    def test_avg_alias(self):
        """stats.avg는 stats.mean의 별칭"""
        ns = StatsNamespace()
        result = ns.avg([1, 2, 3, 4, 5])
        assert result == 3.0

    def test_median(self):
        """stats.median([1, 2, 3, 4, 5]) = 3"""
        ns = StatsNamespace()
        result = ns.median([1, 2, 3, 4, 5])
        assert result == 3

    def test_stdev(self):
        """stats.stdev([1, 2, 3, 4, 5]) > 0"""
        ns = StatsNamespace()
        result = ns.stdev([1, 2, 3, 4, 5])
        assert result > 0

    def test_stdev_single_value(self):
        """stats.stdev([1]) = 0 (단일 값)"""
        ns = StatsNamespace()
        result = ns.stdev([1])
        assert result == 0.0

    def test_variance(self):
        """stats.variance([1, 2, 3, 4, 5]) > 0"""
        ns = StatsNamespace()
        result = ns.variance([1, 2, 3, 4, 5])
        assert result > 0


class TestFormatNamespace:
    """포맷팅 네임스페이스 테스트"""

    def test_pct(self):
        """format.pct(12.34) = '12.34%'"""
        ns = FormatNamespace()
        result = ns.pct(12.34)
        assert result == "12.34%"

    def test_pct_custom_decimals(self):
        """format.pct(12.345, decimals=1) = '12.3%'"""
        ns = FormatNamespace()
        result = ns.pct(12.345, decimals=1)
        assert result == "12.3%"

    def test_currency_default(self):
        """format.currency(1234.56) = '$1,234.56'"""
        ns = FormatNamespace()
        result = ns.currency(1234.56)
        assert result == "$1,234.56"

    def test_currency_custom_symbol(self):
        """format.currency(1234.56, symbol='₩') = '₩1,234.56'"""
        ns = FormatNamespace()
        result = ns.currency(1234.56, symbol='₩')
        assert result == "₩1,234.56"

    def test_number(self):
        """format.number(1234567.89) = '1,234,567.89'"""
        ns = FormatNamespace()
        result = ns.number(1234567.89)
        assert result == "1,234,567.89"

    def test_number_custom_decimals(self):
        """format.number(1234567.89, decimals=0) = '1,234,568'"""
        ns = FormatNamespace()
        result = ns.number(1234567.89, decimals=0)
        assert result == "1,234,568"


class TestListNamespace:
    """리스트 네임스페이스 테스트"""

    def test_first(self):
        """lst.first([1, 2, 3]) = 1"""
        ns = ListNamespace()
        result = ns.first([1, 2, 3])
        assert result == 1

    def test_first_empty(self):
        """lst.first([]) = None"""
        ns = ListNamespace()
        result = ns.first([])
        assert result is None

    def test_last(self):
        """lst.last([1, 2, 3]) = 3"""
        ns = ListNamespace()
        result = ns.last([1, 2, 3])
        assert result == 3

    def test_last_empty(self):
        """lst.last([]) = None"""
        ns = ListNamespace()
        result = ns.last([])
        assert result is None

    def test_count(self):
        """lst.count([1, 2, 3]) = 3"""
        ns = ListNamespace()
        result = ns.count([1, 2, 3])
        assert result == 3

    def test_pluck(self):
        """lst.pluck(items, 'name')"""
        ns = ListNamespace()
        items = [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}]
        result = ns.pluck(items, 'name')
        assert result == ['A', 'B', 'C']

    def test_pluck_nested(self):
        """lst.pluck(items, 'a.b')"""
        ns = ListNamespace()
        items = [{'a': {'b': 1}}, {'a': {'b': 2}}]
        result = ns.pluck(items, 'a.b')
        assert result == [1, 2]

    def test_flatten(self):
        """lst.flatten(items, 'children')"""
        ns = ListNamespace()
        items = [
            {'id': 1, 'children': [{'name': 'A'}, {'name': 'B'}]},
            {'id': 2, 'children': [{'name': 'C'}]},
        ]
        result = ns.flatten(items, 'children')
        assert len(result) == 3
        assert result[0] == {'id': 1, 'name': 'A'}
        assert result[1] == {'id': 1, 'name': 'B'}
        assert result[2] == {'id': 2, 'name': 'C'}


class TestNamespaceInExpression:
    """표현식에서 네임스페이스 사용 테스트"""

    def test_date_namespace_in_expression(self):
        """{{ date.today() }} 표현식"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate("{{ date.today() }}")
        assert result == date.today().isoformat()

    def test_date_ago_with_format(self):
        """{{ date.ago(30, format='yyyymmdd') }} 표현식"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate("{{ date.ago(30, format='yyyymmdd') }}")
        expected = (date.today() - timedelta(days=30)).strftime('%Y%m%d')
        assert result == expected

    def test_finance_namespace_in_expression(self):
        """{{ finance.pct_change(100, 110) }} 표현식"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate("{{ finance.pct_change(100, 110) }}")
        assert result == 10.0

    def test_stats_namespace_in_expression(self):
        """{{ stats.mean([1, 2, 3, 4, 5]) }} 표현식"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate("{{ stats.mean([1, 2, 3, 4, 5]) }}")
        assert result == 3.0

    def test_format_namespace_in_expression(self):
        """{{ format.pct(12.34) }} 표현식"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate("{{ format.pct(12.34) }}")
        assert result == "12.34%"

    def test_lst_namespace_in_expression(self):
        """{{ lst.first([1, 2, 3]) }} 표현식"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate("{{ lst.first([1, 2, 3]) }}")
        assert result == 1

    def test_combined_namespaces(self):
        """여러 네임스페이스 조합"""
        ctx = ExpressionContext()
        ctx.set_node_output("account", "positions", [
            {"symbol": "AAPL", "pnl": 100},
            {"symbol": "TSLA", "pnl": 200},
            {"symbol": "MSFT", "pnl": 300},
        ])
        evaluator = ExpressionEvaluator(ctx)

        # lst.pluck + stats.mean
        result = evaluator.evaluate(
            "{{ stats.mean(lst.pluck(nodes.account.positions, 'pnl')) }}"
        )
        assert result == 200.0

    def test_format_with_finance(self):
        """format + finance 조합"""
        ctx = ExpressionContext()
        evaluator = ExpressionEvaluator(ctx)
        result = evaluator.evaluate(
            "{{ format.pct(finance.pct_change(100, 125)) }}"
        )
        assert result == "25.00%"
