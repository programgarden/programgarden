"""Plugin discovery, resolution, and error reporting helpers for Programgarden.

EN:
        Responsible for locating strategy/order plugin classes, instantiating them
        with supplied parameters, and normalizing failure responses. The resolver
        integrates with community packages, caches lookups, and emits structured
        errors through :mod:`programgarden.pg_listener` to aid host applications.

KR:
        전략/주문 플러그인 클래스를 탐색하고, 제공된 파라미터로 인스턴스화하며, 실패
        시 일관된 응답을 생성합니다. 커뮤니티 패키지와 연동하여 조회 결과를 캐시하고
        :mod:`programgarden.pg_listener`를 통해 구조화된 오류를 전달합니다.
"""

from typing import Dict, List, Optional, Union
import inspect
from programgarden_core import (
    BaseStrategyCondition,
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionOverseasFutures,
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,
    plugin_logger,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType,
    exceptions, HeldSymbol,
    NonTradedSymbol, OrderStrategyType,
    DpsTyped,
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
    BaseModifyOrderOverseasFuturesResponseType,
    BaseCancelOrderOverseasFuturesResponseType,
)
from programgarden.pg_listener import pg_listener
try:
    from programgarden_community import getCommunityCondition  # type: ignore[import]
except ImportError:
    def getCommunityCondition(_condition_id):
        """Fallback when community package is unavailable (EN/KR).

        EN:
            Returns ``None`` to signal the resolver to continue searching built-in
            targets.

        KR:
            기본 내장 플러그인 탐색을 계속 진행하도록 ``None``을 반환합니다.
        """

        return None


