from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ22200RequestHeader(BlockRequestHeader):
    """CSPAQ22200 요청용 Header"""
    pass


class CSPAQ22200ResponseHeader(BlockResponseHeader):
    """CSPAQ22200 응답용 Header"""
    pass


class CSPAQ22200InBlock1(BaseModel):
    """
    CSPAQ22200InBlock1 - 현물계좌예수금 주문가능금액 총평가2 입력 블록

    계좌의 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다.

    Attributes:
        BalCreTp (str): 잔고생성구분 (0:주식잔고, 1:기타, 2:재투자잔고, 3:유통대주, 4:자기융자, 5:유통대주, 6:자기대주)
    """
    BalCreTp: Literal["0", "1", "2", "3", "4", "5", "6"] = Field(
        default="0",
        title="잔고생성구분",
        description="0:주식잔고 1:기타 2:재투자잔고 3:유통대주 4:자기융자 5:유통대주 6:자기대주"
    )
    """ 잔고생성구분 (0:주식잔고) """


class CSPAQ22200Request(BaseModel):
    """
    CSPAQ22200 API 요청 - 현물계좌예수금 주문가능금액 총평가2

    Attributes:
        header (CSPAQ22200RequestHeader)
        body (dict[Literal["CSPAQ22200InBlock1"], CSPAQ22200InBlock1])
    """
    header: CSPAQ22200RequestHeader = CSPAQ22200RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ22200",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAQ22200InBlock1"], CSPAQ22200InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ22200"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAQ22200OutBlock1(BaseModel):
    """
    CSPAQ22200OutBlock1 - 입력 echo-back 블록

    Attributes:
        RecCnt (int): 레코드갯수
        MgmtBrnNo (str): 관리지점번호
        BalCreTp (str): 잔고생성구분
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    MgmtBrnNo: str = Field(default="", title="관리지점번호", description="관리지점번호 (현재 미사용)")
    """ 관리지점번호 (현재 미사용) """
    BalCreTp: str = Field(default="0", title="잔고생성구분", description="0:주식잔고 1:기타 2:재투자잔고 3:유통대주 4:자기융자 5:유통대주 6:자기대주")
    """ 잔고생성구분 """


class CSPAQ22200OutBlock2(BaseModel):
    """
    CSPAQ22200OutBlock2 - 현물계좌예수금 주문가능금액 총평가2 응답 블록

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
    SubstOrdAbleAmt: int = Field(default=0, title="대용주문가능금액", description="대용주문가능금액")
    """ 대용주문가능금액 """
    SeOrdAbleAmt: int = Field(default=0, title="거래소금액", description="거래소금액")
    """ 거래소금액 """
    KdqOrdAbleAmt: int = Field(default=0, title="코스닥금액", description="코스닥금액")
    """ 코스닥금액 """
    CrdtPldgOrdAmt: int = Field(default=0, title="신용담보주문금액", description="신용담보주문금액")
    """ 신용담보주문금액 """
    MgnRat100pctOrdAbleAmt: int = Field(
        default=0,
        title="미수주문가능금액 (Order-able amount eligible for 미수 / credit ordering)",
        description=(
            "Order-able amount eligible for 미수주문 (missed-payment / credit ordering). "
            "Field semantic was changed by LS Securities on 2026-04-11 12:00 KST: "
            "until 2026-04-10 this field held 증거금률 100% 주문가능 금액 (100% margin-rate "
            "order-able amount). From 2026-04-11 onward, the legacy 증거금률 100% value is "
            "exposed by RcvblUablOrdAbleAmt instead. Callers needing the 증거금률 100% "
            "semantic must migrate to RcvblUablOrdAbleAmt. The Korean field title was also "
            "updated upstream to reflect the new semantic. in KRW. Length 16. "
            "Pydantic auto-coerces."
        ),
        examples=[306, 0, 100000],
    )
    """ 미수주문가능금액 (의미 변경: 2026-04-11 LS Securities) """
    MgnRat35ordAbleAmt: int = Field(default=0, title="증거금률35%주문가능금액", description="증거금률35%주문가능금액")
    """ 증거금률35%주문가능금액 """
    MgnRat50ordAbleAmt: int = Field(default=0, title="증거금률50%주문가능금액", description="증거금률50%주문가능금액")
    """ 증거금률50%주문가능금액 """
    CrdtOrdAbleAmt: int = Field(default=0, title="신용주문가능금액", description="신용주문가능금액")
    """ 신용주문가능금액 """
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
    RcvblAmt: int = Field(default=0, title="미수금액", description="미수금액")
    """ 미수금액 """
    D1ovdRepayRqrdAmt: int = Field(default=0, title="D1연체변제소요금액", description="D1연체변제소요금액")
    """ D1연체변제소요금액 """
    D2ovdRepayRqrdAmt: int = Field(default=0, title="D2연체변제소요금액", description="D2연체변제소요금액")
    """ D2연체변제소요금액 """
    MloanAmt: int = Field(default=0, title="융자금액", description="융자금액")
    """ 융자금액 """
    ChgAfPldgRat: float = Field(default=0.0, title="변경후담보비율", description="변경후담보비율")
    """ 변경후담보비율 """
    RqrdPldgAmt: int = Field(default=0, title="소요담보금액", description="소요담보금액")
    """ 소요담보금액 """
    PdlckAmt: int = Field(default=0, title="담보부족금액", description="담보부족금액")
    """ 담보부족금액 """
    OrgPldgSumAmt: int = Field(default=0, title="원담보합계금액", description="원담보합계금액")
    """ 원담보합계금액 """
    SubPldgSumAmt: int = Field(default=0, title="부담보합계금액", description="부담보합계금액")
    """ 부담보합계금액 """
    CrdtPldgAmtMny: int = Field(default=0, title="신용담보금현금", description="신용담보금현금")
    """ 신용담보금현금 """
    CrdtPldgSubstAmt: int = Field(default=0, title="신용담보대용금액", description="신용담보대용금액")
    """ 신용담보대용금액 """
    Imreq: int = Field(default=0, title="신용설정보증금", description="신용설정보증금")
    """ 신용설정보증금 """
    CrdtPldgRuseAmt: int = Field(default=0, title="신용담보재사용금액", description="신용담보재사용금액")
    """ 신용담보재사용금액 """
    DpslRestrcAmt: int = Field(default=0, title="처분제한금액", description="처분제한금액")
    """ 처분제한금액 """
    PrdaySellAdjstAmt: int = Field(default=0, title="전일매도정산금액", description="전일매도정산금액")
    """ 전일매도정산금액 """
    PrdayBuyAdjstAmt: int = Field(default=0, title="전일매수정산금액", description="전일매수정산금액")
    """ 전일매수정산금액 """
    CrdaySellAdjstAmt: int = Field(default=0, title="금일매도정산금액", description="금일매도정산금액")
    """ 금일매도정산금액 """
    CrdayBuyAdjstAmt: int = Field(default=0, title="금일매수정산금액", description="금일매수정산금액")
    """ 금일매수정산금액 """
    CslLoanAmtdt1: int = Field(default=0, title="매도대금담보대출금액", description="매도대금담보대출금액")
    """ 매도대금담보대출금액 """
    RcvblUablOrdAbleAmt: int = Field(
        default=0,
        title="미수불가주문가능금액 (Order-able amount disallowing 미수 / credit ordering)",
        description=(
            "Order-able amount that disallows 미수 (missed-payment / credit) usage. "
            "Added by LS Securities on 2026-04-11. From 2026-04-11 12:00 KST onward, "
            "this field carries the legacy 증거금률 100% 주문가능 금액 (100% margin-rate "
            "order-able amount) that was previously exposed by MgnRat100pctOrdAbleAmt. "
            "Callers that previously read MgnRat100pctOrdAbleAmt for 증거금률 100% semantics "
            "must migrate to this field. in KRW. Length 16. Pydantic auto-coerces."
        ),
        examples=[306, 0, 100000],
    )
    """ 미수불가주문가능금액 """


class CSPAQ22200Response(BaseModel):
    """
    CSPAQ22200 API 전체 응답 - 현물계좌예수금 주문가능금액 총평가2

    Attributes:
        header (Optional[CSPAQ22200ResponseHeader])
        block1 (Optional[CSPAQ22200OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAQ22200OutBlock2]): 예수금/주문가능금액/증거금/담보/정산금 데이터
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAQ22200ResponseHeader] = None
    block1: Optional[CSPAQ22200OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAQ22200OutBlock2] = Field(
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
