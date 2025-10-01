from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from programgarden_core.bases.base import SymbolInfo
from programgarden_core.bases.modify_orders import BaseModifyOrderOverseasStock
from programgarden_core.bases.new_orders import BaseNewOrderOverseasStock
from programgarden_core.bases.cancel_orders import BaseCancelOrderOverseasStock
from programgarden_core.bases.strategy import BaseStrategyCondition


LogicType = Literal["all", "any", "not", "xor", "at_least", "at_most", "exactly", "if_then", "weighted"]
"""
다음 설명과 같습니다.
- "all": 모든 조건 만족 (AND)
- "any": 하나 이상 조건 만족 (OR)
- "not": 조건이 만족되지 않아야 함 (NOT)
- "xor": 정확히 하나만 만족 (XOR)
- "at_least": 최소 N개 조건 만족
- "at_most": 최대 N개 조건 만족
- "exactly": 정확히 N개 조건 만족
- "if_then": 조건부 논리 (if-then)
- "weighted": 가중치 기반 조건 (점수 시스템)
```
"""


class StrategyConditionType(TypedDict):
    """
    기본 전략 타입을 정의하는 TypedDict입니다.
    """

    id: str
    """전략의 고유 ID"""
    description: Optional[str] = None
    """전략에 대한 설명"""
    logic: LogicType
    """전략의 논리 연산자"""
    threshold: Optional[int] = None
    """전략의 임계값"""
    conditions: List[Union['StrategyConditionType', BaseStrategyCondition]]
    """실행할 전략 리스트"""


class MaxSymbolsLimitType(TypedDict):
    order: Literal["random", "mcap"]
    """
    종목 선택 방식
    - random: 랜덤 선택
    - mcap: 시가총액 상위 선택
    """
    limit: int
    """선택할 종목 수"""


class StrategyType(TypedDict):
    schedule: Optional[str] = None
    """
### 필드 순서
- 5-필드: 분 시 일(날짜) 월 요일 → 5-필드는 seconds-first 영향 없음
- 6-필드: 초 분 시 일(날짜) 월 요일
- 7-필드: 초 분 시 일(날짜) 월 요일 연도

<br>

### 허용 값/연산자
- 초/분: 0–59, 시: 0–23, 일: 1–31 또는 l(마지막 날), 월: 1–12 또는 jan–dec, 요일: 0–6 또는 sun–sat(0 또는 7=일요일), 연도: 1970–2099
- 와일드카드: *
- 범위/목록: A-B, A,B,C
- 간격: A/B 또는 A-B/S (예: */5)
- 요일 n번째: 요일#n (예: 2#3=셋째 화요일)
- 요일 마지막: lX (예: l5=마지막 금요일)
- 일(날짜) l: 해당 달의 마지막 날
- 일(날짜)과 요일을 함께 쓰면 OR

<br>

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

<br>

### 7-필드 예시 (초 분 시 일 월 요일 연도)
- 2025년 동안 매초: * * * * * * 2025
- 2025–2026년 매월 1일 00:00:00: 0 0 0 1 * * 2025-2026
- 2025년 평일 09:00:00: 0 0 9 * * mon-fri 2025
- 2025년 매월 마지막 날 18:30:05: 5 30 18 l * * 2025
- 2025년 매월 셋째 화요일 10:00:00: 0 0 10 * * 2#3 2025
- 2025–2030년 격년 1/1 00:00:00: 0 0 0 1 jan * 2025-2030/2

<br>

### 5-필드 예시 (분 시 일 월 요일, 항상 0초)
- 매분: * * * * *
- 5분마다: */5 * * * *
- 평일 09:00: 0 9 * * mon-fri
- 매월 마지막 날 18:00: 0 18 l * *
- 매월 셋째 화요일 10:00: 0 10 * * 2#3

<br>

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
- 시간대는 strategies.timezone을 따릅니다.
    """
    timezone: Optional[str] = "Asia/Seoul"
    id: str
    """전략의 고유 ID"""
    description: Optional[str] = None
    """전략에 대한 설명"""
    symbols: Optional[List[SymbolInfo]] = None
    """분석할 종목들, 빈값이면 전체 종목에서 분석한다."""
    logic: LogicType
    """전략의 논리 연산자"""
    threshold: Optional[int] = None
    """전략의 임계값"""
    order_id: Optional[str] = None
    """
    buy 또는 sell 영역에서 주문으로 사용될 order_id들을 선택한다.
    """
    max_symbols: Optional[MaxSymbolsLimitType]
    """
    전체 종목중에 몇개까지만 확인할지 지정한다. None이면 전체 종목을 다 확인한다.
    """
    conditions: Optional[List[Union['StrategyConditionType', 'DictConditionType', BaseStrategyCondition]]]
    """실행할 전략 리스트"""


