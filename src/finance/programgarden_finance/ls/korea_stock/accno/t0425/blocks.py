from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T0425RequestHeader(BlockRequestHeader):
    """t0425 요청용 Header"""
    pass


class T0425ResponseHeader(BlockResponseHeader):
    """t0425 응답용 Header"""
    pass


class T0425InBlock(BaseModel):
    """
    t0425InBlock - 주식 체결/미체결 입력 블록

    종목번호, 체결구분, 매매구분, 정렬순서와
    연속조회키(cts_ordno)로 당일 주문 내역을 조회합니다.

    Attributes:
        expcode (str): 종목번호 (비워두면 전종목)
        chegb (str): 체결구분 (0:전체 1:체결 2:미체결)
        medosu (str): 매매구분 (0:전체 1:매도 2:매수)
        sortgb (str): 정렬순서 (1:주문번호 역순 2:주문번호 순)
        cts_ordno (str): 주문번호CTS (연속조회시 OutBlock의 동일필드 입력)
    """
    expcode: str = Field(
        default="",
        title="종목번호",
        description="종목번호 (비워두면 전종목)"
    )
    """ 종목번호 (비워두면 전종목) """
    chegb: Literal["0", "1", "2"] = Field(
        default="0",
        title="체결구분",
        description="0:전체 1:체결 2:미체결"
    )
    """ 체결구분 (0:전체 1:체결 2:미체결) """
    medosu: Literal["0", "1", "2"] = Field(
        default="0",
        title="매매구분",
        description="0:전체 1:매도 2:매수"
    )
    """ 매매구분 (0:전체 1:매도 2:매수) """
    sortgb: Literal["1", "2"] = Field(
        default="1",
        title="정렬순서",
        description="1:주문번호 역순 2:주문번호 순"
    )
    """ 정렬순서 (1:주문번호 역순 2:주문번호 순) """
    cts_ordno: str = Field(
        default="",
        title="주문번호CTS",
        description="연속조회시 OutBlock의 동일필드 입력"
    )
    """ 주문번호CTS (연속조회키) """


class T0425Request(BaseModel):
    """
    T0425 API 요청 - 주식 체결/미체결

    Attributes:
        header (T0425RequestHeader)
        body (Dict[Literal["t0425InBlock"], T0425InBlock])
        options (SetupOptions)
    """
    header: T0425RequestHeader = T0425RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t0425",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t0425InBlock"], T0425InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t0425"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T0425OutBlock(BaseModel):
    """
    t0425OutBlock - 주식 체결/미체결 합산 블록

    당일 주문 전체에 대한 총수량, 총체결수량, 추정수수료 등 합산 정보와
    연속조회키(cts_ordno)를 반환합니다.

    Attributes:
        tqty (int): 총주문수량
        tcheqty (int): 총체결수량
        tordrem (int): 총미체결수량
        cmss (int): 추정수수료
        tamt (int): 총주문금액
        tmdamt (int): 총매도체결금액
        tmsamt (int): 총매수체결금액
        tax (int): 추정제세금
        cts_ordno (str): 주문번호CTS (연속조회키)
    """
    tqty: int = Field(default=0, title="총주문수량", description="총주문수량")
    """ 총주문수량 """
    tcheqty: int = Field(default=0, title="총체결수량", description="총체결수량")
    """ 총체결수량 """
    tordrem: int = Field(default=0, title="총미체결수량", description="총미체결수량")
    """ 총미체결수량 """
    cmss: int = Field(default=0, title="추정수수료", description="추정수수료")
    """ 추정수수료 """
    tamt: int = Field(default=0, title="총주문금액", description="총주문금액")
    """ 총주문금액 """
    tmdamt: int = Field(default=0, title="총매도체결금액", description="총매도체결금액")
    """ 총매도체결금액 """
    tmsamt: int = Field(default=0, title="총매수체결금액", description="총매수체결금액")
    """ 총매수체결금액 """
    tax: int = Field(default=0, title="추정제세금", description="추정제세금")
    """ 추정제세금 """
    cts_ordno: str = Field(default="", title="주문번호CTS", description="연속조회키")
    """ 주문번호CTS (연속조회키) """


