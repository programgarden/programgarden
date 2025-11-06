"""TypedDict definitions describing system configuration contracts.

EN:
    Provide strongly-typed data structures for ProgramGarden system, strategy,
    and order configuration files.

KO:
    ProgramGarden 시스템, 전략, 주문 구성 파일을 위한 강타입 데이터 구조를
    제공합니다.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from typing_extensions import NotRequired

from programgarden_core.bases.modify_orders import (
    BaseModifyOrderOverseasStock,
    BaseModifyOrderOverseasFutures,
)
from programgarden_core.bases.new_orders import (
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasFutures,
)
from programgarden_core.bases.cancel_orders import (
    BaseCancelOrderOverseasStock,
    BaseCancelOrderOverseasFutures,
)
from programgarden_core.bases.strategy import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionOverseasFutures,
)


LogicType = Literal["all", "any", "not", "xor", "at_least", "at_most", "exactly", "if_then", "weighted"]
"""EN:
    Logical reducers supported by ProgramGarden strategy conditions.
    - ``all``: All conditions must pass (logical AND).
    - ``any``: At least one condition must pass (logical OR).
    - ``not``: Condition must fail (logical NOT).
    - ``xor``: Exactly one condition must pass (exclusive OR).
    - ``at_least``: At least ``N`` conditions must pass.
    - ``at_most``: At most ``N`` conditions may pass.
    - ``exactly``: Exactly ``N`` conditions must pass.
    - ``if_then``: Conditional logic (if-then semantics).
    - ``weighted``: Weight-based scoring system.

KO:
    ProgramGarden 전략 조건이 지원하는 논리 연산자입니다.
    - ``all``: 모든 조건을 만족해야 합니다 (AND).
    - ``any``: 하나 이상의 조건만 만족하면 됩니다 (OR).
    - ``not``: 조건이 만족되지 않아야 합니다 (NOT).
    - ``xor``: 정확히 하나의 조건만 만족해야 합니다 (XOR).
    - ``at_least``: 최소 ``N`` 개의 조건이 만족해야 합니다.
    - ``at_most``: 최대 ``N`` 개의 조건만 만족할 수 있습니다.
    - ``exactly``: 정확히 ``N`` 개의 조건이 만족해야 합니다.
    - ``if_then``: if-then 형태의 조건부 논리입니다.
    - ``weighted``: 가중치 기반 점수 시스템입니다.
