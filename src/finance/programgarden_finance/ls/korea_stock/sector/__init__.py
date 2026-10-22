
import warnings
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager

# 업종(indtp) 3 TR(t1511/t1514/t1516)은 신규 최상위 도메인 ls.업종()/ls.indtp() 로
# 이전되었습니다. 아래 메서드는 하위호환 deprecation 위임 shim 으로만 남습니다.
from programgarden_finance.ls.indtp import Indtp
from programgarden_finance.ls.indtp.t1511 import TrT1511
from programgarden_finance.ls.indtp.t1511.blocks import T1511InBlock, T1511RequestHeader
from programgarden_finance.ls.indtp.t1514 import TrT1514
from programgarden_finance.ls.indtp.t1514.blocks import T1514InBlock, T1514RequestHeader
from programgarden_finance.ls.indtp.t1516 import TrT1516
from programgarden_finance.ls.indtp.t1516.blocks import T1516InBlock, T1516RequestHeader

from . import t1531
from .t1531 import TrT1531
from .t1531.blocks import T1531InBlock, T1531Request, T1531RequestHeader
from . import t1532
from .t1532 import TrT1532
from .t1532.blocks import T1532InBlock, T1532Request, T1532RequestHeader
from . import t1537
from .t1537 import TrT1537
from .t1537.blocks import T1537InBlock, T1537Request, T1537RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Sector:
    """
    국내 주식 테마를 조회하는 Sector 클래스입니다.

    API 엔드포인트: /stock/sector (테마 t1531/t1532/t1537).
    업종(t1511/t1514/t1516)은 ls.업종()(/indtp/market-data) 로 이전되었으며,
    아래 업종 메서드는 deprecation 위임 shim 으로만 남습니다.
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1511(
        self,
        body: T1511InBlock,
        header: Optional[T1511RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1511:
        """[deprecated] ls.업종().업종현재가() 로 이전됨. ls.국내주식().업종테마() 경유는 finance 2.0 에서 제거됩니다."""
        warnings.warn(
            "ls.국내주식().업종테마().업종현재가() 는 deprecated 입니다. "
            "ls.업종().업종현재가() 로 이전됨 (finance 2.0 에서 제거).",
            DeprecationWarning, stacklevel=2,
        )
        return Indtp(token_manager=self.token_manager).t1511(body, header, options)

    업종현재가 = t1511
    업종현재가.__doc__ = "[deprecated] ls.업종().업종현재가() 로 이전됨"

    @require_korean_alias
    def t1514(
        self,
        body: T1514InBlock,
        header: Optional[T1514RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1514:
        """[deprecated] ls.업종().업종기간별추이() 로 이전됨. ls.국내주식().업종테마() 경유는 finance 2.0 에서 제거됩니다."""
        warnings.warn(
            "ls.국내주식().업종테마().업종기간별추이() 는 deprecated 입니다. "
            "ls.업종().업종기간별추이() 로 이전됨 (finance 2.0 에서 제거).",
            DeprecationWarning, stacklevel=2,
        )
        return Indtp(token_manager=self.token_manager).t1514(body, header, options)

    업종기간별추이 = t1514
    업종기간별추이.__doc__ = "[deprecated] ls.업종().업종기간별추이() 로 이전됨"

    @require_korean_alias
    def t1516(
        self,
        body: T1516InBlock,
        header: Optional[T1516RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1516:
        """[deprecated] ls.업종().업종별종목시세() 로 이전됨. ls.국내주식().업종테마() 경유는 finance 2.0 에서 제거됩니다."""
        warnings.warn(
            "ls.국내주식().업종테마().업종별종목시세() 는 deprecated 입니다. "
            "ls.업종().업종별종목시세() 로 이전됨 (finance 2.0 에서 제거).",
            DeprecationWarning, stacklevel=2,
        )
        return Indtp(token_manager=self.token_manager).t1516(body, header, options)

    업종별종목시세 = t1516
    업종별종목시세.__doc__ = "[deprecated] ls.업종().업종별종목시세() 로 이전됨"

    @require_korean_alias
    def t1531(
        self,
        body: T1531InBlock,
        header: Optional[T1531RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1531:
        """
        테마별종목을 조회합니다.

        테마명 또는 테마코드로 전체 테마 리스트 및 평균등락률을 조회합니다.

        Args:
            body (T1531InBlock): tmname(테마명), tmcode(테마코드) 입력
            header (Optional[T1531RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1531: 테마별종목 조회 인스턴스
        """

        request_data = T1531Request(
            body={
                "t1531InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1531(request_data)

    테마별종목 = t1531
    테마별종목.__doc__ = "테마별 종목 리스트 및 평균등락률을 조회합니다."

    @require_korean_alias
    def t1532(
        self,
        body: T1532InBlock,
        header: Optional[T1532RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1532:
        """
        종목별테마를 조회합니다.

        종목코드로 해당 종목이 속한 테마 리스트를 조회합니다.

        Args:
            body (T1532InBlock): shcode(종목코드) 입력
            header (Optional[T1532RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1532: 종목별테마 조회 인스턴스
        """

        request_data = T1532Request(
            body={
                "t1532InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1532(request_data)

    종목별테마 = t1532
    종목별테마.__doc__ = "종목코드로 해당 종목이 속한 테마 리스트를 조회합니다."

    @require_korean_alias
    def t1537(
        self,
        body: T1537InBlock,
        header: Optional[T1537RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1537:
        """
        테마종목별시세를 조회합니다.

        테마코드로 해당 테마에 속한 종목들의 시세를 조회합니다.

        Args:
            body (T1537InBlock): tmcode(테마코드) 입력
            header (Optional[T1537RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1537: 테마종목별시세 조회 인스턴스
        """

        request_data = T1537Request(
            body={
                "t1537InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1537(request_data)

    테마종목별시세 = t1537
    테마종목별시세.__doc__ = "테마코드로 해당 테마 종목들의 시세(현재가, 등락률, 거래량, 시가총액)를 조회합니다."


__all__ = [
    Sector,
    t1531,
    t1532,
    t1537,
]