class T0425OutBlock1(BaseModel):
    """
    t0425OutBlock1 - 주식 체결/미체결 주문별 상세 정보

    당일 주문별 체결수량, 미체결잔량, 주문상태, 호가유형 등 상세 정보를 제공합니다.

    Attributes:
        ordno (int): 주문번호
        expcode (str): 종목번호
        medosu (str): 구분 (매수/매도)
        qty (int): 주문수량
        price (int): 주문가격
        cheqty (int): 체결수량
        cheprice (int): 체결가격
        ordrem (int): 미체결잔량
        cfmqty (int): 확인수량
        status (str): 상태
        orgordno (int): 원주문번호
        ordgb (str): 유형
        ordtime (str): 주문시간
        ordermtd (str): 주문매체
        sysprocseq (int): 처리순번
        hogagb (str): 호가유형
        price1 (int): 현재가
        orggb (str): 주문구분
        singb (str): 신용구분
        loandt (str): 대출일자
        exchname (str): 거래소명
    """
    ordno: int = Field(default=0, title="주문번호", description="주문번호")
    """ 주문번호 """
    expcode: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    medosu: str = Field(default="", title="구분", description="매수/매도 구분")
    """ 구분 (매수/매도) """
    qty: int = Field(default=0, title="주문수량", description="주문수량")
    """ 주문수량 """
    price: int = Field(default=0, title="주문가격", description="주문가격")
    """ 주문가격 """
    cheqty: int = Field(default=0, title="체결수량", description="체결수량")
    """ 체결수량 """
    cheprice: int = Field(default=0, title="체결가격", description="체결가격")
    """ 체결가격 """
    ordrem: int = Field(default=0, title="미체결잔량", description="미체결잔량")
    """ 미체결잔량 """
    cfmqty: int = Field(default=0, title="확인수량", description="확인수량")
    """ 확인수량 """
    status: str = Field(default="", title="상태", description="주문 상태")
    """ 상태 """
    orgordno: int = Field(default=0, title="원주문번호", description="원주문번호")
    """ 원주문번호 """
    ordgb: str = Field(default="", title="유형", description="주문 유형")
    """ 유형 """
    ordtime: str = Field(default="", title="주문시간", description="주문시간")
    """ 주문시간 """
    ordermtd: str = Field(default="", title="주문매체", description="주문매체")
    """ 주문매체 """
    sysprocseq: int = Field(default=0, title="처리순번", description="처리순번")
    """ 처리순번 """
    hogagb: str = Field(default="", title="호가유형", description="호가유형")
    """ 호가유형 """
    price1: int = Field(default=0, title="현재가", description="현재가")
    """ 현재가 """
    orggb: str = Field(default="", title="주문구분", description="주문구분")
    """ 주문구분 """
    singb: str = Field(default="", title="신용구분", description="신용구분")
    """ 신용구분 """
    loandt: str = Field(default="", title="대출일자", description="대출일자")
    """ 대출일자 """
    exchname: str = Field(default="", title="거래소명", description="거래소명")
    """ 거래소명 """


class T0425Response(BaseModel):
    """
    T0425 API 전체 응답 - 주식 체결/미체결

    당일 주문 합산 정보(cont_block)와 주문별 상세 리스트(block)를 반환합니다.
    연속조회가 필요하면 cont_block.cts_ordno를 다음 요청의 InBlock.cts_ordno에 설정합니다.

    Attributes:
        header (Optional[T0425ResponseHeader])
        cont_block (Optional[T0425OutBlock]): 합산 정보 및 연속조회키 블록
        block (List[T0425OutBlock1]): 주문별 체결/미체결 상세 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T0425ResponseHeader] = None
    cont_block: Optional[T0425OutBlock] = Field(
        None,
        title="합산 및 연속조회 블록",
        description="총주문수량, 추정수수료 등 합산 정보와 연속조회키(cts_ordno)를 포함하는 블록"
    )
    block: List[T0425OutBlock1] = Field(
        default_factory=list,
        title="주문별 체결/미체결 상세 리스트",
        description="당일 주문별 체결수량, 미체결잔량, 주문상태 등 상세 정보 리스트"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지",
        description="오류메시지 (있으면)"
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
