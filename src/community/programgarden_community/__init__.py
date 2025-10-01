"""Programgarden community package root.

This module implements a LangChain-style lazy import surface: names listed in
``_MODULE_MAP`` are imported from their submodules on first access via
``__getattr__``. Use ``getCommunityCondition(name)`` to dynamically retrieve a class
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
    "getCommunityCondition",
]


_MODULE_MAP = {
    "SMAGoldenDeadCross": (
        "programgarden_community.overseas_stock.strategy_conditions.sma_golden_dead",
        "SMAGoldenDeadCross",
    ),
    "StockSplitFunds": (
        "programgarden_community.overseas_stock.new_order_conditions.stock_split_funds",
        "StockSplitFunds",
    ),
    "BasicLossCutManager": (
        "programgarden_community.overseas_stock.new_order_conditions.loss_cut",
        "BasicLossCutManager",
    ),
    "TrackingPriceModifyBuy": (
        "programgarden_community.overseas_stock.modify_order_conditions.tracking_price",
        "TrackingPriceModifyBuy",
    ),
    "PriceRangeCanceller": (
        "programgarden_community.overseas_stock.cancel_order_conditions.price_range_canceller",
        "PriceRangeCanceller",
    )
}


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
    if name in _MODULE_MAP:
        module_name, class_name = _MODULE_MAP[name]
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)

        replacement = f"{module_name}.{class_name}"
        _warn_on_import(name, replacement)

        globals()[name] = cls
        return cls

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    shown: List[str] = list(globals().keys())
    shown.extend(_MODULE_MAP.keys())
    return sorted(shown)


def getCommunityCondition(class_name: str) -> Any:
    """Dynamically import and return a class by its registered id.

    This mirrors the explicit-branch behaviour above and avoids importing the
    entire package root.
    """
    if class_name in _MODULE_MAP:
        module_name, class_name_actual = _MODULE_MAP[class_name]
        module = __import__(module_name, fromlist=[class_name_actual])
        return getattr(module, class_name_actual)

    raise ValueError(f"{class_name} is not a valid community tool.")
