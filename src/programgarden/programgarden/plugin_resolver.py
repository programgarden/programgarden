from typing import Dict, List, Optional, Union
import inspect
from programgarden_core import (
    BaseStrategyConditionResponseType, BaseStrategyCondition,
    pg_logger,
    SymbolInfo, OrderType,
    exceptions, HeldSymbol,
    NonTradedSymbol, OrderStrategyType
)
from programgarden_core import (
    BaseOrderOverseasStock,
    BaseNewOrderOverseasStock,
    BaseModifyOrderOverseasStock,
    BaseCancelOrderOverseasStock,
)
from programgarden_core import (
    BaseNewOrderOverseasStockResponseType,
    BaseModifyOrderOverseasStockResponseType,
    BaseCancelOrderOverseasStockResponseType
)
from programgarden_community import getCommunityCondition

from programgarden.buysell_executor import DpsTyped


class PluginResolver:
    """Resolve and cache plugin classes by identifier.

    Cache shape: Dict[str, type]
    - keys are identifiers used for lookup (short name or fqdn)
    - values are the resolved class objects
    """
    def __init__(self):
        self._plugin_cache: Dict[str, type] = {}

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
                    BaseOrderOverseasStock,
                    BaseNewOrderOverseasStock,
                    BaseModifyOrderOverseasStock,
                    BaseCancelOrderOverseasStock,
                ),
            ):
                self._plugin_cache[condition_id] = exported_cls
                return exported_cls
        except Exception as e:
            pg_logger.debug(f"Error scanning programgarden_community for class '{condition_id}': {e}")

        return None

    async def resolve_buysell_community(
            self,
            system_id: Optional[str],
            trade: OrderStrategyType,
            symbols: List[SymbolInfo] = [],
            held_symbols: List[HeldSymbol] = [],
            non_trade_symbols: List[NonTradedSymbol] = [],
            dps: Optional[DpsTyped] = None
    ) -> tuple[
        Optional[
            Union[
                    List[BaseNewOrderOverseasStockResponseType],
                    List[BaseModifyOrderOverseasStockResponseType],
                    List[BaseCancelOrderOverseasStockResponseType]
                ]
            ],
            Optional[BaseOrderOverseasStock]
            ]:
        """Resolve and run the configured buy/sell plugin.

        Returns:
            A list of `BaseNewOrderOverseasStockResponseType` or `BaseModifyOrderOverseasStockResponseType` objects produced
            by the plugin, or None if an error occurred.
        """

        condition = trade.get("condition", {})
        if isinstance(condition, BaseOrderOverseasStock):
            result = await condition.execute()
            return result, condition

        ident = condition.get("condition_id")
        params = condition.get("params", {}) or {}

        cls = await self._resolve(ident)

        if cls is None:
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

            if not isinstance(community_instance, BaseOrderOverseasStock):
                raise TypeError(f"{__class__.__name__}: Condition class '{ident}' is not a subclass of BaseOrderOverseasStock")

            # Plugins expose an async `execute` method that returns the symbols to act on.
            result = await community_instance.execute()

            return result, community_instance

        except Exception:
            # Log the full traceback to aid external developers debugging plugin errors.
            pg_logger.exception(f"Error executing buy/sell plugin '{ident}'")
            return None, None

    async def resolve_condition(
        self,
        system_id: Optional[str],
        condition_id: str,
        params: Dict,
        symbol_info: SymbolInfo
    ) -> BaseStrategyConditionResponseType:
        cls = await self._resolve(condition_id)

        if cls is None:
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
                raise exceptions.NotExistConditionException(
                    message=f"Condition class '{condition_id}' is not a subclass of BaseStrategyCondition"
                )
            result = await instance.execute()

            return result

        except exceptions.NotExistConditionException as e:
            pg_logger.error(f"Condition '{condition_id}' does not exist: {e}")

            return BaseStrategyConditionResponseType(
                condition_id=condition_id,
                success=False,
                exchcd=symbol_info.get("exchcd"),
                symbol=symbol_info.get("symbol"),
                weight=0
            )

        except Exception as e:
            pg_logger.error(f"Error executing condition '{condition_id}': {e}")
            return BaseStrategyConditionResponseType(
                condition_id=condition_id,
                success=False,
                exchcd=symbol_info.get("exchcd"),
                symbol=symbol_info.get("symbol"),
                weight=0
            )

    async def get_order_types(self, condition_id: str) -> Optional[List[OrderType]]:
        """Get order types from a condition class."""
        cls = await self._resolve(condition_id)
        if cls and hasattr(cls, 'order_types'):
            return cls.order_types
        return None
