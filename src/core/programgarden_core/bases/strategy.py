"""Abstract condition scaffolding for ProgramGarden strategies.

EN:
    Define reusable TypedDict responses and base classes for extracting symbol
    candidates based on strategy-specific conditions.

KO:
    전략 전용 조건을 기반으로 종목 후보를 추출하기 위한 TypedDict 응답과
    베이스 클래스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Literal, Optional, TypeVar, TypedDict

from programgarden_core.bases.base import SymbolInfoOverseasStock, SymbolInfoOverseasFutures


SymbolInfoType = TypeVar("SymbolInfoType", SymbolInfoOverseasStock, SymbolInfoOverseasFutures)


class BaseStrategyConditionResponseCommon(TypedDict):
    """Common response fields shared across strategy conditions.

    EN:
        Supplies metadata such as symbol identifiers and success flags to help
        downstream order logic evaluate condition outcomes.

    KO:
        전략 계산 조건 응답의 공통 필드입니다. 조건 결과에 대한 성공 플래그와 종목 식별자 등 주문 로직이 활용할 메타
        데이터를 제공합니다.
    """

    condition_id: Optional[str]
    """EN: Identifier of the evaluated condition block.
    KO: 평가된 조건 블록의 식별자입니다."""

    success: bool
    """EN: ``True`` when at least one symbol passes the condition.
    KO: 최소 한 개 종목이 조건을 만족하면 ``True`` 입니다."""

    symbol: str
    """EN: Primary symbol associated with the response.
    KO: 종목 코드입니다."""

    exchcd: str
    """EN: Exchange code for the symbol.
    KO: 해당 종목의 거래소 코드입니다."""

    data: Any
    """EN: Additional payload produced by the condition implementation.
    KO: 조건 구현이 제공하는 추가 데이터입니다."""

    weight: Optional[int]
    """EN: Optional weighting factor between 0 and 1 (defaults to 0).
    KO: 0과 1 사이에서 선택적으로 설정하는 가중치입니다 (기본값 0)."""

    product: Literal["overseas_stock", "overseas_futures"]
    """EN: Product category for the response.
    KO: 응답이 속한 상품 유형입니다."""


class BaseStrategyConditionResponseOverseasStockType(BaseStrategyConditionResponseCommon):
    """Specialized response schema for overseas stock conditions.

    EN:
        Narrows the ``product`` field to ``overseas_stock`` for stricter typing.

    KO:
        ``product`` 필드를 ``overseas_stock`` 으로 제한하여 더 엄격한 타입을
        제공합니다.
    """

    product: Literal["overseas_stock"]
    """EN: Literal confirming the stock product category.
    KO: 주식 상품 유형임을 나타내는 literal 입니다."""


class BaseStrategyConditionResponseOverseasFuturesType(BaseStrategyConditionResponseCommon):
    """Specialized response schema for overseas futures conditions.

    EN:
        Adds ``position_side`` awareness needed to transition into order logic.

    KO:
        주문 단계 전환에 필요한 ``position_side`` 정보를 제공합니다.
    """

    product: Literal["overseas_futures"]
    """EN: Literal confirming the futures product category.
    KO: 선물 상품 유형임을 나타내는 literal 입니다."""

    position_side: Literal["long", "short", "flat"]
    """EN:
        Indicates directional bias for futures positions.
        - ``success`` is ``True``: ``position_side`` is meaningful.
        - ``success`` is ``False``: ``position_side`` is ignored.
        - ``success`` is ``True`` and ``position_side`` is ``flat``: treat as
          unmet and skip order submission.

    KO:
        선물 포지션의 방향성을 나타냅니다.
        - ``success`` 가 ``True`` 면 ``position_side`` 값을 사용합니다.
        - ``success`` 가 ``False`` 면 ``position_side`` 값을 무시합니다.
        - ``success`` 가 ``True`` 이지만 ``position_side`` 가 ``flat`` 이면 미충족으로
          간주하여 주문을 진행하지 않습니다.
    """


ResponseType = TypeVar(
    "ResponseType",
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType,
)


class BaseStrategyCondition(Generic[SymbolInfoType, ResponseType], ABC):
    """Abstract base class for symbol selection conditions.

    EN:
        Encapsulates reusable helpers for evaluating strategy conditions against
        single symbols.

    KO:
        단일 종목을 대상으로 전략 조건을 평가할 때 재사용 가능한 헬퍼를 제공합니다.
    """

    id: str
    """EN: Unique identifier assigned to the condition.
    KO: 조건에 부여된 고유 식별자입니다."""

    description: str
    """EN: Human-readable description of the condition logic.
    KO: 조건 로직에 대한 사람 친화적인 설명입니다."""

    securities: List[str]
    """EN: Supported brokers or exchanges.
    KO: 조건이 지원하는 증권사 또는 거래소 목록입니다."""

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize shared state for condition evaluation."""
        self.symbol: Optional[SymbolInfoType] = None

    @abstractmethod
    async def execute(self) -> 'ResponseType':
        """Evaluate the condition and return a structured response.

        EN:
            Implementations should inspect ``self.symbol`` and produce the
            appropriate response payload.

        KO:
            구현체는 ``self.symbol`` 을 참고하여 적절한 응답 페이로드를 생성해야
            합니다.

        Returns:
            ResponseType: Condition result payload consumed by order logic.
        """
        pass

    def _set_system_id(self, system_id: Optional[str]) -> None:
        """Store the system identifier orchestrating the condition.

        EN:
            Useful for logging or cross-component tracing.

        KO:
            로그 혹은 컴포넌트 간 추적에 사용할 시스템 ID를 저장합니다.

        Parameters:
            system_id (Optional[str]): Identifier passed by the runtime.
        """
        self.system_id = system_id

    def _set_symbol(self, symbol: SymbolInfoType) -> None:
        """Bind the symbol under evaluation.

        EN:
            Conditions should use this as the focal point for calculations.

        KO:
            조건 계산의 중심이 되는 종목을 설정합니다.

        Parameters:
            symbol (SymbolInfoType): Symbol metadata for evaluation.
        """
        self.symbol = symbol


class BaseStrategyConditionOverseasStock(
    BaseStrategyCondition[SymbolInfoOverseasStock, BaseStrategyConditionResponseOverseasStockType],
    ABC,
):
    """Base condition class specialized for overseas stock symbols.

    EN:
        Restricts generics to stock metadata and responses.

    KO:
        해외주식 조건 전략 기본 클래스로써, 메타데이터와 응답으로 제네릭을 제한합니다.
    """

    product_type: Literal["overseas_stock"] = "overseas_stock"
    """EN: Literal identifying the stock condition type.
    KO: 주식 조건 타입임을 나타내는 literal 입니다."""


class BaseStrategyConditionOverseasFutures(
    BaseStrategyCondition[SymbolInfoOverseasFutures, BaseStrategyConditionResponseOverseasFuturesType],
    ABC,
):
    """Base condition class specialized for overseas futures symbols.

    EN:
        Restricts generics to futures metadata and responses.

    KO:
        선물 메타데이터와 응답으로 제네릭을 제한합니다.
    """

    product_type: Literal["overseas_futures"] = "overseas_futures"
    """EN: Literal identifying the futures condition type.
    KO: 해외선물 조건 타입임을 나타내는 literal 입니다."""
