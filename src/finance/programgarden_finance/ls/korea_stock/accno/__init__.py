
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager

from .CSPAQ22200 import TrCSPAQ22200
from .CSPAQ22200.blocks import (
    CSPAQ22200InBlock1,
    CSPAQ22200Request,
    CSPAQ22200RequestHeader,
)
from .CSPAQ12300 import TrCSPAQ12300
from .CSPAQ12300.blocks import (
    CSPAQ12300InBlock1,
    CSPAQ12300Request,
    CSPAQ12300RequestHeader,
)
from .CSPAQ13700 import TrCSPAQ13700
from .CSPAQ13700.blocks import (
    CSPAQ13700InBlock1,
    CSPAQ13700Request,
    CSPAQ13700RequestHeader,
)
from .CDPCQ04700 import TrCDPCQ04700
from .CDPCQ04700.blocks import (
    CDPCQ04700InBlock1,
    CDPCQ04700Request,
    CDPCQ04700RequestHeader,
)
from .FOCCQ33600 import TrFOCCQ33600
from .FOCCQ33600.blocks import (
    FOCCQ33600InBlock1,
    FOCCQ33600Request,
    FOCCQ33600RequestHeader,
)
from .CSPAQ12200 import TrCSPAQ12200
from .CSPAQ12200.blocks import (
    CSPAQ12200InBlock1,
    CSPAQ12200Request,
    CSPAQ12200RequestHeader,
)
from .CSPAQ00600 import TrCSPAQ00600
from .CSPAQ00600.blocks import (
    CSPAQ00600InBlock1,
    CSPAQ00600Request,
    CSPAQ00600RequestHeader,
)
from .CSPBQ00200 import TrCSPBQ00200
from .CSPBQ00200.blocks import (
    CSPBQ00200InBlock1,
    CSPBQ00200Request,
    CSPBQ00200RequestHeader,
)
from .t0424 import TrT0424
from .t0424.blocks import (
    T0424InBlock,
    T0424Request,
    T0424RequestHeader,
)
from .t0425 import TrT0425
from .t0425.blocks import (
    T0425InBlock,
    T0425Request,
    T0425RequestHeader,
)

from programgarden_core.korea_alias import require_korean_alias


