from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPBQ00200RequestHeader(BlockRequestHeader):
    """CSPBQ00200 요청용 Header"""
    pass


class CSPBQ00200ResponseHeader(BlockResponseHeader):
    """CSPBQ00200 응답용 Header"""
    pass


class CSPBQ00200InBlock1(BaseModel):
    """
    CSPBQ00200InBlock1 - 현물계좌 증거금률별 주문가능수량 조회 입력 블록

    증거금률별 주문가능수량 및 주문가능금액을 조회합니다.

    Attributes:
        BnsTpCode (str): 매매구분 (1:매도, 2:매수)
        IsuNo (str): 종목번호
        OrdPrc (float): 주문가격
    """
    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="매매구분",
        description="1:매도 2:매수"
    )
    """ 매매구분 (1:매도 2:매수) """
    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목번호"
    )
    """ 종목번호 """
    OrdPrc: float = Field(
        default=0.0,
        title="주문가격",
        description="주문가격"
    )
    """ 주문가격 """


class CSPBQ00200Request(BaseModel):
    """
    CSPBQ00200 API 요청 - 현물계좌 증거금률별 주문가능수량 조회

    Attributes:
        header (CSPBQ00200RequestHeader)
        body (dict[Literal["CSPBQ00200InBlock1"], CSPBQ00200InBlock1])
    """
    header: CSPBQ00200RequestHeader = CSPBQ00200RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPBQ00200",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPBQ00200InBlock1"], CSPBQ00200InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPBQ00200"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPBQ00200OutBlock1(BaseModel):
    """
    CSPBQ00200OutBlock1 - 입력 echo-back 블록

    Attributes:
        RecCnt (int): 레코드갯수
        BnsTpCode (str): 매매구분
        AcntNo (str): 계좌번호
        InptPwd (str): 입력비밀번호
        IsuNo (str): 종목번호
        OrdPrc (float): 주문가격
        RegCommdaCode (str): 등록통신매체코드
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    BnsTpCode: str = Field(default="", title="매매구분", description="1:매도 2:매수")
    """ 매매구분 """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """ 계좌번호 """
    InptPwd: str = Field(default="", title="입력비밀번호", description="입력비밀번호")
    """ 입력비밀번호 """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    OrdPrc: float = Field(default=0.0, title="주문가격", description="주문가격")
    """ 주문가격 """
    RegCommdaCode: str = Field(default="", title="등록통신매체코드", description="등록통신매체코드")
    """ 등록통신매체코드 """


class CSPBQ00200OutBlock2(BaseModel):
    """
    CSPBQ00200OutBlock2 - 현물계좌 증거금률별 주문가능수량 조회 응답 블록

    증거금률별 주문가능수량 및 주문가능금액 정보를 제공합니다.
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    AcntNm: str = Field(default="", title="계좌명", description="계좌명")
    """ 계좌명 """
    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """ 종목명 """
    Dps: int = Field(default=0, title="예수금", description="예수금")
    """ 예수금 """
    SubstAmt: int = Field(default=0, title="대용금액", description="대용금액")
    """ 대용금액 """
    MnyOrdAbleAmt: int = Field(default=0, title="현금주문가능금액", description="현금주문가능금액")
    """ 현금주문가능금액 """
    SubstOrdAbleAmt: int = Field(default=0, title="대용주문가능금액", description="대용주문가능금액")
    """ 대용주문가능금액 """
    MnyMgn: int = Field(default=0, title="현금증거금", description="현금증거금")
    """ 현금증거금 """
    SubstMgn: int = Field(default=0, title="대용증거금", description="대용증거금")
    """ 대용증거금 """
    SeOrdAbleAmt: int = Field(default=0, title="거래소주문가능금액", description="거래소주문가능금액")
    """ 거래소주문가능금액 """
    KdqOrdAbleAmt: int = Field(default=0, title="코스닥주문가능금액", description="코스닥주문가능금액")
    """ 코스닥주문가능금액 """
    MgnRat20pctOrdAbleAmt: int = Field(default=0, title="증거금률20%주문가능금액", description="증거금률20%주문가능금액")
    """ 증거금률20%주문가능금액 """
    MgnRat25pctOrdAbleAmt: int = Field(default=0, title="증거금률25%주문가능금액", description="증거금률25%주문가능금액")
    """ 증거금률25%주문가능금액 """
    MgnRat30pctOrdAbleAmt: int = Field(default=0, title="증거금률30%주문가능금액", description="증거금률30%주문가능금액")
    """ 증거금률30%주문가능금액 """
    MgnRat35pctOrdAbleAmt: int = Field(default=0, title="증거금률35%주문가능금액", description="증거금률35%주문가능금액")
    """ 증거금률35%주문가능금액 """
    MgnRat40pctOrdAbleAmt: int = Field(default=0, title="증거금률40%주문가능금액", description="증거금률40%주문가능금액")
    """ 증거금률40%주문가능금액 """
    MgnRat50pctOrdAbleAmt: int = Field(default=0, title="증거금률50%주문가능금액", description="증거금률50%주문가능금액")
    """ 증거금률50%주문가능금액 """
    MgnRat60pctOrdAbleAmt: int = Field(default=0, title="증거금률60%주문가능금액", description="증거금률60%주문가능금액")
    """ 증거금률60%주문가능금액 """
    MgnRat100pctOrdAbleAmt: int = Field(default=0, title="증거금률100%주문가능금액", description="증거금률100%주문가능금액")
    """ 증거금률100%주문가능금액 """
    MgnRat100MnyOrdAbleAmt: int = Field(default=0, title="증거금률100%현금주문가능금액", description="증거금률100%현금주문가능금액")
    """ 증거금률100%현금주문가능금액 """
    OrdAbleQty: int = Field(default=0, title="주문가능수량", description="주문가능수량")
    """ 주문가능수량 """
    OrdAbleAmt: int = Field(default=0, title="주문가능금액", description="주문가능금액")
    """ 주문가능금액 """
    SellOrdAbleQty: int = Field(default=0, title="매도주문가능수량", description="매도주문가능수량")
    """ 매도주문가능수량 """


class CSPBQ00200Response(BaseModel):
    """
    CSPBQ00200 API 전체 응답 - 현물계좌 증거금률별 주문가능수량 조회

    Attributes:
        header (Optional[CSPBQ00200ResponseHeader])
        block1 (Optional[CSPBQ00200OutBlock1]): 입력 echo-back
        block2 (Optional[CSPBQ00200OutBlock2]): 증거금률별 주문가능수량 데이터
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPBQ00200ResponseHeader] = None
    block1: Optional[CSPBQ00200OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPBQ00200OutBlock2] = Field(
        None,
        title="증거금률별 주문가능수량 데이터",
        description="현물계좌 증거금률별 주문가능수량 및 주문가능금액 정보"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str
    rsp_msg: str
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
