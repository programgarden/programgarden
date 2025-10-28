"""Utilities for normalizing Korean aliases in system configuration.

This module allows user-provided configuration dictionaries to use
commonly requested Korean key names. The keys are converted to the
canonical English identifiers that the runtime expects.

Example:
    >>> system = {"설정": {"시스템ID": "전략-1"}}
    >>> normalize_system_config(system)["settings"]["system_id"]
    '전략-1'
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

# Top-level aliases under the system dictionary.
TOP_LEVEL_ALIAS_MAP: Dict[str, str] = {
    "설정": "settings",
    "세팅": "settings",
    "시스템설정": "settings",
    "증권": "securities",
    "거래": "securities",
    "전략": "strategies",
    "전략들": "strategies",
    "주문": "orders",
    "주문들": "orders",
}

SETTINGS_ALIAS_MAP: Dict[str, str] = {
    "시스템ID": "system_id",
    "이름": "name",
    "전략이름": "name",
    "설명": "description",
    "버전": "version",
    "작성자": "author",
    "작성일": "date",
    "날짜": "date",
    "디버그": "debug",
    "로그": "debug",
}

SECURITIES_ALIAS_MAP: Dict[str, str] = {
    "회사": "company",
    "증권사": "company",
    "상품": "product",
    "앱키": "appkey",
    "API키": "appkey",
    "앱시크릿": "appsecretkey",
    "앱시크릿키": "appsecretkey",
    "비밀키": "appsecretkey",
    "모의투자": "paper_trading",
}

STRATEGY_ALIAS_MAP: Dict[str, str] = {
    "전략ID": "id",
    "설명": "description",
    "스케줄": "schedule",
    "일정": "schedule",
    "시간대": "timezone",
    "로직": "logic",
    "판단방식": "logic",
    "임계값": "threshold",
    "사용하는주문ID": "order_id",
    "주문ID": "order_id",
    "주문ID": "order_id",
    "주문": "order_id",
    "종목": "symbols",
    "심볼": "symbols",
    "최대종목": "max_symbols",
    "조건": "conditions",
    "조건들": "conditions",
    "매수매도": "buy_or_sell",
    "시작즉시실행": "run_once_on_start",
}

SYMBOL_ALIAS_MAP: Dict[str, str] = {
    "심볼": "symbol",
    "종목": "symbol",
    "거래소코드": "exchcd",
    "거래소": "exchcd",
}

MAX_SYMBOLS_ALIAS_MAP: Dict[str, str] = {
    "정렬": "order",
    "정렬기준": "order",
    "제한": "limit",
    "최대": "limit",
}

CONDITION_ALIAS_MAP: Dict[str, str] = {
    "조건ID": "condition_id",
    "필요한데이터": "params",
}

ORDER_ALIAS_MAP: Dict[str, str] = {
    "주문ID": "order_id",
    "설명": "description",
    "중복매수차단": "block_duplicate_buy",
    "중복매수방지": "block_duplicate_buy",
    "주문시간": "order_time",
    "시간": "order_time",
    "조건": "condition",
    "조건들": "condition",
    "종류": "order_types",
    "주문종류": "order_types",
}

ORDER_TIME_ALIAS_MAP: Dict[str, str] = {
    "시작": "start",
    "시작시간": "start",
    "종료": "end",
    "종료시간": "end",
    "요일": "days",
    "시간대": "timezone",
    "시간기다림": "behavior",
    "처리": "behavior",
    "최대지연": "max_delay_seconds",
    "최대지연초": "max_delay_seconds",
}

ORDER_CONDITION_ALIAS_MAP: Dict[str, str] = {
    "조건ID": "condition_id",
    "필요한데이터": "params",
}


def _apply_aliases(target: Dict[str, Any], alias_map: Dict[str, str]) -> None:
    """In-place conversion of alias keys to their canonical names."""
    if not isinstance(target, dict):
        return

    for alias, canonical in list(alias_map.items()):
        if alias in target:
            # Avoid overwriting canonical keys the user already provided.
            if canonical not in target:
                target[canonical] = target.pop(alias)
            else:
                target.pop(alias)


def normalize_system_config(system: Any) -> Any:
    """Return a configuration with Korean aliases normalized.

    The function performs a deep copy so that callers can safely reuse
    the original dictionary without side effects.
    """

    if not isinstance(system, dict):
        return system

    normalized = deepcopy(system)

    _apply_aliases(normalized, TOP_LEVEL_ALIAS_MAP)

    settings = normalized.get("settings")
    if isinstance(settings, dict):
        _apply_aliases(settings, SETTINGS_ALIAS_MAP)

    securities = normalized.get("securities")
    if isinstance(securities, dict):
        _apply_aliases(securities, SECURITIES_ALIAS_MAP)

    strategies = normalized.get("strategies")
    if isinstance(strategies, list):
        for strategy in strategies:
            if not isinstance(strategy, dict):
                continue
            _apply_aliases(strategy, STRATEGY_ALIAS_MAP)

            symbols = strategy.get("symbols")
            if isinstance(symbols, list):
                for symbol in symbols:
                    if isinstance(symbol, dict):
                        _apply_aliases(symbol, SYMBOL_ALIAS_MAP)

            max_symbols = strategy.get("max_symbols")
            if isinstance(max_symbols, dict):
                _apply_aliases(max_symbols, MAX_SYMBOLS_ALIAS_MAP)

            conditions = strategy.get("conditions")
            if isinstance(conditions, list):
                for condition in conditions:
                    if isinstance(condition, dict):
                        _apply_aliases(condition, CONDITION_ALIAS_MAP)

    orders = normalized.get("orders")
    if isinstance(orders, list):
        for order in orders:
            if not isinstance(order, dict):
                continue
            _apply_aliases(order, ORDER_ALIAS_MAP)

            order_time = order.get("order_time")
            if isinstance(order_time, dict):
                _apply_aliases(order_time, ORDER_TIME_ALIAS_MAP)

            condition = order.get("condition")
            if isinstance(condition, dict):
                _apply_aliases(condition, ORDER_CONDITION_ALIAS_MAP)

    return normalized
