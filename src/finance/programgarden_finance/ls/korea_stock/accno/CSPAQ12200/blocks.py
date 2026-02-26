from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ12200RequestHeader(BlockRequestHeader):
    """CSPAQ12200 요청용 Header"""
    pass


class CSPAQ12200ResponseHeader(BlockResponseHeader):
    """CSPAQ12200 응답용 Header"""
    pass


class CSPAQ12200InBlock1(BaseModel):
    """
    CSPAQ12200InBlock1 - 현물계좌예수금 주문가능금액 총평가조회 입력 블록

    계좌의 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다.

    Attributes:
        BalCreTp (str): 잔고생성구분 (0:주식잔고, 1:기타, 2:재투자잔고, 3:유통대주, 4:자기융자, 5:유통대주, 6:자기대주)
    """
    BalCreTp: str = Field(
        default="0",
        title="잔고생성구분",
        description="0:주식잔고 1:기타 2:재투자잔고 3:유통대주 4:자기융자 5:유통대주 6:자기대주"
    )
    """ 잔고생성구분 (0:주식잔고) """


class CSPAQ12200Request(BaseModel):
    """
    CSPAQ12200 API 요청 - 현물계좌예수금 주문가능금액 총평가조회

    Attributes:
        header (CSPAQ12200RequestHeader)
        body (dict[Literal["CSPAQ12200InBlock1"], CSPAQ12200InBlock1])
    """
    header: CSPAQ12200RequestHeader = CSPAQ12200RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ12200",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAQ12200InBlock1"], CSPAQ12200InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ12200"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAQ12200OutBlock1(BaseModel):
    """
    CSPAQ12200OutBlock1 - 입력 echo-back 블록

    Attributes:
        RecCnt (int): 레코드갯수
        MgmtBrnNo (str): 관리지점번호
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        BalCreTp (str): 잔고생성구분
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    MgmtBrnNo: str = Field(default="", title="관리지점번호", description="관리지점번호")
    """ 관리지점번호 """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """ 계좌번호 """
    Pwd: str = Field(default="", title="비밀번호", description="비밀번호")
    """ 비밀번호 """
    BalCreTp: str = Field(default="0", title="잔고생성구분", description="0:주식잔고 1:기타 2:재투자잔고 3:유통대주 4:자기융자 5:유통대주 6:자기대주")
    """ 잔고생성구분 """


class CSPAQ12200OutBlock2(BaseModel):
    """
    CSPAQ12200OutBlock2 - 현물계좌예수금 주문가능금액 총평가조회 응답 블록

    계좌의 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 제공합니다.
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    BrnNm: str = Field(default="", title="지점명", description="지점명")
    """ 지점명 """
    AcntNm: str = Field(default="", title="계좌명", description="계좌명")
    """ 계좌명 """
    MnyOrdAbleAmt: int = Field(default=0, title="현금주문가능금액", description="현금주문가능금액")
    """ 현금주문가능금액 """
    MnyoutAbleAmt: int = Field(default=0, title="현금출금가능금액", description="현금출금가능금액")
    """ 현금출금가능금액 """
    SubstOrdAbleAmt: int = Field(default=0, title="대용주문가능금액", description="대용주문가능금액")
    """ 대용주문가능금액 """
    Dps: int = Field(default=0, title="예수금", description="예수금")
    """ 예수금 """
    SubstAmt: int = Field(default=0, title="대용금액", description="대용금액")
    """ 대용금액 """
    MgnMny: int = Field(default=0, title="증거금현금", description="증거금현금")
    """ 증거금현금 """
    MgnSubst: int = Field(default=0, title="증거금대용", description="증거금대용")
    """ 증거금대용 """
    D1Dps: int = Field(default=0, title="D1예수금", description="D1예수금")
    """ D1예수금 """
    D2Dps: int = Field(default=0, title="D2예수금", description="D2예수금")
    """ D2예수금 """
    BalEvalAmt: int = Field(default=0, title="잔고평가금액", description="잔고평가금액")
    """ 잔고평가금액 """
    DpsastSum: int = Field(default=0, title="예탁자산합계", description="예탁자산합계")
    """ 예탁자산합계 """
    InvstOrgAmt: int = Field(default=0, title="투자원금", description="투자원금")
    """ 투자원금 """
    InvstPlAmt: int = Field(default=0, title="투자손익금액", description="투자손익금액")
    """ 투자손익금액 """
    PnlRat: float = Field(default=0.0, title="손익율", description="손익율")
    """ 손익율 """
    InvstAsm: int = Field(default=0, title="투자누계금액", description="투자누계금액")
    """ 투자누계금액 """
    RcvblAmt: int = Field(default=0, title="미수금액", description="미수금액")
    """ 미수금액 """
    CrdtPldgRuseAmt: int = Field(default=0, title="신용담보재사용금액", description="신용담보재사용금액")
    """ 신용담보재사용금액 """
    DpslRestrcAmt: int = Field(default=0, title="처분제한금액", description="처분제한금액")
    """ 처분제한금액 """
    MnyoutAbleAmt2: int = Field(default=0, title="현금출금가능금액2", description="현금출금가능금액2")
    """ 현금출금가능금액2 """
    SeOrdAbleAmt: int = Field(default=0, title="거래소주문가능금액", description="거래소주문가능금액")
    """ 거래소주문가능금액 """
    KdqOrdAbleAmt: int = Field(default=0, title="코스닥주문가능금액", description="코스닥주문가능금액")
    """ 코스닥주문가능금액 """
    MgnRat100pctOrdAbleAmt: int = Field(default=0, title="증거금률100퍼센트주문가능금액", description="증거금률100퍼센트주문가능금액")
    """ 증거금률100퍼센트주문가능금액 """
    CrdtOrdAbleAmt: int = Field(default=0, title="신용주문가능금액", description="신용주문가능금액")
    """ 신용주문가능금액 """
    MgnRat35ordAbleAmt: int = Field(default=0, title="증거금률35%주문가능금액", description="증거금률35%주문가능금액")
    """ 증거금률35%주문가능금액 """
    MgnRat50ordAbleAmt: int = Field(default=0, title="증거금률50%주문가능금액", description="증거금률50%주문가능금액")
    """ 증거금률50%주문가능금액 """
    PrdaySellAdjstAmt: int = Field(default=0, title="전일매도정산금액", description="전일매도정산금액")
    """ 전일매도정산금액 """
    PrdayBuyAdjstAmt: int = Field(default=0, title="전일매수정산금액", description="전일매수정산금액")
    """ 전일매수정산금액 """
    CrdaySellAdjstAmt: int = Field(default=0, title="금일매도정산금액", description="금일매도정산금액")
    """ 금일매도정산금액 """
    CrdayBuyAdjstAmt: int = Field(default=0, title="금일매수정산금액", description="금일매수정산금액")
    """ 금일매수정산금액 """
    D1ovdRepayRqrdAmt: int = Field(default=0, title="D1연체변제소요금액", description="D1연체변제소요금액")
    """ D1연체변제소요금액 """
    D2ovdRepayRqrdAmt: int = Field(default=0, title="D2연체변제소요금액", description="D2연체변제소요금액")
    """ D2연체변제소요금액 """
    D1MloanAmt: int = Field(default=0, title="D1융자금액", description="D1융자금액")
    """ D1융자금액 """
    D2MloanAmt: int = Field(default=0, title="D2융자금액", description="D2융자금액")
    """ D2융자금액 """
    RcvblSumAmt: int = Field(default=0, title="미수합계금액", description="미수합계금액")
    """ 미수합계금액 """
    PldgSumAmt: int = Field(default=0, title="담보합계금액", description="담보합계금액")
    """ 담보합계금액 """
    DpsastTotamt: int = Field(default=0, title="예탁자산총금액", description="예탁자산총금액")
    """ 예탁자산총금액 """
    Imreq: int = Field(default=0, title="신용설정보증금", description="신용설정보증금")
    """ 신용설정보증금 """


class CSPAQ12200Response(BaseModel):
    """
    CSPAQ12200 API 전체 응답 - 현물계좌예수금 주문가능금액 총평가조회

    Attributes:
        header (Optional[CSPAQ12200ResponseHeader])
        block1 (Optional[CSPAQ12200OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAQ12200OutBlock2]): 예수금/주문가능금액/증거금/담보/정산금 데이터
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAQ12200ResponseHeader] = None
    block1: Optional[CSPAQ12200OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAQ12200OutBlock2] = Field(
        None,
        title="예수금/주문가능금액 데이터",
        description="현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황"
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