class PluginResolver:
    """Resolve and cache plugin classes by identifier.

    EN:
        Maintains a lookup cache for strategy and order plugins, records previously
        reported failures to avoid duplicate noise, and exposes helpers to execute
        both built-in and community-provided plugins.

    KR:
        전략/주문 플러그인의 조회 캐시를 유지하고, 중복 오류 로그를 줄이기 위해 보고된
        실패를 기록하며, 내장/커뮤니티 플러그인 모두를 실행하는 헬퍼를 제공합니다.

    Attributes:
        _plugin_cache (Dict[str, type]):
            EN: Caches resolved plugin classes by identifier.
            KR: 식별자별로 해석된 플러그인 클래스를 저장합니다.
        _reported_condition_errors (set[str]):
            EN: Tracks condition errors already reported to avoid duplication.
            KR: 중복 보고를 피하기 위해 이미 보고한 조건 오류를 추적합니다.
        _reported_order_errors (set[str]):
            EN: Tracks order plugin errors already emitted.
            KR: 이미 전송한 주문 플러그인 오류를 기록합니다.
    """

    def __init__(self):
        self._plugin_cache: Dict[str, type] = {}
        self._reported_condition_errors: set[str] = set()
        self._reported_order_errors: set[str] = set()

    def reset_error_tracking(self) -> None:
        """Reset state so previously reported errors can fire again.

        EN:
            Clears both error-tracking sets to allow duplicate reports on subsequent
            system executions.

        KR:
            두 에러 추적 세트를 초기화하여 다음 시스템 실행에서 동일 오류도 다시 보고될
            수 있도록 합니다.
        """
        self._reported_condition_errors.clear()
        self._reported_order_errors.clear()

    def _build_failure_response(
        self,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
        condition_id: Optional[str],
    ) -> Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
        """Create a failure response shaped like a plugin execution result.

        EN:
            Converts symbol metadata into a failure payload consumed by downstream
            listeners so they can gracefully handle plugin errors.

        KR:
            심볼 메타데이터를 플러그인 실패 페이로드로 변환하여 다운스트림 리스너가
            오류를 우아하게 처리할 수 있도록 합니다.
        """
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
        """Find a plugin class by identifier and cache the result.

        EN:
            Accepts short names or fully-qualified paths. Community plugins are
            queried first, followed by built-in lookups. Successful resolutions are
            cached for reuse.

        KR:
            짧은 이름 또는 전체 경로 모두를 받아 커뮤니티 플러그인을 우선 탐색하고,
            실패 시 내장 플러그인을 찾습니다. 성공 시 결과를 캐시에 저장합니다.

        Args:
            condition_id (str):
                EN: Plugin identifier supplied in strategy/order definitions.
                KR: 전략/주문 정의에서 제공된 플러그인 식별자입니다.

        Returns:
            Optional[type]:
                EN: Resolved class when available; ``None`` if lookup fails.
                KR: 해석된 클래스 또는 실패 시 ``None``.
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
            plugin_logger.debug(f"programgarden_community에서 '{condition_id}' 클래스를 찾는 중 오류 발생: {exc}")

        return None

    async def resolve_buysell_community(
        self,
        system_id: Optional[str],
        trade: OrderStrategyType,
        available_symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = [],
        held_symbols: List[HeldSymbol] = [],
        non_trade_symbols: List[NonTradedSymbol] = [],
        dps: Optional[List[DpsTyped]] = None
    ) -> tuple[
        Optional[
            Union[
                List[BaseNewOrderOverseasStockResponseType],
                List[BaseModifyOrderOverseasStockResponseType],
                List[BaseCancelOrderOverseasStockResponseType],
                List[BaseNewOrderOverseasFuturesResponseType],
                List[BaseModifyOrderOverseasFuturesResponseType],
                List[BaseCancelOrderOverseasFuturesResponseType],
            ]
        ],
        Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFutures]]
            ]:
        """Resolve and run a buy/sell plugin declared in the trade payload.

        EN:
            Supports both direct class instances and identifier-based plugins. Hook
            points (`_set_available_symbols`, etc.) are invoked when present to
            hydrate the plugin with runtime context.

        KR:
            트레이드 페이로드에 선언된 직접 인스턴스와 식별자 기반 플러그인을 모두
            지원합니다. 실행 전 `_set_available_symbols` 등 훅을 호출해 런타임 컨텍스트를
            주입합니다.

        Args:
            system_id (Optional[str]):
                EN: Identifier of the running system, passed to plugins that expect it.
                KR: 시스템 식별자로, 필요한 플러그인에 전달됩니다.
            trade (OrderStrategyType):
                EN: Order block containing the plugin declaration.
                KR: 플러그인 선언을 포함하는 주문 블록입니다.
            available_symbols (...):
                EN/KR: 종목 목록 컨텍스트 (조건 결과, 보유 종목, 미체결 종목 등).
            dps (Optional[List[DpsTyped]]):
                EN: Account balance data for plugins needing buying power info.
                KR: 매매 가능 잔고 정보를 요구하는 플러그인을 위한 계좌 잔고 데이터입니다.

        Returns:
            tuple[Optional[List[...]], Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFutures]]]:
                EN: Tuple containing plugin execution result list and the plugin
                instance (if resolved).
                KR: 실행 결과 리스트와 플러그인 인스턴스를 포함한 튜플입니다.
        """

        condition = trade.get("condition", {})
        if isinstance(condition, (BaseOrderOverseasStock, BaseOrderOverseasFutures)):

            if hasattr(condition, "_set_available_symbols"):
                condition._set_available_symbols(available_symbols)
            if hasattr(condition, "_set_held_symbols"):
                condition._set_held_symbols(held_symbols)
            if hasattr(condition, "_set_system_id") and system_id:
                condition._set_system_id(system_id)
            if hasattr(condition, "_set_non_traded_symbols"):
                condition._set_non_traded_symbols(non_trade_symbols)
            if hasattr(condition, "_set_available_balance") and dps:
                condition._set_available_balance(
                    dps=dps
                )

            result = await condition.execute()
            return result, condition

        ident = condition.get("condition_id")
        params = condition.get("params", {}) or {}

        cls = await self._resolve(ident)

        if cls is None:
            plugin_logger.error(f"{ident}: 조건 클래스를 찾을 수 없습니다")
            raise exceptions.NotExistConditionException(
                message=f"Condition class '{ident}' not found"
            )

        try:
            community_instance = cls(**params)
            # If plugin supports receiving the current symbol list, provide it.
            if hasattr(community_instance, "_set_available_symbols"):
                community_instance._set_available_symbols(available_symbols)
            if hasattr(community_instance, "_set_held_symbols"):
                community_instance._set_held_symbols(held_symbols)
            if hasattr(community_instance, "_set_system_id") and system_id:
                community_instance._set_system_id(system_id)
            if hasattr(community_instance, "_set_non_traded_symbols"):
                community_instance._set_non_traded_symbols(non_trade_symbols)
            if hasattr(community_instance, "_set_available_balance") and dps:
                community_instance._set_available_balance(
                    dps=dps
                )

            if not isinstance(community_instance, (BaseOrderOverseasStock, BaseOrderOverseasFutures)):
                plugin_logger.error(
                    f"{ident}: 주문 플러그인 타입이 올바르지 않습니다"
                )
                raise TypeError(f"{__class__.__name__}: Condition class '{ident}' is not a subclass of BaseOrderOverseasStock/BaseOrderOverseasFutures")

            # Plugins expose an async `execute` method that returns the symbols to act on.
            plugin_logger.debug(
                f"{ident}: 매매 플러그인을 실행합니다 (입력 종목 {len(available_symbols or [])}개)"
            )
            result = await community_instance.execute()
            plugin_logger.debug(
                f"{ident}: 플러그인이 {len(result or []) if result else 0}개 종목을 반환했습니다"
            )

            return result, community_instance

        except Exception as exc:
            # Log the full traceback to aid external developers debugging plugin errors.
            plugin_logger.exception(f"{ident}: 매매 플러그인 실행 중 오류가 발생했습니다")
            if ident not in self._reported_order_errors:
                order_exc = exceptions.OrderExecutionException(
                    message=f"주문 플러그인 '{ident}' 실행 중 오류가 발생했습니다.",
                    data={
                        "condition_id": ident,
                        "system_id": system_id,
                        "details": str(exc),
                    },
                )
                pg_listener.emit_exception(order_exc)
                self._reported_order_errors.add(ident)
            return None, None

    async def resolve_condition(
        self,
        system_id: Optional[str],
        condition_id: str,
        params: Dict,
        symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures],
    ) -> Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
        """Execute a condition plugin for a single symbol.

        EN:
            Resolves the plugin, injects symbol/system context via optional hooks,
            and returns the plugin's response. Failures trigger error emission and a
            normalized failure payload.

        KR:
            플러그인을 해석한 뒤 선택적 훅을 통해 심볼/시스템 컨텍스트를 주입하고,
            플러그인의 응답을 반환합니다. 실행 실패 시 오류를 전송하고 표준화된 실패
            페이로드를 반환합니다.
        """
        cls = await self._resolve(condition_id)

        if cls is None:
            plugin_logger.error(f"{condition_id}: 조건 클래스를 찾을 수 없습니다")
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
                plugin_logger.error(
                    f"{condition_id}: BaseStrategyCondition을 상속하지 않은 클래스입니다"
                )
                raise exceptions.NotExistConditionException(
                    message=f"Condition class '{condition_id}' is not a subclass of BaseStrategyCondition"
                )
            plugin_logger.debug(
                f"{condition_id}: 전략 조건을 실행합니다."
            )
            result = await instance.execute()

            return result

        except exceptions.NotExistConditionException as e:
            plugin_logger.error(f"{condition_id}: 조건이 존재하지 않습니다 -> {e}")
            if condition_id not in self._reported_condition_errors:
                pg_listener.emit_exception(
                    e,
                    data={
                        "condition_id": condition_id,
                        "system_id": system_id,
                    },
                )
                self._reported_condition_errors.add(condition_id)

            return self._build_failure_response(symbol_info, condition_id)

        except Exception as exc:
            plugin_logger.exception(f"{condition_id}: 조건 실행 중 처리되지 않은 오류가 발생했습니다")
            if condition_id not in self._reported_condition_errors:
                cond_exc = exceptions.ConditionExecutionException(
                    message=f"조건 '{condition_id}' 실행 중 오류가 발생했습니다.",
                    data={
                        "condition_id": condition_id,
                        "system_id": system_id,
                        "details": str(exc),
                    },
                )
                pg_listener.emit_exception(cond_exc)
                self._reported_condition_errors.add(condition_id)
            return self._build_failure_response(symbol_info, condition_id)

    async def get_order_types(self, condition_id: str) -> Optional[List[OrderType]]:
        """Retrieve declared ``order_types`` attribute from a plugin.

        EN:
            Returns ``None`` when the plugin lacks the attribute or the lookup
            fails, enabling callers to fall back gracefully.

        KR:
            속성이 없거나 조회에 실패하면 ``None``을 반환하여 호출자가 우아하게 대처할 수
            있도록 합니다.
        """
        cls = await self._resolve(condition_id)
        if cls and hasattr(cls, 'order_types'):
            return cls.order_types
        return None