class DictConditionType(TypedDict):
    """
    문자열 표현을 사용하여 조건을 정의합니다.
    """
    condition_id: str
    """전략의 고유 ID"""
    params: Optional[Dict[str, Any]]
    """조건에 필요한 매개변수들"""
    weight: Optional[int] = 0
    """조건의 가중치, 기본값은 0"""


class SystemSettingType(TypedDict):
    """시스템 설정 정보"""
    name: str
    """시스템 이름"""
    description: str
    """시스템 설명"""
    version: str
    """시스템 버전"""
    author: str
    """시스템 작성자"""
    date: str
    """시스템 생성일"""
    debug: str
    """
    디버그 모드 여부
    "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" 단계로 설정
    """


class SecuritiesAccountType(TypedDict):
    """계좌와 증권사 및 상품 정보"""
    company: Literal["ls"]
    """증권사 이름"""
    product: Literal["overseas_stock", "overseas_future"]
    """상품 이름"""
    appkey: Optional[str]
    """앱 키"""
    appsecretkey: Optional[str]
    """앱 시크릿 키"""


class OrderTimeType(TypedDict, total=False):
    start: str
    """시작 시간, HH:MM:SS 형식"""
    end: str
    """종료 시간, HH:MM:SS 형식"""
    days: List[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]]
    """주문 실행 요일, 예: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']"""
    timezone: Optional[str]
    """시간대, 예: 'Asia/Seoul'"""
    behavior: Optional[Literal["defer", "skip"]]
    """
    - defer: 전략이 윈도우 밖에서 트리거되면 다음 윈도우 시작 시 주문을 실행(대기). 윈도우 안에서 트리거되면 즉시 실행.
    - skip: 윈도우 밖에서 트리거되면 주문을 실행하지 않음(스킵). 윈도우 안에서는 즉시 실행.
    """
    max_delay_seconds: Optional[int] = 86400
    """최대 지연 시간(초), 기본값 86400초(24시간)"""


class OrderStrategyType(TypedDict, total=False):
    """
    오더 전략 타입
    """
    order_id: str
    """오더의 고유 ID"""
    description: Optional[str]
    """오더에 대한 설명"""
    block_duplicate_buy: Optional[bool]
    """중복 매수 방지 여부"""
    available_balance: Optional[float]
    """사용 가능한 예수금"""
    order_time: Optional[OrderTimeType] = None
    """주문 실행 시간 설정"""
    condition: Optional[Union[
        DictConditionType,
        BaseNewOrderOverseasStock,
        BaseModifyOrderOverseasStock,
        BaseCancelOrderOverseasStock
    ]]
    """오더 전략 정보"""


class SystemType(TypedDict):
    """자동화 시스템 데이터 타입"""
    id: str
    """시스템의 고유 ID"""
    settings: SystemSettingType
    """시스템 설정 정보"""
    securities: SecuritiesAccountType
    """증권사 인증 정보"""
    strategies: List[StrategyType]
    """시스템 실행 바디"""
    orders: List[OrderStrategyType]
    """주문 정보"""
