"""
핵심 기능 모듈

LS OpenAPI 클라이언트의 핵심 기능을 제공합니다.
"""

from programgarden_core.alias_resolver import normalize_system_config
from programgarden_core.bases import (
    SystemType, StrategyConditionType,
    StrategyType, SystemSettingType,
    DictConditionType,
    SecuritiesAccountType,
    DpsTyped,
    StrategySymbolInputType,

    BaseStrategyCondition,
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseCommon,
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,

    OrderType,
    OrderRealResponseType,

    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    HeldSymbol,
    HeldSymbolOverseasStock,
    HeldSymbolOverseasFutures,
    NonTradedSymbol,
    NonTradedSymbolOverseasStock,
    NonTradedSymbolOverseasFutures,

    OrderTimeType,
    OrderStrategyType,

    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,

    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasStockResponseType,
    BaseNewOrderOverseasFutures,
    BaseNewOrderOverseasFuturesResponseType,

    BaseModifyOrderOverseasStock,
    BaseModifyOrderOverseasStockResponseType,
    BaseModifyOrderOverseasFutures,
    BaseModifyOrderOverseasFutureResponseType,

    BaseCancelOrderOverseasStock,
    BaseCancelOrderOverseasStockResponseType,
    BaseCancelOrderOverseasFutures,
    BaseCancelOrderOverseasFuturesResponseType,
)
from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias
from programgarden_core import logs, exceptions
from programgarden_core.logs import pg_log_disable, pg_log_reset, pg_logger, pg_log


__all__ = [
    logs,
    exceptions,

    pg_logger,
    pg_log,
    pg_log_disable,
    pg_log_reset,

    normalize_system_config,
    require_korean_alias,
    EnforceKoreanAliasMeta,

    SecuritiesAccountType,
    StrategyConditionType,
    StrategyType,
    DictConditionType,
    SystemSettingType,
    SystemType,
    OrderStrategyType,
    DpsTyped,
    StrategySymbolInputType,

    # system 타입
    SystemType,
    StrategyType,
    SecuritiesAccountType,
    StrategyConditionType,
    DictConditionType,
    SystemSettingType,
    OrderTimeType,
    OrderType,
    OrderRealResponseType,

    # base types
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    HeldSymbol,
    HeldSymbolOverseasStock,
    HeldSymbolOverseasFutures,
    NonTradedSymbol,
    NonTradedSymbolOverseasStock,
    NonTradedSymbolOverseasFutures,
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,

    # strategy types
    BaseStrategyCondition,
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseCommon,
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,

    # new_order types
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasStockResponseType,
    BaseNewOrderOverseasFutures,
    BaseNewOrderOverseasFuturesResponseType,

    # modify_order types
    BaseModifyOrderOverseasStock,
    BaseModifyOrderOverseasStockResponseType,
    BaseModifyOrderOverseasFutures,
    BaseModifyOrderOverseasFutureResponseType,

    # cancel_order types
    BaseCancelOrderOverseasStock,
    BaseCancelOrderOverseasStockResponseType,
    BaseCancelOrderOverseasFutures,
    BaseCancelOrderOverseasFuturesResponseType,
]
