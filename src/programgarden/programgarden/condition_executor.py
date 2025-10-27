"""
High-level utilities for executing and evaluating strategy conditions.

This module provides the :class:`ConditionExecutor` which is responsible for
running individual conditions (plugins or BaseStrategyCondition instances), evaluating
nested condition groups using logical operators, and filtering symbol lists
based on a strategy's condition definitions.

Key responsibilities:
- Resolve and execute plugin-based conditions via :class:`PluginResolver`.
- Execute nested condition trees concurrently and evaluate their combined
    result using a small DSL of logical operators (and/or/xor/not/at_least/...).
- Provide a convenient API to evaluate a strategy's condition list over a set
    of symbols and return the symbols that passed.

The public surface is intentionally small: construct a :class:`ConditionExecutor`
and use :meth:`execute_condition` and :meth:`execute_condition_list`.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import asyncio

from programgarden_core import (
    BaseStrategyCondition,
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,
    StrategyConditionType,
    StrategyType,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    SystemType,
    pg_logger,
    OrderStrategyType,
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,
)
from programgarden_core.exceptions import ConditionExecutionException

from programgarden.pg_listener import pg_listener

from .plugin_resolver import PluginResolver
from .symbols_provider import SymbolProvider


class ConditionExecutor:
    """Execute and combine strategy conditions.

    The ConditionExecutor coordinates execution of single condition items and
    nested condition groups. It is purposely lightweight and relies on
    :class:`PluginResolver` to instantiate plugin condition classes and on
    :class:`SymbolProvider` to retrieve symbol lists when a strategy does not
    provide them directly.

    Attributes
    ----------
    resolver:
        A :class:`PluginResolver` instance used to map a string condition
        identifier to a concrete condition class (usually a subclass of
        :class:`programgarden_core.BaseStrategyCondition`). The resolver.resolve
        method is awaited and expected to return a callable/class.

    symbol_provider:
        A :class:`SymbolProvider` responsible for returning market symbols when
        the strategy does not include an explicit `symbols` list.

    state_lock:
        An :class:`asyncio.Lock` reserved for future stateful operations. It is
        created here to allow safe extension later; current implementation
        methods do not require locking.

    Thread-safety / concurrency
    ---------------------------
    Methods on this class are implemented as coroutines and can be called
    concurrently. Internally they use :mod:`asyncio.gather` to run child
    condition checks in parallel. If future stateful updates are added, use
    ``state_lock`` to protect shared state.
    """

    def __init__(self, resolver: PluginResolver, symbol_provider: SymbolProvider):
        self.resolver = resolver
        self.symbol_provider = symbol_provider
        self.state_lock = asyncio.Lock()

    def _symbol_label(self, symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]) -> str:
        if isinstance(symbol_info, dict):
            exch = symbol_info.get("exchcd") or symbol_info.get("ExchCode") or "?"
            symbol = symbol_info.get("symbol") or symbol_info.get("IsuCodeVal") or symbol_info.get("ShtnIsuNo") or "?"
            return f"{exch}:{symbol}"
        return str(symbol_info)

    def _describe_condition(self, condition: StrategyConditionType) -> str:
        if isinstance(condition, dict):
            return condition.get("condition_id") or condition.get("logic", "group")
        return getattr(condition, "id", condition.__class__.__name__)

    def evaluate_logic(
        self,
        results: List[
            Union[
                BaseStrategyConditionResponseOverseasStockType,
                BaseStrategyConditionResponseOverseasFuturesType,
            ]
        ],
        logic: str,
        threshold: Optional[int] = None,
    ) -> Tuple[bool, int]:
        """Evaluate a list of condition results using a logical operator.

        Returns a tuple: (bool_result, numeric_weight).
        """
        if logic in ("and", "all"):
            return (all(result.get("success", False) for result in results), 0)
        if logic in ("or", "any"):
            return (any(result.get("success", False) for result in results), 0)
        if logic == "not":
            return (not any(result.get("success", False) for result in results), 0)
        if logic == "xor":
            return (sum(bool(result.get("success", False)) for result in results) == 1, 0)
        if logic == "at_least":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'at_least' logic.")
            return (sum(bool(result.get("success", False)) for result in results) >= threshold, 0)
        if logic == "at_most":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'at_most' logic.")
            return (sum(bool(result.get("success", False)) for result in results) <= threshold, 0)
        if logic == "exactly":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'exactly' logic.")
            return (sum(bool(result.get("success", False)) for result in results) == threshold, 0)
        if logic == "weighted":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'weighted' logic.")
            total_weight = sum(result.get("weight", 0) for result in results if result.get("success", False))
            return (total_weight >= threshold, total_weight)
        return (False, 0)

    def _build_response(
        self,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
        *,
        success: bool,
        condition_id: Optional[str] = None,
        weight: int = 0,
        data: Optional[Any] = None,
        position_side: Optional[str] = None,
    ) -> Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
        product_type = symbol_info.get("product_type") if isinstance(symbol_info, dict) else None
        if product_type == "overseas_futures":
            futures_response: BaseStrategyConditionResponseOverseasFuturesType = {
                "condition_id": condition_id,
                "success": success,
                "symbol": symbol_info.get("symbol", ""),
                "exchcd": symbol_info.get("exchcd", ""),
                "data": data if data is not None else {},
                "weight": weight,
                "product": "overseas_futures",
                "position_side": position_side if position_side in {"long", "short", "flat"} else "flat",
            }
            return futures_response

        stock_response: BaseStrategyConditionResponseOverseasStockType = {
            "condition_id": condition_id,
            "success": success,
            "symbol": symbol_info.get("symbol", ""),
            "exchcd": symbol_info.get("exchcd", ""),
            "data": data if data is not None else {},
            "weight": weight,
            "product": "overseas_stock",
        }
        return stock_response

    async def execute_condition(
        self,
        system: SystemType,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
        condition: Union[
            BaseStrategyConditionOverseasStock,
            BaseStrategyConditionOverseasFutures,
            StrategyConditionType,
        ],
    ) -> Union[
        BaseStrategyConditionResponseOverseasStockType,
        BaseStrategyConditionResponseOverseasFuturesType,
    ]:
        """Execute a single condition entry.

        A condition entry can be either:
        - An instance of :class:`programgarden_core.BaseStrategyCondition`, in which
          case its ``execute`` coroutine is awaited and its result returned.
        - A dictionary describing a plugin condition, e.g. ``{"condition_id": "MyCond", "params": {...}}``.
        - A nested condition group (dict containing a ``"conditions"`` list and
          optional ``"logic"``/``"threshold"`` keys).
        """
        if isinstance(condition, BaseStrategyCondition):
            system_id = system.get("settings", {}).get("system_id", None)

            if hasattr(condition, "_set_symbol"):
                condition._set_symbol(symbol_info)
            if hasattr(condition, "_set_system_id") and system_id:
                condition._set_system_id(system_id)

            result = await condition.execute()

            return result

        if isinstance(condition, dict):
            if "condition_id" in condition and "conditions" not in condition:
                pg_logger.debug(
                    f"[CONDITION] {condition.get('condition_id')}: {self._symbol_label(symbol_info)}에 대한 플러그인 조건을 평가합니다"
                )
                return await self._execute_plugin_condition(
                    system_id=system.get("settings", {}).get("system_id", None),
                    condition=condition,
                    symbol_info=symbol_info,
                )
            # Nested condition group
            if "conditions" in condition:
                pg_logger.debug(
                    f"[CONDITION] group: {self._symbol_label(symbol_info)}에 대해 로직 '{condition.get('logic', 'and')}'을 평가합니다"
                )
                return await self._execute_nested_condition(system, symbol_info, condition)
            # Unknown dict shape: treat as failure but keep symbol context.
            return self._build_response(symbol_info, success=False)

        pg_logger.warning(
            f"[CONDITION] 지원되지 않는 조건 타입입니다: {type(condition)}"
        )
        return self._build_response(symbol_info, success=False)

    async def _execute_plugin_condition(
        self,
        system_id: Optional[str],
        condition: Dict,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
    ) -> Union[
        BaseStrategyConditionResponseOverseasStockType,
        BaseStrategyConditionResponseOverseasFuturesType,
    ]:
        """
        Execute a single plugin condition identified by ``condition_id``.
        """
        condition_id = condition.get("condition_id")
        params = condition.get("params", {}) or {}

        result = await self.resolver.resolve_condition(
            system_id=system_id,
            condition_id=condition_id,
            params=params,
            symbol_info=symbol_info,
        )

        pg_logger.debug(
            f"[CONDITION] {condition_id}: {self._symbol_label(symbol_info)} 결과 -> 성공={result.get('success')} 가중치={result.get('weight', 0)}"
        )

        return result

    async def _execute_nested_condition(
        self,
        system: SystemType,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
        condition_nested: StrategyConditionType,
    ) -> Union[
        BaseStrategyConditionResponseOverseasStockType,
        BaseStrategyConditionResponseOverseasFuturesType,
    ]:
        """
        Execute a nested condition group using concurrent execution and
        """
        conditions = condition_nested.get("conditions", [])
        logic = condition_nested.get("logic", "and")
        threshold = condition_nested.get("threshold", None)

        tasks: List[asyncio.Task] = []
        task_metadata: Dict[asyncio.Task, Dict[str, Any]] = {}
        for index, condition in enumerate(conditions):
            task = asyncio.create_task(
                self.execute_condition(system=system, symbol_info=symbol_info, condition=condition)
            )
            tasks.append(task)
            task_metadata[task] = {"condition": condition, "index": index}

        condition_results: List[
            Union[
                BaseStrategyConditionResponseOverseasStockType,
                BaseStrategyConditionResponseOverseasFuturesType,
            ]
        ] = []
        failure_count = 0
        for task in asyncio.as_completed(tasks):
            try:
                res = await task
                condition_results.append(res)

            except Exception as e:
                failure_count += 1
                pg_logger.error(f"[CONDITION] 그룹 조건 실행 중 오류가 발생했습니다: {e}")
                meta = task_metadata.get(task, {})
                condition_obj = meta.get("condition") if meta else None
                condition_label = self._describe_condition(condition_obj) if condition_obj is not None else None
                cond_exc = ConditionExecutionException(
                    message="그룹 조건 실행 중 오류가 발생했습니다.",
                    data={
                        "symbol": self._symbol_label(symbol_info),
                        "logic": logic,
                        "condition": condition_label,
                        "condition_index": meta.get("index") if meta else None,
                    },
                )
                pg_listener.emit_exception(cond_exc)
                condition_results.append(
                    self._build_response(symbol_info, success=False, condition_id=None)
                )

        complete, total_weight = self.evaluate_logic(results=condition_results, logic=logic, threshold=threshold)
        if failure_count:
            pg_logger.warning(
                f"[CONDITION] 그룹: {self._symbol_label(symbol_info)} 대상 조건 {failure_count}개가 실패했습니다"
            )
        if not complete:
            return self._build_response(
                symbol_info,
                success=False,
                weight=total_weight,
            )

        # All conditions passed
        return self._build_response(
            symbol_info,
            success=True,
            weight=total_weight,
        )

    async def execute_condition_list(
        self,
        system: SystemType,
        strategy: StrategyType,
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """
        Perform calculations defined in the strategy
        """

        my_symbols = strategy.get("symbols", [])
        securities = system.get("securities", {})
        order_id = strategy.get("order_id", None)
        orders = system.get("orders", {})
        conditions = strategy.get("conditions", [])

        order_types = []
        if order_id is not None:
            order_types = await self._get_order_types(order_id, orders)
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 주문 ID '{order_id}'의 주문 유형 -> {order_types}"
            )

        market_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        account_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        non_account_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []

        if not my_symbols and ("new_buy" in order_types or order_types is None):
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 신규 매수를 위한 시장 종목을 조회합니다"
            )
            market_symbols = await self.symbol_provider.get_symbols(
                order_type="new_buy",
                securities=securities,
            )

        if "new_sell" in order_types:
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 신규 매도를 위한 계좌 종목을 조회합니다"
            )
            account_symbols = await self.symbol_provider.get_symbols(
                order_type="new_sell",
                securities=securities,
            )

        if "modify_buy" in order_types:
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 정정 매수를 위한 종목을 조회합니다"
            )
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="modify_buy",
                securities=securities,
            )
        elif "modify_sell" in order_types:
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 정정 매도를 위한 종목을 조회합니다"
            )
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="modify_sell",
                securities=securities,
            )
        elif "cancel_buy" in order_types:
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 취소 매수를 위한 종목을 조회합니다"
            )
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="cancel_buy",
                securities=securities,
            )
        elif "cancel_sell" in order_types:
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 취소 매도를 위한 종목을 조회합니다"
            )
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="cancel_sell",
                securities=securities,
            )

        # Merge market_symbols and account_symbols into symbols without duplicate ids
        seen_ids = set()
        for symbol in my_symbols:
            exch = symbol.get("exchcd", "")
            sym = symbol.get("symbol", "")
            seen_ids.add(f"{exch}:{sym}:")

        for src in (market_symbols, account_symbols, non_account_symbols):
            for symbol in src:
                exch = symbol.get("exchcd", "")
                sym = symbol.get("symbol", "")
                ord_no = symbol.get("OrdNo", "")
                ident = f"{exch}:{sym}:{ord_no}"
                if ident not in seen_ids:
                    my_symbols.append(symbol)
                    seen_ids.add(ident)

        max_symbols = strategy.get("max_symbols", {})
        max_order = max_symbols.get("order", "random")
        max_count = max_symbols.get("limit", 0)

        # Sort symbols based on the specified order
        if max_order == "random":
            import random
            random.shuffle(my_symbols)
        elif max_order == "mcap":
            my_symbols.sort(key=lambda x: x.get("mcap", 0), reverse=True)

        if max_count > 0:
            my_symbols = my_symbols[:max_count]
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: '{max_order}' 기준으로 최대 {max_count}개 종목만 사용합니다"
            )

        if not conditions:
            pg_logger.debug(
                f"[CONDITION] {strategy.get('id')}: 조건이 없어 {len(my_symbols)}개 종목을 그대로 반환합니다"
            )
            return my_symbols

        passed_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        for symbol_info in my_symbols:
            conditions = strategy.get("conditions", [])
            logic = strategy.get("logic", "and")
            threshold = strategy.get("threshold", None)
            tasks: List[asyncio.Task] = []
            task_metadata: Dict[asyncio.Task, Dict[str, Any]] = {}
            for index, condition in enumerate(conditions):
                task = asyncio.create_task(
                    self.execute_condition(
                        system=system,
                        symbol_info=symbol_info,
                        condition=condition
                    )
                )
                tasks.append(task)
                task_metadata[task] = {"condition": condition, "index": index}

            condition_results: List[
                Union[
                    BaseStrategyConditionResponseOverseasStockType,
                    BaseStrategyConditionResponseOverseasFuturesType,
                ]
            ] = []
            for task in asyncio.as_completed(tasks):
                try:
                    res = await task

                    pg_listener.emit_strategies(
                        payload={
                            "condition_id": res.get("condition_id", None),
                            "message": "Completed condition execution",
                            "response": res,
                        }
                    )
                    pg_logger.debug(
                        f"[CONDITION] {res.get('condition_id')}: {self._symbol_label(symbol_info)} 결과 -> 성공={res.get('success')} 가중치={res.get('weight', 0)}"
                    )
                    condition_results.append(res)

                except Exception as e:
                    pg_logger.error(f"[CONDITION] {strategy.get('id')}: 조건 실행 중 오류가 발생했습니다 -> {e}")
                    meta = task_metadata.get(task, {})
                    condition_obj = meta.get("condition") if meta else None
                    condition_label = self._describe_condition(condition_obj) if condition_obj is not None else None
                    cond_exc = ConditionExecutionException(
                        message="조건 실행 중 오류가 발생했습니다.",
                        data={
                            "strategy_id": strategy.get("id"),
                            "symbol": self._symbol_label(symbol_info),
                            "condition": condition_label,
                            "condition_index": meta.get("index") if meta else None,
                        },
                    )
                    pg_listener.emit_exception(cond_exc)

                    failure_response = self._build_response(symbol_info, success=False)

                    pg_listener.emit_strategies(
                        payload={
                            "condition_id": failure_response.get("condition_id"),
                            "message": f"Failed executing condition: {e}",
                            "response": failure_response,
                        }
                    )
                    condition_results.append(failure_response)

            complete, total_weight = self.evaluate_logic(results=condition_results, logic=logic, threshold=threshold)
            if complete:
                pg_logger.debug(
                    f"[CONDITION] {strategy.get('id')}: 종목 {self._symbol_label(symbol_info)} 통과 (가중치 {total_weight})"
                )
                passed_symbols.append(symbol_info)
            else:
                pg_logger.debug(
                    f"[CONDITION] {strategy.get('id')}: 종목 {self._symbol_label(symbol_info)}이(가) 조건을 통과하지 못했습니다"
                )

        return passed_symbols

    async def _get_order_types(
        self,
        order_id: str,
        orders: list[OrderStrategyType],
    ):
        """
        Get the order types for a specific order ID.
        """

        for trade in orders:
            if trade.get("order_id") == order_id:
                condition = trade.get("condition", None)
                if condition is None:
                    continue

                if isinstance(condition, (BaseOrderOverseasStock, BaseOrderOverseasFutures)):
                    return condition.order_types

                condition_id = condition.get("condition_id")
                order_types = await self.resolver.get_order_types(condition_id)
                return order_types

        return None
