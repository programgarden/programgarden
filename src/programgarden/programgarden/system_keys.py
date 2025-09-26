"""programgarden.system_keys

This module provides utilities to validate that an externally supplied
system configuration object (`system`) contains all required keys.

It is intended to ensure that when external developers use this package,
the minimal runtime configuration (security credentials, strategy list,
buy settings, etc.) is explicitly checked so that nothing required is missing.

The function raises ValueError when required keys are missing.
"""

from programgarden_core import (
    SystemType,
    exceptions,
    pg_logger
)


def exist_system_keys_error(system: SystemType) -> None:
    """
    Verify that the System object contains all required keys.
    """

    if not isinstance(system, dict):
        pg_logger.error("Invalid system configuration: must be a dictionary.")
        raise exceptions.NotExistSystemException(
            message="Invalid system configuration: must be a dictionary.",
        )

    # --- settings ---
    settings = system.get("settings", {})
    if not settings:
        pg_logger.error("System settings information ('settings') is required.")
        raise exceptions.NotExistSystemKeyException(
            message="System settings information ('settings') is required.",
        )

    if not isinstance(settings, dict):
        pg_logger.error("System settings information ('settings') must be a dictionary.")
        raise exceptions.NotExistSystemKeyException(
            message="System settings information ('settings') must be a dictionary.",
        )

    if not settings.get("system_id", None):
        pg_logger.error("System settings must include a unique 'system_id'.")
        raise exceptions.NotExistSystemKeyException(
            message="System settings must include a unique 'system_id'.",
        )

    # --- securities ---
    securities = system.get("securities")
    if securities is None:
        pg_logger.error("System securities information ('securities') is required.")
        raise exceptions.NotExistSystemKeyException(
            message="System securities information ('securities') is required.",
        )

    if not isinstance(securities, dict):
        pg_logger.error("System securities information ('securities') must be a dictionary.")
        raise exceptions.NotExistSystemKeyException(
            message="System securities information ('securities') must be a dictionary.",
        )

    required_sec_keys = ["company", "product", "appkey", "appsecretkey"]
    for key in required_sec_keys:
        if key not in securities:
            pg_logger.error(f"Missing '{key}' key in system securities.")
            raise exceptions.NotExistSystemKeyException(
                message=f"Missing '{key}' key in system securities."
            )

    # --- strategies ---
    strategies = system.get("strategies", [])
    if strategies is None:
        strategies = []

    if not isinstance(strategies, list):
        pg_logger.error("System strategies ('strategies') must be a list.")
        raise exceptions.NotExistSystemKeyException(
            message="'strategies' must be a list."
        )

    required_strategy_keys = [
        "id",
        "logic",
    ]

    for idx, strategy in enumerate(strategies):
        if not isinstance(strategy, dict):
            raise exceptions.NotExistSystemKeyException(
                message=f"strategies[{idx}] must be a dictionary."
            )

        strategy_id = strategy.get("id")
        if not strategy_id:
            raise exceptions.NotExistSystemKeyException(
                message=f"strategies[{idx}] requires a unique 'id'."
            )

        for key in required_strategy_keys:
            if key not in strategy:
                raise exceptions.NotExistSystemKeyException(
                    message=f"Strategy '{strategy_id}' is missing '{key}' key."
                )

        buy_or_sell = strategy.get("buy_or_sell", None)
        if buy_or_sell not in ("buy_new", "sell_new", None):
            raise exceptions.NotExistSystemKeyException(
                message=f"Strategy '{strategy_id}' has invalid 'buy_or_sell' value: {buy_or_sell}"
            )
