"""Strategy condition evaluation utilities for Programgarden.

EN:
        Exposes the :class:`ConditionExecutor`, a coordination layer responsible for
        running plugin-based conditions, evaluating nested logical groups, and
        filtering symbol universes according to a strategy definition. The module
        integrates tightly with :class:`PluginResolver` to instantiate condition
        plugins and :class:`SymbolProvider` to resolve symbol lists when strategies
        rely on dynamic discovery.

        Key capabilities include:
        - Resolving and executing plugin-driven conditions with consistent payloads.
        - Evaluating nested condition trees concurrently using a DSL of logical
            operators (``and``/``or``/``xor``/``not``/``at_least``/``weighted`` ...).
        - Generating condition responses enriched with weights, position sides, and
            error telemetry for downstream listeners.

KR:
        플러그인 기반 조건 실행, 중첩된 논리 그룹 평가, 전략 정의에 따른 종목 필터링을
        담당하는 조정 레이어 :class:`ConditionExecutor`를 제공합니다. 전략이 동적 종목
        조회에 의존하는 경우 :class:`PluginResolver`와 :class:`SymbolProvider`를 활용해
        조건 플러그인을 인스턴스화하고 종목 목록을 수집합니다.

        주요 기능은 다음과 같습니다:
        - 일관된 페이로드를 유지하며 플러그인 기반 조건을 해석하고 실행합니다.
        - ``and``/``or``/``xor``/``not``/``at_least``/``weighted`` 등 DSL 논리 연산자를
            사용해 중첩 조건 트리를 병렬로 평가합니다.
        - 가중치, 포지션 방향, 오류 텔레메트리를 포함한 조건 응답을 생성하여
            다운스트림 리스너로 전달합니다.
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Set
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


# EN: Mapping of user-friendly exchange aliases to LS market codes.
# KR: 사용자가 이해하기 쉬운 거래소 별칭을 LS 시장 코드로 매핑한 사전입니다.
EXCHANGE_CODE_ALIASES: Dict[str, str] = {
    "81": "81",
    "nyse": "81",
    "amex": "81",
    "82": "82",
    "nasdaq": "82",
}


class ConditionExecutor:
    """Coordinate the execution and aggregation of strategy conditions.

    EN:
        Acts as the central hub for condition evaluation. Individual condition
        entries—whether concrete subclasses of
        :class:`programgarden_core.BaseStrategyCondition` or plugin definitions
        resolved via :class:`PluginResolver`—are executed in parallel, and their
        results are combined according to logical policies expressed in
        strategy metadata. When a strategy omits explicit symbol lists, the
        executor depends on :class:`SymbolProvider` to source market, account,
        and pending-order symbols.

    KR:
        전략 조건 평가를 총괄하는 허브 역할을 합니다. 각 조건 항목은
        :class:`programgarden_core.BaseStrategyCondition`의 구체 서브클래스거나
        :class:`PluginResolver`를 통해 해석된 플러그인 정의일 수 있으며, 병렬로
        실행한 뒤 전략 메타데이터에 정의된 논리 정책에 따라 결합합니다. 전략이
        명시적인 종목 리스트를 제공하지 않는 경우 :class:`SymbolProvider`를 이용해
        시장/보유/미체결 종목을 수집합니다.

    Attributes:
        resolver (PluginResolver):
            EN: Dependency used to resolve condition identifiers into concrete
            callables or classes.
            KR: 조건 식별자를 구체적인 호출 가능 객체나 클래스로 해석하는
            의존성입니다.
        symbol_provider (SymbolProvider):
            EN: Adapter that fetches symbol universes (market, account,
            non-traded) when strategies rely on discovery.
            KR: 전략이 동적 조회에 의존할 때 시장/보유/미체결 종목을 가져오는
            어댑터입니다.
        state_lock (asyncio.Lock):
            EN: Placeholder lock to support future stateful extensions while
            keeping current operations lock-free.
            KR: 현재 구현은 락이 필요 없지만, 향후 상태 기반 확장을 지원하기 위한
            예약 락입니다.
    """

    def __init__(self, resolver: PluginResolver, symbol_provider: SymbolProvider):
        """Initialize executor dependencies and concurrency primitives.

        EN:
            Stores the supplied resolver/provider and prepares a reusable
            :class:`asyncio.Lock` for future shared-state scenarios.

        KR:
            전달된 리졸버와 프로바이더를 저장하고, 향후 공유 상태 처리에 사용할 수
            있도록 :class:`asyncio.Lock`을 준비합니다.

        Args:
            resolver (PluginResolver):
                EN: Resolver that maps `condition_id` strings to executable
                condition classes or instances.
                KR: `condition_id` 문자열을 실행 가능한 조건 클래스로 변환하는
                리졸버입니다.
            symbol_provider (SymbolProvider):
                EN: Symbol source used when strategies omit explicit symbol
                lists.
                KR: 전략이 명시적인 종목 목록을 제공하지 않을 때 사용하는 종목
                공급자입니다.

        Returns:
            None:
                EN: Constructor performs setup side effects only.
                KR: 생성자는 설정 작업만 수행하며 값을 반환하지 않습니다.
        """
        self.resolver = resolver
        self.symbol_provider = symbol_provider
        self.state_lock = asyncio.Lock()

    def _normalize_exchange_code(self, exchange: Any) -> str:
        """Map human-friendly exchange aliases to LS market codes.

        EN:
            Accepts free-form exchange identifiers (e.g., ``"NYSE"``) and
            resolves them to LS OpenAPI market codes using
            ``EXCHANGE_CODE_ALIASES``. Non-string values are coerced into
            strings without additional validation.

        KR:
            자유 형식의 거래소 식별자(예: ``"NYSE"``)를 받아
            ``EXCHANGE_CODE_ALIASES`` 매핑을 통해 LS OpenAPI 시장 코드로 변환합니다.
            문자열이 아닌 값은 추가 검증 없이 문자열로 변환합니다.

        Args:
            exchange (Any):
                EN: User-provided exchange identifier or alias.
                KR: 사용자가 입력한 거래소 식별자 또는 별칭입니다.

        Returns:
            str:
                EN: Normalized LS market code or the original value as string
                when no alias matches.
                KR: 매핑된 LS 시장 코드 또는 매핑이 없을 때 원본 값을 문자열로
                반환합니다.
        """

        if isinstance(exchange, str):
            normalized = exchange.strip()
            if not normalized:
                return normalized

            alias = normalized.lower()
            return EXCHANGE_CODE_ALIASES.get(alias, normalized)

        return str(exchange)

    def _symbol_label(self, symbol_info: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]) -> str:
        """Generate a display label for a symbol payload.

        EN:
            Prefers dictionary-style payloads and composes an
            ``EXCHANGE:SYMBOL`` label using known keys. Falls back to
            ``str(symbol_info)`` for non-mapping objects.

        KR:
            딕셔너리 형태 페이로드를 우선 사용해 ``거래소:종목`` 형식의 라벨을
            조합하고, 매핑이 아닌 객체는 ``str(symbol_info)`` 결과를 반환합니다.

        Args:
            symbol_info (Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]):
                EN: Symbol metadata dictionary or domain object.
                KR: 종목 메타데이터 딕셔너리 또는 도메인 객체입니다.

        Returns:
            str:
                EN: Human-readable label identifying the symbol.
                KR: 종목을 식별하는 사람이 읽기 쉬운 라벨입니다.
        """
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
        """Normalize user-supplied symbol structures for downstream execution.

        EN:
            Ensures each symbol dictionary carries the runtime fields expected
            by order and condition plugins (e.g., ``product_type``,
            ``position_side`` for futures). Alias keys such as ``exchange`` or
            ``name`` are mapped to canonical keys.

        KR:
            사용자 관심 종목 딕셔너리가 주문 및 조건 플러그인이 기대하는 런타임
            필드(예: ``product_type``, 해외선물의 ``position_side`` 등)를 포함하도록
            정규화합니다. ``exchange``/``name``과 같은 별칭 키는 표준 키로 매핑합니다.

        Args:
            symbols (Optional[List[StrategySymbolInputType]]):
                EN: Raw symbol inputs provided in the strategy configuration.
                KR: 전략 설정에서 제공된 원시 종목 입력 목록입니다.
            product (Optional[str]):
                EN: Target product type hint (``"overseas_stock"`` or
                ``"overseas_futures"``), used to set default fields.
                KR: 기본 필드 설정에 사용되는 대상 상품 타입 힌트입니다
                (``"overseas_stock"`` 또는 ``"overseas_futures"``).

        Returns:
            List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
                EN: Normalized symbol payloads enriched with consistent
                metadata.
                KR: 일관된 메타데이터가 추가된 정규화된 종목 페이로드 목록입니다.
        """

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
        """Produce a human-readable identifier for logging.

        EN:
            Extracts ``condition_id`` or ``logic`` metadata when the condition
            is a mapping; otherwise derives the identifier from object
            attributes for informative diagnostics.

        KR:
            조건이 딕셔너리일 때 ``condition_id`` 또는 ``logic`` 메타데이터를 추출하고,
            객체일 경우 속성 기반 식별자를 생성해 로깅 정보를 풍부하게 합니다.

        Args:
            condition (StrategyConditionType):
                EN: Condition object or dictionary as defined in strategy
                configuration.
                KR: 전략 설정에 정의된 조건 객체 또는 딕셔너리입니다.

        Returns:
            str:
                EN: Identifier suitable for trace logs.
                KR: 추적 로그에 적합한 식별자 문자열입니다.
        """
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
        """Evaluate condition responses with logical policies and futures alignment.

        EN:
            Applies the requested logical operator to the list of condition
            responses, optionally incorporating thresholds or aggregated
            weights. Futures conditions must agree on a non-flat
            ``position_side`` for the evaluation to succeed.

        KR:
            조건 응답 목록에 지정된 논리 연산자를 적용하고, 필요 시 임계값 또는
            가중치를 반영합니다. 해외선물 조건은 비중립 ``position_side``를 공유해야
            성공으로 간주됩니다.

        Args:
            results (List[Union[...]]):
                EN: Condition response payloads to aggregate.
                KR: 집계할 조건 응답 페이로드 목록입니다.
            logic (str):
                EN: Logical operator keyword (``and``, ``or``, ``xor``,
                ``weighted`` 등).
                KR: 논리 연산자 키워드(``and``, ``or``, ``xor``, ``weighted`` 등).
            threshold (Optional[int]):
                EN: Auxiliary threshold used by operators such as
                ``at_least``/``at_most``/``exactly``/``weighted``.
                KR: ``at_least``/``at_most``/``exactly``/``weighted`` 등에서 사용하는
                보조 임계값입니다.

        Returns:
            Tuple[bool, int, Optional[str]]:
                EN: A triple of ``(is_success, aggregated_weight,
                aligned_position_side)`` suitable for downstream evaluation.
                KR: 후속 평가에 사용할 ``(성공 여부, 집계 가중치, 정렬된 포지션 방향)``
                튜플입니다.

        Raises:
            ValueError:
                EN: Raised when an operator requiring a threshold is invoked
                without providing one.
                KR: 임계값이 필요한 연산자를 임계값 없이 호출할 경우 발생합니다.
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
        data: Any = None,
        position_side: Optional[str] = None,
    ) -> Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
        """Create a normalized condition response payload for stocks or futures.

        EN:
            Produces a dict matching Programgarden Core response schemas while
            enforcing default product metadata and futures position semantics.

        KR:
            Programgarden Core 응답 스키마에 맞는 딕셔너리를 생성하며, 상품 메타데이터와
            해외선물 포지션 규칙을 일관되게 적용합니다.

        Args:
            symbol_info (Union[...]):
                EN: Symbol metadata dict used to populate symbol/exchange fields.
                KR: 심볼/거래소 필드를 채우는 데 사용되는 종목 메타데이터입니다.
            success (bool):
                EN: Indicates whether the condition passed.
                KR: 조건 통과 여부를 나타냅니다.
            condition_id (Optional[str]):
                EN: Identifier of the condition that produced the response.
                KR: 응답을 생성한 조건 식별자입니다.
            weight (int):
                EN: Accumulated weight contribution for weighted logic.
                KR: 가중치 기반 로직에 사용되는 누적 가중치입니다.
            data (Optional[Any]):
                EN: Arbitrary plugin-specific payload to surface downstream.
                KR: 다운스트림에 전달할 플러그인 전용 페이로드입니다.
            position_side (Optional[str]):
                EN: Futures direction hint (``long``/``short``/``flat``).
                KR: 해외선물 방향 정보(``long``/``short``/``flat``)입니다.

        Returns:
            Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
                EN: Structured response dictionary tagged with the appropriate
                product type.
                KR: 상품 타입이 태깅된 구조화된 응답 딕셔너리입니다.
        """
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
        """Execute a single condition entry in its applicable form.

        EN:
            Supports strategy conditions represented either as concrete
            :class:`BaseStrategyCondition` subclasses, plugin dictionaries, or
            nested logical groups. Handles symbol and system metadata injection
            prior to execution.

        KR:
            :class:`BaseStrategyCondition` 서브클래스, 플러그인 딕셔너리, 중첩 논리
            그룹 형태로 표현된 전략 조건을 지원하며, 실행 전 필요한 종목/시스템
            메타데이터를 주입합니다.

        Args:
            system (SystemType):
                EN: Full system configuration containing settings/system_id.
                KR: settings/system_id를 포함한 전체 시스템 구성입니다.
            symbol_info (Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]):
                EN: Symbol payload currently under evaluation.
                KR: 평가 중인 종목 페이로드입니다.
            condition (Union[...]):
                EN: Condition definition or object to execute.
                KR: 실행할 조건 정의 또는 객체입니다.

        Returns:
            Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
                EN: Normalized condition response emitted by the condition or
                synthesized on failure.
                KR: 조건 실행 결과 또는 실패 시 생성된 정규화된 조건 응답입니다.

        Raises:
            ConditionExecutionException:
                EN: Propagated indirectly when nested conditions fault during
                evaluation.
                KR: 중첩 조건 평가 중 오류가 발생하면 간접적으로 전파됩니다.
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
        """Execute a plugin condition using the resolver infrastructure.

        EN:
            Delegates to :meth:`PluginResolver.resolve_condition`, passing
            system, symbol, and parameter context, then logs outcomes and emits
            structured responses.

        KR:
            시스템/종목/파라미터 컨텍스트를 전달하여
            :meth:`PluginResolver.resolve_condition`에 위임하고, 결과를 로깅하며
            구조화된 응답을 반환합니다.

        Args:
            system_id (Optional[str]):
                EN: Identifier of the running system for plugin context.
                KR: 플러그인 컨텍스트에 전달할 시스템 식별자입니다.
            condition (Dict):
                EN: Plugin configuration dictionary containing ``condition_id``
                and optional ``params``.
                KR: ``condition_id``와 선택적 ``params``를 포함한 플러그인 구성
                딕셔너리입니다.
            symbol_info (Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]):
                EN: Symbol under evaluation.
                KR: 평가 대상 종목입니다.

        Returns:
            Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
                EN: Result returned by the plugin with standardized keys.
                KR: 표준화된 키를 포함한 플러그인 실행 결과입니다.
        """
        condition_id = condition.get("condition_id")
        params = condition.get("params", {}) or {}
        configured_weight = condition.get("weight", None)

        result = await self.resolver.resolve_condition(
            system_id=system_id,
            condition_id=condition_id,
            params=params,
            symbol_info=symbol_info,
        )

        if configured_weight is not None:
            result["weight"] = configured_weight

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
        """Execute a nested condition group using concurrent evaluation.

        EN:
            Spawns child tasks for each sub-condition, aggregates their results
            via :meth:`evaluate_logic`, and emits structured responses while
            reporting failures through the listener.

        KR:
            각 하위 조건에 대한 태스크를 생성해 병렬로 실행하고,
            :meth:`evaluate_logic`을 통해 결과를 집계하며, 실패 시 리스너를 통해
            알림을 전송하면서 구조화된 응답을 반환합니다.

        Args:
            system (SystemType):
                EN: Running system configuration for plugin resolution.
                KR: 플러그인 해석에 필요한 실행 중 시스템 구성입니다.
            symbol_info (Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]):
                EN: Symbol context shared by the nested conditions.
                KR: 중첩 조건이 공유하는 종목 컨텍스트입니다.
            condition_nested (StrategyConditionType):
                EN: Dictionary describing the logical group (contains
                ``conditions``/``logic``/``threshold`` keys).
                KR: ``conditions``/``logic``/``threshold`` 키를 포함하는 논리 그룹
                딕셔너리입니다.

        Returns:
            Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]:
                EN: Group-level response indicating success, weight, and
                futures direction when applicable.
                KR: 그룹 전체의 성공 여부, 가중치, (필요 시) 선물 방향을 담은 응답입니다.

        Raises:
            ConditionExecutionException:
                EN: Emitted and logged when a child condition fails during
                execution; also forwarded to listeners.
                KR: 하위 조건 실행 중 오류가 발생하면 발생 및 로깅되며, 리스너로도
                전파됩니다.
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
        """Evaluate all conditions associated with a strategy over candidate symbols.

        EN:
            Collects user-defined, market, account, and pending-order symbols;
            filters them based on strategy configuration; executes each
            condition concurrently; and returns the subset that satisfied the
            strategy logic.

        KR:
            사용자 정의, 시장, 보유, 미체결 종목을 수집하고 전략 설정에 따라 필터링한
            뒤, 각 조건을 병렬로 실행하여 전략 로직을 통과한 종목만 반환합니다.

        Args:
            system (SystemType):
                EN: Complete system definition containing securities and orders.
                KR: 증권/주문 정보를 포함한 전체 시스템 정의입니다.
            strategy (StrategyType):
                EN: Strategy configuration describing conditions, symbols, and
                evaluation policies.
                KR: 조건, 종목, 평가 정책을 설명하는 전략 구성입니다.

        Returns:
            List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
                EN: Symbols that passed the evaluated strategy conditions.
                KR: 전략 조건을 통과한 종목 목록입니다.
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

        def _symbol_identity(symbol: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]) -> str:
            if isinstance(symbol, dict):
                exch = symbol.get("exchange", "") or symbol.get("exchcd", "")
                sym = symbol.get("symbol", "")
                return f"{exch}:{sym}"
            return str(symbol)

        order_types = []
        if order_id is not None:
            order_types = await self._get_order_types(order_id, orders)

        # EN: Symbol pools partitioned into market candidates, account holdings, and non-traded orders.
        # KR: 시장 후보, 보유 잔고, 미체결 주문으로 분리된 심볼 풀입니다.
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

        # 관심종목인 것 확인
        watchlist_ids: Set[str] = set()
        for symbol in my_symbols:
            ident = _symbol_identity(symbol)
            if ident:
                watchlist_ids.add(ident)

        # EN: Final list of symbols scheduled for condition evaluation.
        # KR: 조건 평가 대상으로 확정된 종목 목록입니다.
        responsible_symbols: List[SymbolInfoOverseasStock | SymbolInfoOverseasFutures] = []
        added_symbol_ids: Set[str] = set()

        def _append_if_watchlisted(symbol: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]):
            ident = _symbol_identity(symbol)
            if not ident:
                return
            if ident not in watchlist_ids:
                return
            if ident in added_symbol_ids:
                return
            responsible_symbols.append(symbol)
            added_symbol_ids.add(ident)

        # 미체결 정정/취소 주문에서는 관심종목에 있는 경우만 계산하도록 한다.
        for non_symbol in non_account_symbols:
            ident = _symbol_identity(non_symbol)
            if not ident or ident in added_symbol_ids:
                continue
            responsible_symbols.append(non_symbol)
            added_symbol_ids.add(ident)

        # 보유 잔고 판매 주문에서는 관심종목에 있는 경우만 계산하도록 한다.
        for account_symbol in account_symbols:
            ident = _symbol_identity(account_symbol)
            if not ident or ident in added_symbol_ids:
                continue
            responsible_symbols.append(account_symbol)
            added_symbol_ids.add(ident)

        # 시장 종목들 주문에서는 관심종목에 있는 경우만 계산하도록 만든다.
        for market_symbol in market_symbols:
            _append_if_watchlisted(market_symbol)

        # 관심종목은 항상 평가 대상에 포함하되, 이미 추가된 종목은 중복 제거한다.
        for symbol in my_symbols:
            ident = _symbol_identity(symbol)
            if not ident or ident in added_symbol_ids:
                continue
            responsible_symbols.append(symbol)
            added_symbol_ids.add(ident)

        # EN: Strategy-specific hard cap settings guiding how many symbols to evaluate and ordering preference.
        # KR: 평가 수량과 정렬 우선순위를 제어하는 전략별 상한 설정입니다.
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
        """Retrieve order type declarations for the given order identifier.

        EN:
            Searches the system-wide order list for a matching ``order_id`` and
            resolves the order types by inspecting either concrete
            order-plugins or condition metadata.

        KR:
            시스템 전체 주문 목록에서 ``order_id``가 일치하는 항목을 찾아, 구체적인
            주문 플러그인 또는 조건 메타데이터를 통해 주문 타입을 해석합니다.

        Args:
            order_id (str):
                EN: Identifier assigned to the order in the system config.
                KR: 시스템 구성에서 주문에 할당된 식별자입니다.
            orders (list[OrderStrategyType]):
                EN: Collection of order specifications defined in the system.
                KR: 시스템에 정의된 주문 명세 모음입니다.

        Returns:
            Optional[List[OrderType]]:
                EN: Declared order type list (``new_buy``/``cancel_sell`` etc.)
                or ``None`` when unresolved.
                KR: 선언된 주문 타입 목록(``new_buy``/``cancel_sell`` 등) 또는
                찾을 수 없을 때 ``None``입니다.
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
