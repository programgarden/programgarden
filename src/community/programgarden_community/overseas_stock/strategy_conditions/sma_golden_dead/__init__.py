"""
Moving average golden/dead cross detection conditions

1) Observed a dead->golden where golden_price > dead_price (candidate)
2) The golden occurred within the most recent 2 data points
3) The latest alignment is golden (still maintained)
"""
from dataclasses import dataclass
from typing import List, Literal, Optional, TypedDict
from programgarden_core import (
    BaseStrategyConditionResponseType,
    BaseStrategyCondition,
)
from programgarden_finance import LS, g3204


class ChartDay(TypedDict):
    """
    차트 일별 데이터 타입
    """
    date: str  # 날짜
    price: float  # 종가


@dataclass
class SMASignal:
    """
    SMA 신호 데이터 클래스
    """
    cross: Literal["golden", "dead", "none"]
    price: float
    volume: float
    date: str


class SMAGoldenDeadCross(BaseStrategyCondition):
    """
    SMA 해외 주식 클래스
    """

    id: str = "SMAGoldenDeadCross"
    description: str = """
Moving average golden/dead cross detection conditions

1) Observed a dead->golden where golden_price > dead_price (candidate)
2) The golden occurred within the most recent 2 data points
3) The latest alignment is golden (still maintained)
"""

    def __init__(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        long_period: int,
        short_period: int,
        time_category: Literal["months", "weeks", "days"] = "days",
        days_prices: Optional[list[ChartDay]] = None,
        use_ls: bool = True,
        alignment: Literal["golden", "dead"] = "golden",
        appkey: Optional[str] = None,
        appsecretkey: Optional[str] = None,
    ):
        """
        SMA 해외 주식 클래스 초기화

        Args:
            symbol (str): 종목 코드, ex) "82TSLA"
            exchcd (str): LS증권에서 사용하는 거래소 코드, ex) "82"
            start_date (Optional[str]): 시작 날짜, ex) 20230101
            end_date (Optional[str]): 종료 날짜, ex) 20231231
            long_period: int: 롱 포지션 기간
            short_period: int: 숏 포지션 기간
            time_category (Literal["months", "weeks", "days", "minutes"]): 카테고리
            days_prices (Optional[list[ChartDay]]): 기간 동안의 종가 리스트
            use_ls (bool): LS증권 데이터를 사용할지 여부
            alignment (Literal["golden", "dead"]): 정렬 방식
            appkey (Optional[str]): LS증권 앱키
            appsecretkey (Optional[str]): LS증권 앱시크릿키
        """
        super().__init__()

        if not use_ls and not days_prices:
            raise ValueError("LS증권 데이터를 사용하지 않는 경우 days_prices가 필요합니다.")

        if use_ls and (not appkey or not appsecretkey):
            raise ValueError("LS증권 데이터를 사용하려면 appkey와 appsecretkey가 필요합니다.")

        self.start_date = start_date
        self.end_date = end_date

        # store provided SMA periods and helper list used by calculator
        self.long_period = long_period
        self.short_period = short_period
        # list of SMA periods used throughout the calculator (short -> long)
        self.sma_periods = [self.short_period, self.long_period]

        # transition detection state:
        # last observed dead cross price (None if not seen yet)
        self._last_dead_price = None
        # whether a valid dead->golden transition (golden price > dead price) was observed
        self._transition_detected = False

        self.time_category = time_category
        self.days_prices = days_prices if days_prices is not None else []
        self.use_ls = use_ls
        self.alignment = alignment
        self.appkey = appkey
        self.appsecretkey = appsecretkey

    async def execute(self) -> BaseStrategyConditionResponseType:
        """
        SMA 해외 주식 전략을 실행합니다.
        이 메서드는 비동기적으로 실행됩니다.
        """

        self.ls = LS.get_instance()
        if not self.ls.token_manager.is_token_available():
            await self.ls.async_login()
        exchcd = self.symbol.get("exchcd")
        symbol = self.symbol.get("symbol")

        gubun = "2"
        if self.time_category == "days":
            gubun = "2"
        elif self.time_category == "weeks":
            gubun = "3"
        elif self.time_category == "months":
            gubun = "4"

        m_g3204 = self.ls.overseas_stock().chart().g3204(
            g3204.G3204InBlock(
                sdate=self.start_date,
                edate=self.end_date,
                keysymbol=exchcd + symbol,
                exchcd=exchcd,
                symbol=symbol,
                gubun=gubun,
                qrycnt=500,
            )
        )

        occurs_result = await m_g3204.occurs_req_async()
        all_blocks: List[g3204.blocks.G3204OutBlock1] = []
        for response in occurs_result:
            all_blocks.extend(response.block1)
        all_blocks.sort(key=lambda x: x.date)

        self.all_signal = self._calculator(all_blocks)

        return {
            "condition_id": self.id,
            # "success": getattr(self, "_transition_detected", False),
            "success": True,
            "exchange": self.symbol.get("exchcd", None),
            "symbol": self.symbol.get("symbol", None),
            "data": self.all_signal
        }

    def _calculator(
        self,
        blocks: List[g3204.blocks.G3204OutBlock1],
    ) -> List[SMASignal]:
        """
        응답을 처리하는 메소드

        Args:
            response (g3204.blocks.G3204Response): 응답 객체
            status (RequestStatus): 요청 상태
        """

        signals = []

        # For simplicity we only handle a single short vs long SMA pair
        short_period = int(self.short_period)
        long_period = int(self.long_period)
        max_period = max(self.sma_periods)

        # tracking variables to support the new requirement:
        # - golden must have occurred within the last 2 data points
        # - golden alignment must still be maintained at the end
        last_dead_price = None
        golden_index = None
        golden_price = None
        transition_candidate = False
        last_alignment_golden = False

        for idx, block in enumerate(blocks):
            # SMA 계산을 위한 데이터 수집
            if not hasattr(self, 'price_history'):
                self.price_history = []

            self.price_history.append(block.close)

            cross_type = "none"

            # 현재 SMA 계산 (데이터가 충분할 때)
            if len(self.price_history) >= max_period:
                current_short = sum(self.price_history[-short_period:]) / short_period
                current_long = sum(self.price_history[-long_period:]) / long_period

                # update last alignment state (used after loop)
                last_alignment_golden = current_short > current_long

                # 이전 시점 SMA가 존재할 때만 크로스 판정
                if len(self.price_history) > max_period:
                    prev_short = sum(self.price_history[-short_period-1:-1]) / short_period
                    prev_long = sum(self.price_history[-long_period-1:-1]) / long_period

                    # 정렬 상태: strict 비교 (현재 단기 > 장기 => 골든 정렬)
                    all_golden_aligned = current_short > current_long
                    all_dead_aligned = current_short < current_long

                    # 최근 크로스 발생 여부
                    recent_golden_cross = (prev_short <= prev_long and current_short > current_long)
                    recent_dead_cross = (prev_short >= prev_long and current_short < current_long)

                    if all_golden_aligned and recent_golden_cross:
                        cross_type = "golden"
                    elif all_dead_aligned and recent_dead_cross:
                        cross_type = "dead"

                    sma_signal = SMASignal(
                        cross=cross_type,
                        price=block.close,
                        volume=block.volume,
                        date=block.date,
                    )

                    # transition tracking: record dead/golden with their indices and prices
                    if cross_type == "dead":
                        last_dead_price = block.close
                        # keep compatibility with instance attribute
                        self._last_dead_price = last_dead_price
                    elif cross_type == "golden":
                        golden_index = idx
                        golden_price = block.close
                        # golden must be strictly higher than last dead price to be candidate
                        if last_dead_price is not None and golden_price > last_dead_price:
                            transition_candidate = True

                    signals.append(sma_signal)

        # Final evaluation: mark transition detected only when
        # 1) we observed a dead->golden where golden_price > dead_price (candidate)
        # 2) the golden occurred within the most recent 2 data points
        # 3) the latest alignment is golden (still maintained)
        self._transition_detected = False
        if transition_candidate and golden_index is not None:
            # number of data points since the golden event
            if len(blocks) - golden_index <= 2 and last_alignment_golden:
                self._transition_detected = True

        # persist last dead price for external visibility
        self._last_dead_price = last_dead_price

        return signals