"""


class StrategyConditionType(TypedDict):
    """Nested condition definitions for strategy configuration.

    EN:
        Describes condition trees composed of both primitive and class-based
        conditions.

    KO:
        기본 조건과 클래스 기반 조건으로 구성된 조건 트리를 설명합니다.
    """

    id: str
    """EN: Unique identifier for the condition node.
    KO: 조건 노드의 고유 식별자입니다."""

    description: NotRequired[str]
    """EN: Human-readable description of the condition.
    KO: 조건 로직에 대한 설명입니다."""

    logic: LogicType
    """EN: Logical reducer applied to child conditions.
    KO: 하위 조건에 적용되는 논리 연산자입니다."""

    threshold: NotRequired[int]
    """EN: Numeric threshold used by reducers such as ``at_least``.
    KO: ``at_least`` 등에서 사용하는 수치 임계값입니다."""

    conditions: List[Union[
        'StrategyConditionType',
        BaseStrategyConditionOverseasStock,
        BaseStrategyConditionOverseasFutures,
    ]]
    """EN: Child conditions to evaluate.
    KO: 평가할 하위 조건 목록입니다."""


class MaxSymbolsLimitType(TypedDict):
    """Constraints for limiting the number of selected symbols.

    EN:
        Control how many symbols are processed and how they are ordered.

    KO:
        처리할 종목 수와 정렬 방식을 제어합니다.
    """

    order: Literal["random", "mcap"]
    """EN: Selection mode (``random`` or ``mcap`` for market cap ranking).
    KO: 선택 모드 (``random`` 또는 시가총액 순 정렬 ``mcap``)."""

    limit: int
    """EN: Maximum number of symbols to retain.
    KO: 유지할 최대 종목 수입니다."""


class StrategySymbolInputType(TypedDict, total=False):
    """Symbol metadata provided by configuration authors.

    EN:
        Represents minimal symbol info used to bootstrap strategy inputs.

    KO:
        전략 입력을 초기화할 때 사용하는 최소 종목 정보를 나타냅니다.
    """

    symbol: str
    """EN: Symbol code recognized by the broker.
    KO: 브로커가 인식하는 종목 코드입니다."""

    exchange: str
    """EN: Exchange or market code (e.g., ``CME``, ``81``).
    KO: 거래소/시장 코드입니다 (예: ``CME``, ``81``)."""

    name: NotRequired[str]
    """EN: Optional display-friendly name.
    KO: 선택적 표기용 종목명입니다."""


class StrategyType(TypedDict):
    """Complete strategy configuration describing schedules and conditions.

    EN:
        Combines scheduling metadata, symbol lists, logical reducers, and the
        order identifiers that should fire upon success.

    KO:
        스케줄, 종목 목록, 논리 연산자, 실행할 주문 ID를 모두 정의합니다.
    """

    schedule: NotRequired[str]
    """EN:
        Cron-style expression controlling when the strategy evaluates. Supports
        5/6/7-field cron dialects with seconds and year precision.

    KO:
        크론 표현식으로 전략 실행 시간을 지정합니다. 초/연도 필드를 포함한
        5/6/7 필드 형식을 지원하며 아래는 상세 안내입니다.

        ### 필드 순서
        - 5-필드: 분 시 일(날짜) 월 요일 → 5-필드는 seconds-first 영향 없음
        - 6-필드: 초 분 시 일(날짜) 월 요일
        - 7-필드: 초 분 시 일(날짜) 월 요일 연도

        ### 허용 값/연산자
        - 초/분: 0–59, 시: 0–23, 일: 1–31 또는 l(마지막 날), 월: 1–12 또는 jan–dec,
          요일: 0–6 또는 sun–sat(0 또는 7=일요일), 연도: 1970–2099
        - 와일드카드: *
        - 범위/목록: A-B, A,B,C
        - 간격: A/B 또는 A-B/S (예: */5)
        - 요일 n번째: 요일#n (예: 2#3=셋째 화요일)
        - 요일 마지막: lX (예: l5=마지막 금요일)
        - 일(날짜) l: 해당 달의 마지막 날
        - 일(날짜)과 요일을 함께 쓰면 OR

        ### 6-필드 예시 (초 분 시 일 월 요일)
        - 매초: * * * * * *
        - 5초마다: */5 * * * * *
        - 매분 0초: 0 * * * * *
        - 15분마다(0초): 0 */15 * * * *
        - 매시 정각: 0 0 * * * *
        - 매일 09:30:00: 0 30 9 * * *
        - 매월 1일 09:00:00: 0 0 9 1 * *
        - 매월 마지막 날 18:00:00: 0 0 18 l * *
        - 매주 월요일 10:00:00: 0 0 10 * * mon
        - 평일 10:00:00: 0 0 10 * * mon-fri
        - 1·4·7월 10:00:00: 0 0 10 * jan,apr,jul *
        - 매월 셋째 화요일 10:00:00: 0 0 10 * * 2#3
        - 매월 마지막 금요일 18:00:00: 0 0 18 * * l5
        - 평일 9–18시 매시 정각: 0 0 9-18 * * mon-fri
        - 평일 9–18시 10분 간격(0초): 0 0/10 9-18 * * mon-fri
        - 매 시각 15·30·45분의 10초: 10 15,30,45 * * * *
        - 일요일 09:00:00: 0 0 9 * * 0,7

        ### 7-필드 예시 (초 분 시 일 월 요일 연도)
        - 2025년 동안 매초: * * * * * * 2025
        - 2025–2026년 매월 1일 00:00:00: 0 0 0 1 * * 2025-2026
        - 2025년 평일 09:00:00: 0 0 9 * * mon-fri 2025
        - 2025년 매월 마지막 날 18:30:05: 5 30 18 l * * 2025
        - 2025년 매월 셋째 화요일 10:00:00: 0 0 10 * * 2#3 2025
        - 2025–2030년 격년 1/1 00:00:00: 0 0 0 1 jan * 2025-2030/2

        ### 5-필드 예시 (분 시 일 월 요일, 항상 0초)
        - 매분: * * * * *
        - 5분마다: */5 * * * *
        - 평일 09:00: 0 9 * * mon-fri
        - 매월 마지막 날 18:00: 0 18 l * *
        - 매월 셋째 화요일 10:00: 0 10 * * 2#3

        ### 팁/주의
        - 5-필드는 초 필드가 없고 항상 0초입니다.
        - 일(날짜)과 요일을 같이 쓰면 OR입니다.
        - 일요일은 0 또는 7, 요일/월 이름은 대소문자 무관입니다.
            - 허용 형태:
                - 요일: sun, mon, tue, wed, thu, fri, sat 또는 숫자 0–6
                - 일요일은 0 권장. 7은 일부 설정/버전에서 거부될 수 있으니 사용하지 않는 게 안전합니다.
                - 월: jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec 또는 숫자 1–12
            - 예시:
                - 0 0 10 * * Mon-Fri → 평일 10:00:00
                - 0 0 9 * Jan,Apr,Jul * → 1·4·7월 09:00:00
                - 0 0 9 * * sun → 일요일 09:00:00
                - 0 0 9 * * 0 → 일요일 09:00:00 (권장 숫자 표기)
        - 연도 제한은 7-필드에서만 가능합니다(1970–2099).
        - 시간대는 ``strategies.timezone`` 을 따릅니다.
    """

    timezone: NotRequired[str]
    """EN: Time zone name used for schedule evaluation.
    KO: 스케줄을 평가할 때 사용하는 시간대 이름입니다."""

    id: str
    """EN: Unique identifier for the strategy.
    KO: 전략의 고유 식별자입니다."""

    description: NotRequired[str]
    """EN: Human-readable description of the strategy.
    KO: 전략 설명입니다."""

    symbols: NotRequired[Optional[List[
        StrategySymbolInputType,
    ]]]
    """EN: Symbols to evaluate; ``None`` checks all available symbols.
    KO: 분석할 종목 목록이며 ``None`` 이면 전체 종목을 검토합니다."""

    logic: LogicType
    """EN: Logical reducer applied to the ``conditions`` list.
    KO: ``conditions`` 목록에 적용되는 논리 연산자입니다."""

    threshold: NotRequired[int]
    """EN: Numeric threshold used by selected logic modes.
    KO: 특정 논리 모드에서 사용하는 수치 임계값입니다."""

    order_id: NotRequired[str]
    """EN: Identifier of the order definition triggered by this strategy.
    KO: 전략 성공 시 실행할 주문 정의의 식별자입니다."""

    max_symbols: NotRequired[MaxSymbolsLimitType]
    """EN: Limits how many symbols the strategy processes.
    KO: 전략이 처리할 종목 수를 제한합니다."""

    conditions: NotRequired[List[Union[
        'StrategyConditionType',
        'DictConditionType',
        BaseStrategyConditionOverseasStock,
        BaseStrategyConditionOverseasFutures,
    ]]]
    """EN: Condition blocks or callables to evaluate.
    KO: 평가할 조건 블록 혹은 호출 가능한 조건 목록입니다."""

    run_once_on_start: NotRequired[bool]
    """EN: Run immediately on system startup before schedule waits.
    KO: 시스템 시작 직후 스케줄 대기 전에 한 번 실행할지 여부입니다."""


class DictConditionType(TypedDict):
    """String-referenced condition definition for dynamic loading.

    EN:
        Allows referencing condition implementations by identifier along with
        parameter dictionaries.

    KO:
        식별자와 매개변수 사전을 통해 조건 구현을 참조할 수 있습니다.
    """

    condition_id: str
    """EN: Identifier of the condition to resolve dynamically.
    KO: 동적으로 로드할 조건의 식별자입니다."""

    params: NotRequired[Dict[str, Any]]
    """EN: Parameters forwarded to the condition implementation.
    KO: 조건 구현에 전달할 매개변수입니다."""

    weight: NotRequired[int]
    """EN: Optional weighting factor (defaults to 0).
    KO: 선택적 가중치이며 기본값은 0입니다."""


class SystemSettingType(TypedDict):
    """Metadata describing a ProgramGarden system.

    EN:
        Includes display information and logging preferences.

    KO:
        표시 정보와 로깅 선호도를 포함한 시스템 메타데이터입니다.
    """

    system_id: str
    """EN: Unique identifier for the system.
    KO: 시스템의 고유 식별자입니다."""

    name: str
    """EN: System display name.
    KO: 시스템 이름입니다."""

    description: NotRequired[str]
    """EN: Human-readable system description.
    KO: 시스템 설명입니다."""

    version: NotRequired[str]
    """EN: Version identifier.
    KO: 버전 식별자입니다."""

    author: NotRequired[str]
    """EN: Author or maintainer name.
    KO: 작성자 또는 유지보수자 이름입니다."""

    date: NotRequired[str]
    """EN: Creation date as a string (e.g., ``YYYY-MM-DD``).
    KO: 문자열 형태의 생성일입니다 (예: ``YYYY-MM-DD``)."""

    debug: NotRequired[str]
    """EN:
        Logging level string such as ``DEBUG`` or ``INFO``.

    KO:
        ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL`` 등 로깅 레벨을
        설정합니다.
    """


class SecuritiesAccountType(TypedDict):
    """Brokerage credential information for ProgramGarden systems.

    EN:
        Maps configuration inputs to credentials required by LS Securities.

    KO:
        LS 증권에 필요한 자격 증명을 구성 파일과 매핑합니다.
    """

    company: Literal["ls"]
    """EN: Brokerage company identifier (currently ``ls``).
    KO: 증권사 식별자이며 현재는 ``ls`` 만 지원합니다."""

    product: Literal["overseas_stock", "overseas_futures"]
    """EN: Product category managed by the account.
    KO: 계좌가 다루는 상품 유형입니다."""

    appkey: str
    """EN: Application key issued by the broker.
    KO: 브로커가 발급한 앱 키입니다."""

    appsecretkey: str
    """EN: Application secret key.
    KO: 앱 시크릿 키입니다."""

    paper_trading: NotRequired[bool]
    """EN: Flag indicating whether to use paper trading endpoints.
    KO: 모의투자를 사용할지 여부입니다."""


class OrderTimeType(TypedDict):
    """Time window configuration for order execution.

    EN:
        Allows strategies to restrict when orders can be sent.

    KO:
        주문 전송 가능 시간을 제한하기 위한 설정입니다.
    """

    start: str
    """EN: Window start time in ``HH:MM:SS`` format.
    KO: ``HH:MM:SS`` 형식의 시작 시간입니다."""

    end: str
    """EN: Window end time in ``HH:MM:SS`` format.
    KO: ``HH:MM:SS`` 형식의 종료 시간입니다."""

    days: List[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]]
    """EN: Days of week when the window is active (e.g., ``['mon', 'tue']``).
    KO: 주문 실행이 활성화되는 요일 목록입니다 (예: ``['mon', 'tue']``)."""

    timezone: NotRequired[str]
    """EN: Time zone identifier (e.g., ``Asia/Seoul``).
    KO: 시간대 식별자입니다 (예: ``Asia/Seoul``)."""

    behavior: Literal["defer", "skip"] = "defer"
    """EN:
        - ``defer``: Triggered outside the window → execute at next window start.
        - ``skip``: Triggered outside the window → drop the order.

    KO:
        - ``defer``: 시간 범위 밖에서 트리거되면 다음 시간 시작 시 주문을 실행합니다.
        - ``skip``: 시간 범위 밖에서 트리거되면 주문을 실행하지 않습니다.
    """

    max_delay_seconds: int = 86400
    """EN: Maximum delay allowed in seconds (default 86400).
    KO: 허용되는 최대 지연 시간(초)이며 기본값은 86400초입니다."""


class DpsTyped(TypedDict):
    """Deposit metadata shared with order strategies.

    EN:
        Provides available balance information (currently USD only).

    KO:
        주문 전략에 전달되는 예수금 정보입니다 (현재 USD만 지원).
    """

    deposit: float
    """EN: Total deposit amount.
    KO: 총 예수금 금액입니다."""

    orderable_amount: float
    """EN: Amount available for new orders.
    KO: 신규 주문에 사용할 수 있는 금액입니다."""

    currency: Literal["USD"]
    """EN: Currency code for the deposit (``USD``).
    KO: 예수금 통화 코드이며 ``USD`` 입니다."""


class OrderStrategyType(TypedDict):
    """Configuration describing how orders should be executed.

    EN:
        Binds condition implementations to specific order payload generators.

    KO:
        특정 주문 생성 로직을 조건 구현과 연결하는 설정입니다.
    """

    order_id: str
    """EN: Unique identifier for the order strategy.
    KO: 주문 전략의 고유 식별자입니다."""

    description: NotRequired[str]
    """EN: Optional description for documentation.
    KO: 문서화를 위한 선택적 설명입니다."""

    block_duplicate_buy: NotRequired[bool]
    """EN: Prevent repeated buy orders for the same symbol.
    KO: 동일 종목에 대한 중복 매수를 방지합니다."""

    available_balance: NotRequired[DpsTyped]
    """EN: Snapshot of balances used when sizing orders.
    KO: 주문 규모 산정 시 참고할 예수금 정보입니다."""

    order_time: NotRequired[OrderTimeType]
    """EN: Time-window configuration restricting when orders can run.
    KO: 주문 실행 시간을 제한하는 설정입니다."""

    condition: NotRequired[Union[
        DictConditionType,
        BaseNewOrderOverseasStock,
        BaseModifyOrderOverseasStock,
        BaseCancelOrderOverseasStock,
        BaseNewOrderOverseasFutures,
        BaseModifyOrderOverseasFutures,
        BaseCancelOrderOverseasFutures,
    ]]
    """EN: Condition or strategy class that produces order payloads.
    KO: 주문 페이로드를 생성하는 조건 또는 전략 클래스입니다."""


class SystemType(TypedDict):
    """Top-level automation system configuration contract.

    EN:
        Aggregates settings, accounts, strategies, and orders into a single
        structure consumed by ProgramGarden.

    KO:
        ProgramGarden이 소비하는 설정, 계좌, 전략, 주문을 하나로 묶은 구성입니다.
    """

    id: str
    """EN: Unique system identifier.
    KO: 시스템 고유 식별자입니다."""

    settings: SystemSettingType
    """EN: System-level metadata and logging preferences.
    KO: 시스템 메타데이터와 로깅 설정입니다."""

    securities: SecuritiesAccountType
    """EN: Brokerage account credentials.
    KO: 증권사 인증 정보입니다."""

    strategies: List[StrategyType]
    """EN: Strategy definitions to execute.
    KO: 실행할 전략 정의 목록입니다."""

    orders: List[OrderStrategyType]
    """EN: Order strategies referenced by ``order_id``.
    KO: ``order_id`` 로 참조되는 주문 전략 목록입니다."""
