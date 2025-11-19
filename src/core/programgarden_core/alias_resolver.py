"""Utilities for normalizing Korean aliases in system configuration.

EN:
    This module allows user-provided configuration dictionaries to use
    commonly requested Korean key names. The keys are converted to the
    canonical English identifiers that the runtime expects.

KO:
    이 모듈은 사용자 구성 사전에서 자주 사용되는 한글 키 이름을
    표준 영문 식별자로 변환합니다. 런타임이 기대하는 키로 자동 변환하여
    개발자가 자유롭게 한글 별칭을 사용할 수 있도록 지원합니다.

Example:
    >>> system = {"설정": {"시스템ID": "전략-1"}}
    >>> normalize_system_config(system)["settings"]["system_id"]
    '전략-1'
"""

from __future__ import annotations

from typing import Any, Dict

# EN: Alias mappings for top-level keys under the system dictionary.
# KO: 시스템 구성의 최상위 키에 대한 한글 별칭과 표준 영문 키의 매핑입니다.
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

# EN: Alias mappings for system settings keys provided by users.
# KO: 사용자가 입력하는 시스템 설정 키에 대한 한글 별칭과 표준 영문 키의 매핑입니다.
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

# EN: Alias mappings that normalize brokerage and product related keys.
# KO: 증권사 및 상품 관련 키를 표준화하기 위한 한글 별칭 매핑입니다.
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

# EN: Alias mappings used when normalizing strategy configuration blocks.
# KO: 전략 구성 블록을 표준화할 때 사용하는 한글 별칭 매핑입니다.
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
    "주문": "order_id",
    "종목": "symbols",
    "심볼": "symbols",
    "최대종목": "max_symbols",
    "조건": "conditions",
    "조건들": "conditions",
    "매수매도": "buy_or_sell",
    "시작즉시실행": "run_once_on_start",
}

# EN: Alias mappings for individual symbol configuration entries.
# KO: 개별 종목 구성 항목에 대한 한글 별칭과 표준 키 매핑입니다.
SYMBOL_ALIAS_MAP: Dict[str, str] = {
    "심볼": "symbol",
    "종목": "symbol",
    "거래소코드": "exchcd",
    "거래소": "exchcd",
}

# EN: Alias mappings for maximum symbol constraint settings.
# KO: 최대 종목 제한 설정을 위한 한글 별칭과 표준 키 매핑입니다.
MAX_SYMBOLS_ALIAS_MAP: Dict[str, str] = {
    "정렬": "order",
    "정렬기준": "order",
    "제한": "limit",
    "최대": "limit",
}

# EN: Alias mappings for strategy condition definitions.
# KO: 전략 조건 정의에 사용되는 한글 별칭과 표준 키 매핑입니다.
CONDITION_ALIAS_MAP: Dict[str, str] = {
    "조건ID": "condition_id",
    "필요한데이터": "params",
}

# EN: Alias mappings that describe the structure of order definitions.
# KO: 주문 정의 구조를 설명하는 한글 별칭과 표준 키 매핑입니다.
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

# EN: Alias mappings for order timing window configuration.
# KO: 주문 시간 창 설정을 위한 한글 별칭과 표준 키 매핑입니다.
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

# EN: Alias mappings for conditions embedded within order definitions.
# KO: 주문 정의에 포함된 조건 블록을 위한 한글 별칭과 표준 키 매핑입니다.
ORDER_CONDITION_ALIAS_MAP: Dict[str, str] = {
    "조건ID": "condition_id",
    "필요한데이터": "params",
}


def _apply_aliases(target: Dict[str, Any], alias_map: Dict[str, str]) -> None:
    """Perform in-place alias normalization for mapping keys.

    EN:
        Update ``target`` so that any keys present in ``alias_map`` are replaced
        by their canonical equivalents while preserving existing canonical keys.

    KO:
        ``alias_map`` 에 정의된 한글 별칭 키를 표준 키로 교체하여 ``target``
        사전을 제자리에서 업데이트합니다. 이미 표준 키가 존재할 때는 값을
        덮어쓰지 않고 별칭 키만 제거합니다.

    Parameters:
        target (Dict[str, Any]): The dictionary to mutate by applying alias rules.
        alias_map (Dict[str, str]): Alias-to-canonical mapping definitions.

    Returns:
        None: The function mutates ``target`` directly and returns ``None``.

    Raises:
        None: Non-dictionary inputs are ignored without raising.
    """
    if not isinstance(target, dict):
        return

    for alias, canonical in list(alias_map.items()):
        if alias in target:
            # Avoid overwriting canonical keys the user already provided.
            if canonical not in target:
                target[canonical] = target.pop(alias)
            else:
                target.pop(alias)


def _safe_copy(value: Any, memo: Dict[int, Any] | None = None) -> Any:
    """Recursively copy mappings/sequences while leaving other objects intact."""
    if memo is None:
        memo = {}

    obj_id = id(value)
    if obj_id in memo:
        return memo[obj_id]

    if isinstance(value, dict):
        cloned: Dict[Any, Any] = {}
        memo[obj_id] = cloned
        for key, item in value.items():
            cloned[key] = _safe_copy(item, memo)
        return cloned

    if isinstance(value, list):
        cloned_list: list[Any] = []
        memo[obj_id] = cloned_list
        cloned_list.extend(_safe_copy(item, memo) for item in value)
        return cloned_list

    if isinstance(value, tuple):
        return tuple(_safe_copy(item, memo) for item in value)

    if isinstance(value, set):
        cloned_set: set[Any] = set()
        memo[obj_id] = cloned_set
        for item in value:
            cloned_set.add(_safe_copy(item, memo))
        return cloned_set

    return value


def normalize_system_config(system: Any) -> Any:
    """Deep-copy and normalize configuration dictionaries using alias maps.

    EN:
        Produce a sanitized configuration object where Korean aliases are
        converted to canonical English keys. A deep copy is created so the
        original input remains untouched.

    KO:
        한글 별칭을 표준 영문 키로 변환한 구성 사전을 반환합니다. 원본 입력이
        변경되지 않도록 깊은 복사본을 생성하여 안전하게 재사용할 수 있습니다.

    Parameters:
        system (Any): The user-supplied configuration object to normalize.

    Returns:
        Any: A normalized deep-copied configuration if ``system`` is a dict;
        otherwise the original value is returned unchanged.

    Raises:
        None: All operations handle unexpected types gracefully.
    """

    if not isinstance(system, dict):
        return system

    normalized = _safe_copy(system)

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
