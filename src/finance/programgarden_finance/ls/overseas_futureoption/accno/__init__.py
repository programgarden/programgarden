from typing import Optional

from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .CIDBQ01400 import TrCIDBQ01400
from .CIDBQ01400.blocks import (
    CIDBQ01400InBlock1,
    CIDBQ01400Request,
    CIDBQ01400RequestHeader,
)
from .CIDBQ01500 import TrCIDBQ01500
from .CIDBQ01500.blocks import (
    CIDBQ01500InBlock1,
    CIDBQ01500Request,
    CIDBQ01500RequestHeader,
)
from .CIDBQ01800 import TrCIDBQ01800
from .CIDBQ01800.blocks import (
    CIDBQ01800InBlock1,
    CIDBQ01800Request,
    CIDBQ01800RequestHeader,
)
from .CIDBQ02400 import TrCIDBQ02400
from .CIDBQ02400.blocks import (
    CIDBQ02400InBlock1,
    CIDBQ02400Request,
    CIDBQ02400RequestHeader,
)
from .CIDBQ03000 import TrCIDBQ03000
from .CIDBQ03000.blocks import (
    CIDBQ03000InBlock1,
    CIDBQ03000Request,
    CIDBQ03000RequestHeader,
)
from .CIDBQ05300 import TrCIDBQ05300
from .CIDBQ05300.blocks import (
    CIDBQ05300InBlock1,
    CIDBQ05300Request,
    CIDBQ05300RequestHeader,
)
from .CIDEQ00800 import TrCIDEQ00800
from .CIDEQ00800.blocks import (
    CIDEQ00800InBlock1,
    CIDEQ00800Request,
    CIDEQ00800RequestHeader,
)
from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Accno(metaclass=EnforceKoreanAliasMeta):

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def CIDBQ01400(
        self,
        body: CIDBQ01400InBlock1,
        header: Optional[CIDBQ01400RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCIDBQ01400:
        """
        LS openAPI의 CIDBQ01400 해외선물 체결내역개별 조회(주문가능수량)를 조회합니다.

        Args:
            body (CIDBQ01400InBlock1): 조회를 위한 입력 데이터입니다.

        Returns:
            TrCIDBQ01400: 조회를 위한 TrCIDBQ01400 인스턴스
        """

        request_data = CIDBQ01400Request(
            body={
                "CIDBQ01400InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBQ01400(request_data)

    해외선물_체결내역개별조회 = CIDBQ01400
    해외선물_체결내역개별조회.__doc__ = "해외선물 체결내역개별 조회(주문가능수량)를 조회합니다."

    @require_korean_alias
    def CIDBQ01500(
        self,
        body: CIDBQ01500InBlock1,
        header: Optional[CIDBQ01500RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """해외선물 미결제잔고내역 조회를 조회합니다."""

        request_data = CIDBQ01500Request(
            body={
                "CIDBQ01500InBlock1": body,
            },
        )

        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBQ01500(request_data)

    해외선물_미결제잔고내역조회 = CIDBQ01500
    해외선물_미결제잔고내역조회.__doc__ = "해외선물 미결제잔고내역 조회를 조회합니다."

    @require_korean_alias
    def CIDBQ01800(
        self,
        body: CIDBQ01800InBlock1,
        header: Optional[CIDBQ01800RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        해외선물 주문내역 조회를 조회합니다.
        """

        request_data = CIDBQ01800Request(
            body={
                "CIDBQ01800InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBQ01800(request_data)

    해외선물_주문내역조회 = CIDBQ01800
    해외선물_주문내역조회.__doc__ = "해외선물 주문내역 조회를 조회합니다."

    @require_korean_alias
    def CIDBQ02400(
        self,
        body: CIDBQ02400InBlock1,
        header: Optional[CIDBQ02400RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        해외선물 주문체결내역 상세 조회를 조회합니다.
        """

        request_data = CIDBQ02400Request(
            body={
                "CIDBQ02400InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBQ02400(request_data)

    해외선물_주문체결내역상세조회 = CIDBQ02400
    해외선물_주문체결내역상세조회.__doc__ = "해외선물 주문체결내역 상세 조회를 조회합니다."

    @require_korean_alias
    def CIDBQ03000(
        self,
        body: CIDBQ03000InBlock1,
        header: Optional[CIDBQ03000RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        해외선물 예수금/잔고현황 조회를 조회합니다.
        """

        request_data = CIDBQ03000Request(
            body={
                "CIDBQ03000InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBQ03000(request_data)

    해외선물_예수금잔고현황조회 = CIDBQ03000
    해외선물_예수금잔고현황조회.__doc__ = "해외선물 예수금/잔고현황 조회를 조회합니다."

    @require_korean_alias
    def CIDBQ05300(
        self,
        body: CIDBQ05300InBlock1,
        header: Optional[CIDBQ05300RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        해외선물 예탁자산 조회를 조회합니다.
        """

        request_data = CIDBQ05300Request(
            body={
                "CIDBQ05300InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBQ05300(request_data)

    해외선물_예탁자산조회 = CIDBQ05300
    해외선물_예탁자산조회.__doc__ = "해외선물 예탁자산 조회를 조회합니다."

    @require_korean_alias
    def CIDEQ00800(
        self,
        body: CIDEQ00800InBlock1,
        header: Optional[CIDEQ00800RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        해외선물 일자별 미결제 잔고내역조회합니다.
        """

        request_data = CIDEQ00800Request(
            body={
                "CIDEQ00800InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDEQ00800(request_data)

    해외선물_일자별_미결제잔고내역조회 = CIDEQ00800
    해외선물_일자별_미결제잔고내역조회.__doc__ = "해외선물 일자별 미결제 잔고내역을 조회합니다."

    def account_tracker(
        self,
        market_client,
        real_client,
        refresh_interval: int = 60,
        spec_refresh_hours: int = 6,
        commission_rate: float = 7.5,
    ):
        """
        계좌 추적기 생성 (보유포지션, 예수금, 미체결 실시간 추적)

        Args:
            market_client: 시세 API 클라이언트 (overseas_futureoption().market()) - 필수
                - o3121 종목 명세 조회에 필요
            real_client: 실시간 클라이언트 (overseas_futureoption().real()) - 필수
            refresh_interval: API 갱신 주기 (초, 기본 60초)
            spec_refresh_hours: 종목 명세 갱신 주기 (시간, 기본 6시간)
            commission_rate: 계약당 수수료 (USD, 편도. 기본 $7.5)

        Returns:
            FuturesAccountTracker: 계좌 추적기 인스턴스

        Example:
            ```python
            # 사용 예시
            market = overseas_futureoption().market()
            real = overseas_futureoption().real()
            await real.connect()
            
            tracker = accno.account_tracker(
                market_client=market,
                real_client=real,
                commission_rate=7.5,  # 계약당 $7.5
            )
            await tracker.start()

            # 콜백 등록
            tracker.on_position_change(lambda positions: print(positions))
            tracker.on_balance_change(lambda balance: print(balance))

            # 종목 명세 조회
            spec = tracker.get_symbol_spec("NQH25")
            print(f"Tick Size: {spec.tick_size}, Tick Value: {spec.tick_value}")

            # 종료
            await tracker.stop()
            ```
        """
        from decimal import Decimal
        from ..extension import FuturesAccountTracker

        return FuturesAccountTracker(
            accno_client=self,
            market_client=market_client,
            real_client=real_client,
            refresh_interval=refresh_interval,
            spec_refresh_hours=spec_refresh_hours,
            commission_rate=Decimal(str(commission_rate)),
        )

    계좌추적기 = account_tracker
    계좌추적기.__doc__ = "해외선물 계좌 실시간 추적기를 생성합니다."


__all__ = [
    Accno,

    TrCIDBQ01400,
    TrCIDBQ01800,
    TrCIDBQ02400,
    TrCIDBQ03000,
    TrCIDBQ05300,
    TrCIDEQ00800,

    CIDBQ01400InBlock1,
    CIDBQ01800InBlock1,
    CIDBQ02400InBlock1,
    CIDBQ03000InBlock1,
    CIDBQ05300InBlock1,
    CIDEQ00800InBlock1,

    CIDBQ01400Request,
    CIDBQ01800Request,
    CIDBQ02400Request,
    CIDBQ03000Request,
    CIDBQ05300Request,
    CIDEQ00800Request,
]