class Accno:
    """
    국내 주식 계좌 정보를 조회하는 Accno 클래스입니다.

    API 엔드포인트: /stock/accno
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def cspaq22200(
        self,
        body: CSPAQ22200InBlock1 = None,
        header: Optional[CSPAQ22200RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAQ22200:
        """
        현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다.

        Args:
            body (CSPAQ22200InBlock1): BalCreTp(잔고생성구분, 기본 "0":주식잔고) 입력
            header (Optional[CSPAQ22200RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAQ22200: 예수금/주문가능금액 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = CSPAQ22200InBlock1()

        request_data = CSPAQ22200Request(
            body={
                "CSPAQ22200InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAQ22200(request_data)

    현물계좌예수금주문가능금액총평가 = cspaq22200
    현물계좌예수금주문가능금액총평가.__doc__ = "현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다."

    @require_korean_alias
    def cspaq12300(
        self,
        body: CSPAQ12300InBlock1 = None,
        header: Optional[CSPAQ12300RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAQ12300:
        """
        현물계좌 종목별 잔고내역 및 BEP 단가를 조회합니다.

        Args:
            body (CSPAQ12300InBlock1): 잔고생성구분, 수수료적용구분, 단가구분 등 입력
            header (Optional[CSPAQ12300RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAQ12300: 잔고내역 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = CSPAQ12300InBlock1()

        request_data = CSPAQ12300Request(
            body={
                "CSPAQ12300InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAQ12300(request_data)

    현물계좌잔고내역 = cspaq12300
    현물계좌잔고내역.__doc__ = "현물계좌 종목별 잔고내역 및 BEP 단가를 조회합니다."

    @require_korean_alias
    def cspaq13700(
        self,
        body: CSPAQ13700InBlock1 = None,
        header: Optional[CSPAQ13700RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAQ13700:
        """
        현물계좌 주문체결내역을 조회합니다.

        Args:
            body (CSPAQ13700InBlock1): 주문시장코드, 매매구분, 종목번호, 주문일자 등 입력
            header (Optional[CSPAQ13700RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAQ13700: 주문체결내역 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = CSPAQ13700InBlock1()

        request_data = CSPAQ13700Request(
            body={
                "CSPAQ13700InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAQ13700(request_data)

    현물계좌주문체결내역 = cspaq13700
    현물계좌주문체결내역.__doc__ = "현물계좌 주문체결내역을 조회합니다."

    @require_korean_alias
    def cdpcq04700(
        self,
        body: CDPCQ04700InBlock1 = None,
        header: Optional[CDPCQ04700RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCDPCQ04700:
        """
        계좌의 기간별 거래내역을 조회합니다.

        Args:
            body (CDPCQ04700InBlock1): 계좌번호, 비밀번호, 조회시작일, 조회종료일 등 입력
            header (Optional[CDPCQ04700RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCDPCQ04700: 거래내역 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = CDPCQ04700InBlock1()

        request_data = CDPCQ04700Request(
            body={
                "CDPCQ04700InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCDPCQ04700(request_data)

    계좌거래내역 = cdpcq04700
    계좌거래내역.__doc__ = "계좌의 기간별 거래내역을 조회합니다."

    @require_korean_alias
    def foccq33600(
        self,
        body: FOCCQ33600InBlock1 = None,
        header: Optional[FOCCQ33600RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrFOCCQ33600:
        """
        주식 계좌의 기간별(일별/주별/월별) 수익률 상세를 조회합니다.

        Args:
            body (FOCCQ33600InBlock1): 조회시작일, 조회종료일, 기간구분(1:일별/2:주별/3:월별) 입력
            header (Optional[FOCCQ33600RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrFOCCQ33600: 기간별 수익률 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = FOCCQ33600InBlock1()

        request_data = FOCCQ33600Request(
            body={
                "FOCCQ33600InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrFOCCQ33600(request_data)

    계좌기간별수익률 = foccq33600
    계좌기간별수익률.__doc__ = "주식 계좌의 기간별(일별/주별/월별) 수익률 상세를 조회합니다."

    @require_korean_alias
    def cspaq12200(
        self,
        body: CSPAQ12200InBlock1 = None,
        header: Optional[CSPAQ12200RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAQ12200:
        """
        현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다. (API용)

        Args:
            body (CSPAQ12200InBlock1): BalCreTp(잔고생성구분, 기본 "0":주식잔고) 입력
            header (Optional[CSPAQ12200RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAQ12200: 예수금/주문가능금액 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = CSPAQ12200InBlock1()

        request_data = CSPAQ12200Request(
            body={
                "CSPAQ12200InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAQ12200(request_data)

    현물계좌예수금주문가능금액총평가조회 = cspaq12200
    현물계좌예수금주문가능금액총평가조회.__doc__ = "현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다. (API용)"

    @require_korean_alias
    def cspaq00600(
        self,
        body: CSPAQ00600InBlock1,
        header: Optional[CSPAQ00600RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAQ00600:
        """
        계좌별 신용한도 및 주문가능금액/수량을 조회합니다.

        Args:
            body (CSPAQ00600InBlock1): LoanDtlClssCode(대출상세분류코드), IsuNo(종목번호), OrdPrc(주문가) 입력
            header (Optional[CSPAQ00600RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAQ00600: 계좌별신용한도 조회 인스턴스 (.req() 호출로 실행)
        """

        request_data = CSPAQ00600Request(
            body={
                "CSPAQ00600InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAQ00600(request_data)

    계좌별신용한도조회 = cspaq00600
    계좌별신용한도조회.__doc__ = "계좌별 신용한도 및 주문가능금액/수량을 조회합니다."

    @require_korean_alias
    def cspbq00200(
        self,
        body: CSPBQ00200InBlock1,
        header: Optional[CSPBQ00200RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPBQ00200:
        """
        현물계좌 증거금률별 주문가능수량 및 주문가능금액을 조회합니다.

        Args:
            body (CSPBQ00200InBlock1): BnsTpCode(매매구분), IsuNo(종목번호), OrdPrc(주문가격) 입력
            header (Optional[CSPBQ00200RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPBQ00200: 증거금률별 주문가능수량 조회 인스턴스 (.req() 호출로 실행)
        """

        request_data = CSPBQ00200Request(
            body={
                "CSPBQ00200InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPBQ00200(request_data)

    현물계좌증거금률별주문가능수량조회 = cspbq00200
    현물계좌증거금률별주문가능수량조회.__doc__ = "현물계좌 증거금률별 주문가능수량 및 주문가능금액을 조회합니다."

    @require_korean_alias
    def t0424(
        self,
        body: T0424InBlock = None,
        header: Optional[T0424RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT0424:
        """
        계좌 내 보유 종목별 잔고수량, 평가금액, 손익 등을 조회합니다.

        cts_expcode 기반 연속조회를 지원합니다.

        Args:
            body (T0424InBlock): prcgb(단가구분), chegb(체결구분), dangb(단일가구분), charge(제비용포함) 입력
            header (Optional[T0424RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT0424: 주식잔고2 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """
        if body is None:
            body = T0424InBlock()

        request_data = T0424Request(
            body={
                "t0424InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT0424(request_data)

    주식잔고2 = t0424
    주식잔고2.__doc__ = "계좌 내 보유 종목별 잔고수량, 평가금액, 손익 등을 조회합니다."

    @require_korean_alias
    def t0425(
        self,
        body: T0425InBlock = None,
        header: Optional[T0425RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT0425:
        """
        당일 주문별 체결수량, 미체결잔량, 주문상태를 조회합니다.

        cts_ordno 기반 연속조회를 지원합니다.

        Args:
            body (T0425InBlock): expcode(종목번호), chegb(체결구분), medosu(매매구분), sortgb(정렬순서) 입력
            header (Optional[T0425RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT0425: 주식체결/미체결 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """
        if body is None:
            body = T0425InBlock()

        request_data = T0425Request(
            body={
                "t0425InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT0425(request_data)

    주식체결미체결 = t0425
    주식체결미체결.__doc__ = "당일 주문별 체결수량, 미체결잔량, 주문상태를 조회합니다."

    def account_tracker(
        self,
        real_client,
        refresh_interval: int = 60,
        commission_rate=None,
    ):
        """
        계좌 추적기 생성 (보유종목, 예수금, 미체결 실시간 추적)

        Args:
            real_client: 실시간 클라이언트 (korea_stock().real()) - 필수
            refresh_interval: API 갱신 주기 (초, 기본 60초)
            commission_rate: 수수료율 (None이면 0.015%)

        Returns:
            KrStockAccountTracker: 계좌 추적기 인스턴스

        Example:
            ```python
            real = korea_stock().real()
            await real.connect()

            tracker = accno.account_tracker(real_client=real)
            await tracker.start()

            tracker.on_position_change(lambda positions: print(positions))
            tracker.on_balance_change(lambda balance: print(balance))

            await tracker.stop()
            ```
        """
        from ..extension import KrStockAccountTracker

        return KrStockAccountTracker(
            accno_client=self,
            real_client=real_client,
            refresh_interval=refresh_interval,
            commission_rate=commission_rate,
        )

    계좌추적기 = account_tracker
    계좌추적기.__doc__ = "계좌 실시간 추적기를 생성합니다."


__init__ = [
    Accno,
    TrCSPAQ22200,
    TrCSPAQ12300,
    TrCSPAQ13700,
    TrCDPCQ04700,
    TrFOCCQ33600,
    TrCSPAQ12200,
    TrCSPAQ00600,
    TrCSPBQ00200,
    TrT0424,
    TrT0425,
]
