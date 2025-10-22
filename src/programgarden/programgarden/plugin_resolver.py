from typing import Dict, List, Optional, Union
import inspect
from programgarden_core import (
    BaseStrategyCondition,
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,
    pg_logger,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType,
    exceptions, HeldSymbol,
    NonTradedSymbol, OrderStrategyType
)
from programgarden_core import (
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasFutures,
    BaseModifyOrderOverseasStock,
    BaseModifyOrderOverseasFutures,
    BaseCancelOrderOverseasStock,
    BaseCancelOrderOverseasFutures,
)
from programgarden_core import (
    BaseNewOrderOverseasStockResponseType,
    BaseModifyOrderOverseasStockResponseType,
    BaseCancelOrderOverseasStockResponseType,
    BaseNewOrderOverseasFuturesResponseType,
    BaseModifyOrderOverseasFutureResponseType,
    BaseCancelOrderOverseasFuturesResponseType,
)
try:
    from programgarden_community import getCommunityCondition  # type: ignore[import]
except ImportError:
    def getCommunityCondition(_condition_id):
        return None

from programgarden.buysell_executor import DpsTyped


class PluginResolver:
    """Resolve and cache plugin classes by identifier.

    Cache shape: Dict[str, type]
    - keys are identifiers used for lookup (short name or fqdn)
    - values are the resolved class objects
    """
    def __init__(self):
        self._plugin_cache: Dict[str, type] = {}

    def _build_failure_response(
        self,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
        condition_id: Optional[str],
    ) -> Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
        product_type = symbol_info.get("product_type") if isinstance(symbol_info, dict) else None
        product = "overseas_futures" if product_type == "overseas_futures" else "overseas_stock"

        response: Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType] = {
            "condition_id": condition_id,
            "success": False,
            "symbol": symbol_info.get("symbol", ""),
            "exchcd": symbol_info.get("exchcd", ""),
            "data": {},
            "weight": 0,
            "product": product,
        }

        if product == "overseas_futures":
            response["position_side"] = "flat"

        return response

    async def _resolve(self, condition_id: str):
        """Locate a plugin class by name and cache the result.

        This method accepts either a short class name ("MyPlugin") or a
        fully-qualified class name ("package.module.MyPlugin"). It
        returns the class object if found and subclasses either
        `BaseStrategyCondition` or `BaseNewBuyOverseasStock`.

        Behaviour and notes:
        - If the condition_id is already cached, the cached class is
          returned immediately.
        - Fully-qualified names are resolved first using importlib.
        - If `programgarden_community` is installed, the resolver
          attempts a top-level attribute lookup on the package and
          then scans submodules using `pkgutil.walk_packages`.
        - All import/scan failures are logged but do not raise; a
          failure to resolve simply returns `None`.

        Args:
            condition_id: Short or fully-qualified class name to resolve.

        Returns:
            The resolved class object if found and valid, otherwise
            `None`.
        """
        if condition_id in self._plugin_cache:
            return self._plugin_cache[condition_id]

        # Attempt to use the optional `programgarden_community` package
        # (if installed) to find community-provided plugins.
        try:
            exported_cls = getCommunityCondition(condition_id)
            if inspect.isclass(exported_cls) and issubclass(
                exported_cls,
                (
                    BaseStrategyCondition,
                    BaseStrategyConditionOverseasStock,
                    BaseStrategyConditionOverseasFutures,
                    BaseOrderOverseasStock,
                    BaseOrderOverseasFutures,
                    BaseNewOrderOverseasStock,
                    BaseNewOrderOverseasFutures,
                    BaseModifyOrderOverseasStock,
                    BaseModifyOrderOverseasFutures,
                    BaseCancelOrderOverseasStock,
                    BaseCancelOrderOverseasFutures,
                ),
            ):
                self._plugin_cache[condition_id] = exported_cls
                return exported_cls
        except Exception as exc:
            pg_logger.debug(f"programgarden_community에서 '{condition_id}' 클래스를 찾는 중 오류 발생: {exc}")

        return None

    async def resolve_buysell_community(
        self,
        system_id: Optional[str],
        trade: OrderStrategyType,
        symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = [],
        held_symbols: List[HeldSymbol] = [],
        non_trade_symbols: List[NonTradedSymbol] = [],
        dps: Optional[DpsTyped] = None
    ) -> tuple[
        Optional[
            Union[
                List[BaseNewOrderOverseasStockResponseType],
                List[BaseModifyOrderOverseasStockResponseType],
                List[BaseCancelOrderOverseasStockResponseType],
                List[BaseNewOrderOverseasFuturesResponseType],
                List[BaseModifyOrderOverseasFutureResponseType],
                List[BaseCancelOrderOverseasFuturesResponseType],
            ]
        ],
        Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFutures]]
            ]:
        """Resolve and run the configured buy/sell plugin.

        Returns:
            A list of `BaseNewOrderOverseasStockResponseType` or `BaseModifyOrderOverseasStockResponseType` objects produced
            by the plugin, or None if an error occurred.
        """

        condition = trade.get("condition", {})
        if isinstance(condition, (BaseOrderOverseasStock, BaseOrderOverseasFutures)):

            if hasattr(condition, "_set_available_symbols"):
                condition._set_available_symbols(symbols)
            if hasattr(condition, "_set_held_symbols"):
                condition._set_held_symbols(held_symbols)
            if hasattr(condition, "_set_system_id") and system_id:
                condition._set_system_id(system_id)
            if hasattr(condition, "_set_non_traded_symbols"):
                condition._set_non_traded_symbols(non_trade_symbols)
            if hasattr(condition, "_set_available_balance") and dps:
                condition._set_available_balance(
                    fcurr_dps=dps.get("fcurr_dps", 0.0),
                    fcurr_ord_able_amt=dps.get("fcurr_ord_able_amt", 0.0)
                )

            result = await condition.execute()
            return result, condition

        ident = condition.get("condition_id")
        params = condition.get("params", {}) or {}

        cls = await self._resolve(ident)

        if cls is None:
            pg_logger.error(f"[PLUGIN] {ident}: 조건 클래스를 찾을 수 없습니다")
            raise exceptions.NotExistConditionException(
                message=f"Condition class '{ident}' not found"
            )

        try:
            community_instance = cls(**params)
            # If plugin supports receiving the current symbol list, provide it.
            if hasattr(community_instance, "_set_available_symbols"):
                community_instance._set_available_symbols(symbols)
            if hasattr(community_instance, "_set_held_symbols"):
                community_instance._set_held_symbols(held_symbols)
            if hasattr(community_instance, "_set_system_id") and system_id:
                community_instance._set_system_id(system_id)
            if hasattr(community_instance, "_set_non_traded_symbols"):
                community_instance._set_non_traded_symbols(non_trade_symbols)
            if hasattr(community_instance, "_set_available_balance") and dps:
                community_instance._set_available_balance(
                    fcurr_dps=dps.get("fcurr_dps", 0.0),
                    fcurr_ord_able_amt=dps.get("fcurr_ord_able_amt", 0.0)
                )

            if not isinstance(community_instance, (BaseOrderOverseasStock, BaseOrderOverseasFutures)):
                pg_logger.error(
                    f"[PLUGIN] {ident}: 주문 플러그인 타입이 올바르지 않습니다"
                )
                raise TypeError(f"{__class__.__name__}: Condition class '{ident}' is not a subclass of BaseOrderOverseasStock/BaseOrderOverseasFutures")

            # Plugins expose an async `execute` method that returns the symbols to act on.
            pg_logger.debug(
                f"[PLUGIN] {ident}: 매매 플러그인을 실행합니다 (입력 종목 {len(symbols or [])}개)"
            )
            result = await community_instance.execute()
            pg_logger.debug(
                f"[PLUGIN] {ident}: 플러그인이 {len(result or []) if result else 0}개 종목을 반환했습니다"
            )

            return result, community_instance

        except Exception:
            # Log the full traceback to aid external developers debugging plugin errors.
            pg_logger.exception(f"[PLUGIN] {ident}: 매매 플러그인 실행 중 오류가 발생했습니다")
            return None, None

    async def resolve_condition(
        self,
        system_id: Optional[str],
        condition_id: str,
        params: Dict,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
    ) -> Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
        cls = await self._resolve(condition_id)

        if cls is None:
            pg_logger.error(f"[PLUGIN] {condition_id}: 조건 클래스를 찾을 수 없습니다")
            raise exceptions.NotExistConditionException(
                message=f"Condition class '{condition_id}' not found"
            )

        try:
            instance = cls(**params)
            if hasattr(instance, "_set_symbol"):
                instance._set_symbol(symbol_info)
            if hasattr(instance, "_set_system_id") and system_id:
                instance._set_system_id(system_id)

            if not isinstance(instance, BaseStrategyCondition):
                pg_logger.error(
                    f"[PLUGIN] {condition_id}: BaseStrategyCondition을 상속하지 않은 클래스입니다"
                )
                raise exceptions.NotExistConditionException(
                    message=f"Condition class '{condition_id}' is not a subclass of BaseStrategyCondition"
                )
            pg_logger.debug(
                f"[PLUGIN] {condition_id}: 전략 조건을 실행합니다 (params={params})"
            )
            result = await instance.execute()

            return result

        except exceptions.NotExistConditionException as e:
            pg_logger.error(f"[PLUGIN] {condition_id}: 조건이 존재하지 않습니다 -> {e}")

            return self._build_failure_response(symbol_info, condition_id)

        except Exception:
            pg_logger.exception(f"[PLUGIN] {condition_id}: 조건 실행 중 처리되지 않은 오류가 발생했습니다")
            return self._build_failure_response(symbol_info, condition_id)

    async def get_order_types(self, condition_id: str) -> Optional[List[OrderType]]:
        """Get order types from a condition class."""
        cls = await self._resolve(condition_id)
        if cls and hasattr(cls, 'order_types'):
            return cls.order_types
        return None
