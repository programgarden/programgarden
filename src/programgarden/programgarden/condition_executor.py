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
    condition_logger,
    OrderStrategyType,
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,
    StrategySymbolInputType,
)
from programgarden_core.exceptions import ConditionExecutionException

from programgarden.pg_listener import pg_listener

from .plugin_resolver import PluginResolver
from .symbols_provider import SymbolProvider


EXCHANGE_CODE_ALIASES: Dict[str, str] = {
    "81": "81",
    "nyse": "81",
    "amex": "81",
    "82": "82",
    "nasdaq": "82",
}


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

    def _normalize_exchange_code(self, exchange: Any) -> str:
        """Map human-friendly exchange aliases to LS market codes."""

        if isinstance(exchange, str):
            normalized = exchange.strip()
            if not normalized:
                return normalized

            alias = normalized.lower()
            return EXCHANGE_CODE_ALIASES.get(alias, normalized)

        return str(exchange)

    def _symbol_label(self, symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]) -> str:
        if isinstance(symbol_info, dict):
            exch = symbol_info.get("exchcd") or symbol_info.get("ExchCode") or "?"
            symbol = symbol_info.get("symbol") or symbol_info.get("IsuCodeVal") or symbol_info.get("ShtnIsuNo") or "?"
            return f"{exch}:{symbol}"
        return str(symbol_info)

    def _coerce_user_symbols(
        self,
        symbols: Optional[List[
            StrategySymbolInputType,
        ]],
        product: Optional[str],
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """사용자가 관심종목으로 넣은 종목 딕셔너리가 필요한 런타임 필드를 포함하도록 합니다."""

        if not symbols:
            return []

        normalized_product = "overseas_futures" if product == "overseas_futures" else "overseas_stock"
        coerced: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []

        for entry in symbols:
            if not isinstance(entry, dict):
                coerced.append(entry)
                continue

            product_type = entry.get("product_type")
            if product_type in {"overseas_stock", "overseas_futures"}:
                coerced.append(entry)
                continue

            normalized = dict(entry)
            exchange = normalized.get("exchcd") or normalized.pop("exchange", None)
            if exchange:
                normalized["exchcd"] = self._normalize_exchange_code(exchange)

            name = normalized.get("symbol_name") or normalized.pop("name", None)
            if name:
                normalized["symbol_name"] = name

            normalized["product_type"] = normalized_product
            if normalized_product == "overseas_futures" and "position_side" not in normalized:
                normalized["position_side"] = "flat"

            coerced.append(normalized)

        return coerced

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
    ) -> Tuple[bool, int, Optional[str]]:
        """Evaluate condition results with logical operators and futures direction.

        Returns a tuple: (bool_result, numeric_weight, aligned_position_side).
        For overseas futures conditions a success requires a non-flat direction, and
        all successful futures conditions must agree on the same side.
        """

        normalized_successes: List[bool] = []
        futures_sides: List[str] = []

        for result in results:
            product = str(result.get("product", "") or "").lower()
            position_side = str(result.get("position_side", "") or "").lower()
            is_success = bool(result.get("success", False))

            if product == "overseas_futures":
                if is_success and position_side in {"long", "short"}:
                    futures_sides.append(position_side)
                else:
                    # Treat flat/missing direction as failure for futures conditions.
                    is_success = False

            normalized_successes.append(is_success)

        success_count = sum(1 for success in normalized_successes if success)

        bool_result = False
        total_weight = 0

        if logic in ("and", "all"):
            bool_result = all(normalized_successes) if normalized_successes else True
        elif logic in ("or", "any"):
            bool_result = any(normalized_successes)
        elif logic == "not":
            bool_result = not any(normalized_successes)
        elif logic == "xor":
            bool_result = success_count == 1
        elif logic == "at_least":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'at_least' logic.")
            bool_result = success_count >= threshold
        elif logic == "at_most":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'at_most' logic.")
            bool_result = success_count <= threshold
        elif logic == "exactly":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'exactly' logic.")
            bool_result = success_count == threshold
        elif logic == "weighted":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'weighted' logic.")
            total_weight = sum(
                result.get("weight", 0) for result, success in zip(results, normalized_successes) if success
            )
            bool_result = total_weight >= threshold

        unique_sides = {side for side in futures_sides}
        aligned_side: Optional[str] = None

        if bool_result:
            if len(unique_sides) > 1:
                condition_logger.debug("해외선물 조건 간 방향이 일치하지 않아 실패 처리합니다")
                bool_result = False
            elif len(unique_sides) == 1:
                aligned_side = unique_sides.pop()

        weight_result = total_weight if bool_result and logic == "weighted" else 0

        if not bool_result:
            aligned_side = None

        return (bool_result, weight_result, aligned_side)

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
                condition_logger.debug(
                    f"{condition.get('condition_id')}: {self._symbol_label(symbol_info)}에 대한 플러그인 조건을 평가합니다"
                )
                return await self._execute_plugin_condition(
                    system_id=system.get("settings", {}).get("system_id", None),
                    condition=condition,
                    symbol_info=symbol_info,
                )
            # Nested condition group
            if "conditions" in condition:
                condition_logger.debug(
                    f"group: {self._symbol_label(symbol_info)}에 대해 로직 '{condition.get('logic', 'and')}'을 평가합니다"
                )
                return await self._execute_nested_condition(system, symbol_info, condition)
            # Unknown dict shape: treat as failure but keep symbol context.
            return self._build_response(symbol_info, success=False)

        condition_logger.warning(
            f"지원되지 않는 조건 타입입니다: {type(condition)}"
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

        position_side = result.get("position_side", None)
        direction_note = f", 방향 {position_side}" if position_side else ""
        status = "통과" if result.get("success") else "실패"
        condition_logger.debug(
            f"조건 {condition_id}의 {self._symbol_label(symbol_info)} 종목의 계산의 결과는 {status}이고 가중치는 {result.get('weight', 0)}{direction_note} 입니다."
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
                condition_logger.error(f"그룹 조건 실행 중 오류가 발생했습니다: {e}")
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

        complete, total_weight, position_side = self.evaluate_logic(
            results=condition_results,
            logic=logic,
            threshold=threshold,
        )
        if failure_count:
            condition_logger.warning(
                f"그룹: {self._symbol_label(symbol_info)} 대상 조건 {failure_count}개가 실패했습니다"
            )
        if not complete:
            return self._build_response(
                symbol_info,
                success=False,
                weight=total_weight,
                position_side=position_side,
            )

        # All conditions passed
        symbol_info["position_side"] = position_side or "flat"
        return self._build_response(
            symbol_info,
            success=True,
            weight=total_weight,
            position_side=position_side,
        )

    async def execute_condition_list(
        self,
        system: SystemType,
        strategy: StrategyType,
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """
        Perform calculations defined in the strategy
        """

        securities = system.get("securities", {})
        order_id = strategy.get("order_id", None)
        orders = system.get("orders", {})
        conditions = strategy.get("conditions", [])
        product = securities.get("product", None)

        my_symbols = self._coerce_user_symbols(
            symbols=strategy.get("symbols", []),
            product=product,
        )
        strategy["symbols"] = my_symbols

        order_types = []
        if order_id is not None:
            order_types = await self._get_order_types(order_id, orders)

        market_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        account_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        non_account_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []

        # 해외주식은 매수/매도 구분이 필요하지만
        # 해외선물은 매수/매도 구분 없이 보유종목(미결제종목)을 조회해야한다.
        if product == "overseas_stock":
            if (
                not my_symbols
                or (
                    order_types is None
                    or "new_buy" in order_types
                )
            ):
                market_symbols = await self.symbol_provider.get_symbols(
                    order_type="new_buy",
                    securities=securities,
                )

            if "new_sell" in order_types:
                account_symbols = await self.symbol_provider.get_symbols(
                    order_type="new_sell",
                    securities=securities,
                )

        elif product == "overseas_futures":
            if (
                not my_symbols
                or (
                    order_types is None
                    or "new_buy" in order_types
                    or "new_sell" in order_types
                )
            ):
                market_symbols = await self.symbol_provider.get_symbols(
                    order_type=None,
                    securities=securities,
                    product=product,
                )

            account_symbols = await self.symbol_provider.get_symbols(
                order_type=None,
                securities=securities,
                product=product,
                futures_outstanding_only=True,
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

        # TODO: 관심종목의 종목이 중복 계산되지 않도록, 전체종목 및 보유종목 및 미체결종목에 포함되어 있으면
        # 관심종목에서 제외되도록 만든다.
        seen_ids = set()
        for symbol in my_symbols:
            exch = symbol.get("exchange", "") or symbol.get("exchcd", "")
            sym = symbol.get("symbol", "")
            seen_ids.add(f"{exch}:{sym}")
        print("market_symbols:", seen_ids)

        # TODO 관심종목을 확인해서 보유종목, 미체결 종목에 있는지 확인한 후에
        # 없으면 관심종목만 계산하도록 진행한다.

        responsible_symbols: List[SymbolInfoOverseasStock | SymbolInfoOverseasFutures] = []

        # 미체결 정정/취소 주문에서는 관심종목에 있는 경우만 계산하도록 한다.
        for non_symbol in non_account_symbols:
            exch = non_symbol.get("exchange", "") or non_symbol.get("exchcd", "")
            sym = non_symbol.get("symbol", "")
            # ord_no = symbol.get("OrdNo", "")
            ident = f"{exch}:{sym}"
            if ident in seen_ids:
                responsible_symbols.append(non_symbol)

        # 보유 잔고 판매 주문에서는 관심종목에 있는 경우만 계산하도록 한다.
        for account_symbol in account_symbols:
            exch = account_symbol.get("exchange", "") or account_symbol.get("exchcd", "")
            sym = account_symbol.get("symbol", "")
            ident = f"{exch}:{sym}"
            if ident in seen_ids:
                responsible_symbols.append(account_symbol)

        # 시장 종목들 주문에서는 관심종목에 있는 경우만 계산하도록 만든다.
        for market_symbol in market_symbols:
            exch = market_symbol.get("exchange", "") or market_symbol.get("exchcd", "")
            sym = market_symbol.get("symbol", "")
            ident = f"{exch}:{sym}"
            if ident in seen_ids:
                responsible_symbols.append(market_symbol)

        max_symbols = strategy.get("max_symbols", {})
        max_order = max_symbols.get("order", "random")
        max_count = max_symbols.get("limit", 0)

        # Sort symbols based on the specified order
        if max_order == "random":
            import random
            random.shuffle(responsible_symbols)
        elif max_order == "mcap":
            responsible_symbols.sort(key=lambda x: x.get("mcap", 0), reverse=True)

        if max_count > 0:
            responsible_symbols = responsible_symbols[:max_count]
            condition_logger.debug(
                f"{strategy.get('id')}: '{max_order}' 기준으로 최대 {max_count}개 종목만 사용합니다"
            )

        if not conditions:
            condition_logger.debug(
                f"{strategy.get('id')}: 조건이 없어 {len(responsible_symbols)}개 종목을 그대로 반환합니다"
            )
            return responsible_symbols

        if not responsible_symbols:
            condition_logger.debug(f"{order_id} 주문 전략을 위해서 분석하려는 종목이 없습니다.")
            return []

        passed_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        for symbol_info in responsible_symbols:
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

                    position_side = res.get("position_side", None)
                    direction_note = f", 방향 {position_side}" if position_side else ""
                    status = "통과" if res.get("success") else "실패"
                    condition_logger.debug(
                        f"조건 {res.get('condition_id')}의 {self._symbol_label(symbol_info)} 종목의 계산의 결과는 {status}이고 가중치는 {res.get('weight', 0)}{direction_note}입니다."
                    )
                    condition_results.append(res)

                except Exception as e:
                    condition_logger.error(f"{strategy.get('id')}: 조건 실행 중 오류가 발생했습니다 -> {e}")
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

            complete, total_weight, position_side = self.evaluate_logic(
                results=condition_results,
                logic=logic,
                threshold=threshold,
            )
            if complete:
                symbol_info["position_side"] = position_side or "flat"
                passed_symbols.append(symbol_info)
            else:
                condition_logger.debug(
                    f"{strategy.get('id')}: 종목 {self._symbol_label(symbol_info)}이(가) 조건을 통과하지 못했습니다"
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
