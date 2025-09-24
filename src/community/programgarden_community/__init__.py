"""Programgarden community package root.

This module implements a LangChain-style lazy import surface: names listed in
``_MODULE_MAP`` are imported from their submodules on first access via
``__getattr__``. Use ``getCommunityTool(name)`` to dynamically retrieve a class
by its id string.
"""

from importlib import metadata
import warnings
from typing import Any, List, Optional

try:
    __version__ = metadata.version(__package__)
except metadata.PackageNotFoundError:
    __version__ = ""
del metadata

__all__ = [
    "SMAGoldenDeadCross",
    "StockSplitFunds",
    "getCommunityTool",
]


def _warn_on_import(name: str, replacement: Optional[str] = None) -> None:
    """Emit a warning when a name is imported from the package root.

    This mirrors LangChain's behaviour: importing many symbols from the root
    is convenient but we suggest importing from the actual submodule.
    """
    if replacement:
        warnings.warn(
            f"Importing {name} from programgarden_community root is discouraged; "
            f"prefer {replacement}",
            stacklevel=3,
        )


def __getattr__(name: str) -> Any:
    """LangChain-style explicit lazy import surface.

    Each supported top-level name is handled with an explicit branch that
    imports the real implementation from its submodule on first access.
    """
    if name == "SMAGoldenDeadCross":
        from programgarden_community.overseas_stock.strategy_conditions.sma_golden_dead import (
            SMAGoldenDeadCross,
        )

        _warn_on_import(
            name,
            replacement=(
                "programgarden_community.overseas_stock.strategy_conditions.sma_golden_dead.SMAGoldenDeadCross"
            ),
        )

        globals()[name] = SMAGoldenDeadCross
        return SMAGoldenDeadCross

    if name == "StockSplitFunds":
        from programgarden_community.overseas_stock.new_buy_conditions.stock_split_funds import (
            StockSplitFunds,
        )

        _warn_on_import(
            name,
            replacement=(
                "programgarden_community.overseas_stock.new_buy_conditions.stock_split_funds.StockSplitFunds"
            ),
        )

        globals()[name] = StockSplitFunds
        return StockSplitFunds

    if name == "TrailingStopManager":
        from programgarden_community.overseas_stock.new_sell_conditions.trailing_stop import (
            TrailingStopManager,
        )

        _warn_on_import(
            name,
            replacement=(
                "programgarden_community.overseas_stock.new_sell_conditions.trailing_stop.TrailingStopManager"
            ),
        )

        globals()[name] = TrailingStopManager
        return TrailingStopManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    shown: List[str] = list(globals().keys())
    shown.extend(["SMAGoldenDeadCross", "StockSplitFunds"])
    return sorted(shown)


def getCommunityCondition(class_name: str) -> Any:
    """Dynamically import and return a class by its registered id.

    This mirrors the explicit-branch behaviour above and avoids importing the
    entire package root.
    """
    if class_name == "SMAGoldenDeadCross":
        from programgarden_community.overseas_stock.strategy_conditions.sma_golden_dead import (
            SMAGoldenDeadCross,
        )

        return SMAGoldenDeadCross

    if class_name == "StockSplitFunds":
        from programgarden_community.overseas_stock.new_buy_conditions.stock_split_funds import (
            StockSplitFunds,
        )

        return StockSplitFunds

    if class_name == "TrailingStopManager":
        from programgarden_community.overseas_stock.new_sell_conditions.trailing_stop import (
            TrailingStopManager,
        )

        return TrailingStopManager

    raise ValueError(f"{class_name} is not a valid community tool.")
