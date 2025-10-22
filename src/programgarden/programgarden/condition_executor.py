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
)

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
            result = await condition.execute()

            return result

        if isinstance(condition, dict):
            if "condition_id" in condition and "conditions" not in condition:
                return await self._execute_plugin_condition(
                    system_id=system.get("settings", {}).get("system_id", None),
                    condition=condition,
                    symbol_info=symbol_info,
                )
            # Nested condition group
            if "conditions" in condition:
                return await self._execute_nested_condition(system, symbol_info, condition)
            # Unknown dict shape: treat as failure but keep symbol context.
            return self._build_response(symbol_info, success=False)

        pg_logger.warning(f"Unknown condition type: {type(condition)}")
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

        return await self.resolver.resolve_condition(
            system_id=system_id,
            condition_id=condition_id,
            params=params,
            symbol_info=symbol_info,
        )

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

        tasks = [
            asyncio.create_task(
                self.execute_condition(system=system, symbol_info=symbol_info, condition=condition)
            )
            for condition in conditions
        ]

        condition_results: List[
            Union[
                BaseStrategyConditionResponseOverseasStockType,
                BaseStrategyConditionResponseOverseasFuturesType,
            ]
        ] = []
        for task in asyncio.as_completed(tasks):
            try:
                res = await task
                condition_results.append(res)

            except Exception as e:
                pg_logger.error(f"Error executing condition: {e}")
                condition_results.append(
                    self._build_response(symbol_info, success=False, condition_id=None)
                )

        complete, total_weight = self.evaluate_logic(results=condition_results, logic=logic, threshold=threshold)
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

        order_types = await self._get_order_types(order_id, orders)

        market_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        account_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        non_account_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []

        if not my_symbols and ("new_buy" in order_types or order_types is None):
            market_symbols = await self.symbol_provider.get_symbols(
                order_type="new_buy",
                securities=securities,
            )

        if "new_sell" in order_types:
            account_symbols = await self.symbol_provider.get_symbols(
                order_type="new_sell",
                securities=securities,
            )

        if "modify_buy" in order_types:
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="modify_buy",
                securities=securities,
            )
        elif "modify_sell" in order_types:
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="modify_sell",
                securities=securities,
            )
        elif "cancel_buy" in order_types:
            non_account_symbols = await self.symbol_provider.get_symbols(
                order_type="cancel_buy",
                securities=securities,
            )
        elif "cancel_sell" in order_types:
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

        if not conditions:
            return my_symbols

        passed_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        for symbol_info in my_symbols:
            conditions = strategy.get("conditions", [])
            logic = strategy.get("logic", "and")
            threshold = strategy.get("threshold", None)
            tasks = [
                asyncio.create_task(
                    self.execute_condition(
                        system=system,
                        symbol_info=symbol_info,
                        condition=condition
                    )
                )
                for condition in conditions
            ]

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
                    condition_results.append(res)

                except Exception as e:
                    pg_logger.error(f"Error executing condition: {e}")

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
                passed_symbols.append(symbol_info)

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
                condition_id = trade.get("condition", {}).get("condition_id")
                order_types = await self.resolver.get_order_types(condition_id)
                return order_types

        return None
