"""
Plugin discovery and caching utilities.

This module provides a small helper for locating "plugin" classes that
implement either condition or buy logic for the ProgramGarden system.

The resolver performs the following search strategy (in order):
1. If the identifier looks like a fully-qualified name (contains a dot),
     attempt to import the module and retrieve the class by name.
2. Try to resolve a top-level export from the optional
     `programgarden_community` package (if installed).
3. Scan all modules under `programgarden_community` (using
     `pkgutil.walk_packages`) and import modules to look for the class.

When a matching class is found it is cached for future lookups. The
cache stores both the original identifier and a fully-qualified name
(when available) so lookups later can succeed with either form.

Notes:
- The resolver only considers classes that subclass `BaseCondition`
    or `BaseBuyOverseasStock` from `programgarden_core`.
- The resolver swallows import/scan exceptions and logs them via
    `pg_logger`; callers should not rely on exceptions being raised for
    resolution failures.
- `PluginResolver.resolve` is declared `async` for compatibility with
    async code paths, but the implementation is synchronous internally.
"""

from typing import Dict, List, Optional, Union
import inspect
from programgarden_core import (
    BaseCondition, BaseBuyOverseasStock, pg_logger,
    SymbolInfo, BaseBuyOverseasStockResponseType, BaseSellOverseasStockResponseType,
    exceptions, NewBuyTradeType, HeldSymbol,
    NonTradedSymbol, BaseSellOverseasStock,
    BaseConditionResponseType
)
from programgarden_community import getCommunityCondition

from programgarden.buysell_executor import DpsTyped


class PluginResolver:
    """Resolve and cache plugin classes by identifier.

    The resolver is lightweight and intended to be used by callers that
    need to convert a short name (e.g. "MyCondition") or a fully-
    qualified name (e.g. "some.module.MyCondition") into the concrete
    plugin class object. Resolved classes are cached in-memory to avoid
    repeated import and scan costs.

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
        `BaseCondition` or `BaseBuyOverseasStock`.

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
            if inspect.isclass(exported_cls) and issubclass(exported_cls, (BaseCondition, BaseBuyOverseasStock)):
                self._plugin_cache[condition_id] = exported_cls
                return exported_cls
        except Exception as e:
            pg_logger.debug(f"Error scanning programgarden_community for class '{condition_id}': {e}")

        return None

    async def resolve_buysell_community(
            self,
            system_id: Optional[str],
            trade: Union[NewBuyTradeType],
            symbols: List[SymbolInfo] = [],
            held_symbols: List[HeldSymbol] = [],
            non_trade_symbols: List[NonTradedSymbol] = [],
            dps: Optional[DpsTyped] = None
    ) -> tuple[Optional[Union[List[BaseBuyOverseasStockResponseType], List[BaseSellOverseasStockResponseType]]], Optional[Union[BaseBuyOverseasStock, BaseSellOverseasStock]]]:
        """Resolve and run the configured buy/sell plugin.

        Returns:
            A list of `BaseBuyOverseasStockResponseType` or `BaseSellOverseasStockResponseType` objects produced
            by the plugin, or None if an error occurred.
        """

        condition = trade.get("condition", {})
        if isinstance(condition, BaseBuyOverseasStock) or isinstance(condition, BaseSellOverseasStock):
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

            if not isinstance(community_instance, BaseBuyOverseasStock):
                raise TypeError(f"{__class__.__name__}: Condition class '{ident}' is not a subclass of BaseBuyOverseasStock")

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
    ) -> BaseConditionResponseType:
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

            if not isinstance(instance, BaseCondition):
                raise exceptions.NotExistConditionException(
                    message=f"Condition class '{condition_id}' is not a subclass of BaseCondition"
                )
            result = await instance.execute()

            return result

        except exceptions.NotExistConditionException as e:
            pg_logger.error(f"Condition '{condition_id}' does not exist: {e}")

            return BaseConditionResponseType(
                condition_id=condition_id,
                success=False,
                exchcd=symbol_info.get("exchcd"),
                symbol=symbol_info.get("symbol"),
                weight=0
            )

        except Exception as e:
            pg_logger.error(f"Error executing condition '{condition_id}': {e}")
            return BaseConditionResponseType(
                condition_id=condition_id,
                success=False,
                exchcd=symbol_info.get("exchcd"),
                symbol=symbol_info.get("symbol"),
                weight=0
            )
