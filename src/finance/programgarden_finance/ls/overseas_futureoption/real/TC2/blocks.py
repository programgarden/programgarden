from typing import Literal, Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class TC2RealRequestHeader(BlockRealRequestHeader):
    pass


class TC2RealResponseHeader(BlockRealResponseHeader):
    tr_cd: str = Field(..., title="거래 CD")


class TC2RealRequestBody(BaseModel):
    tr_cd: str = Field("TC2", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드")


class TC2RealRequest(BaseModel):
    """
    해외선물 주문응답 실시간 요청
    """
    header: TC2RealRequestHeader = Field(
        TC2RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록",
        description="TC2 API 요청을 위한 헤더 데이터 블록"
    )
    body: TC2RealRequestBody = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 주문응답 입력 데이터 블록",
    )


class TC2RealResponseBody(BaseModel):
    lineseq: str = Field(..., title="라인일련번호")
    """라인일련번호"""
    key: str = Field(..., title="KEY")
    """KEY"""
    user: str = Field(..., title="조작자ID")
    """조작자ID"""
    svc_id: str = Field(..., title="서비스ID HO02:확인 HO03:거부")
    """서비스ID HO02:확인 HO03:거부"""
    ordr_dt: str = Field(..., title="주문일자")
    """주문일자"""
    brn_cd: str = Field(..., title="지점번호")
    """지점번호"""
    ordr_no: str = Field(..., title="주문번호")
    """주문번호"""
    orgn_ordr_no: str = Field(..., title="원주문번호")
    """원주문번호"""
    mthr_ordr_no: str = Field(..., title="모주문번호")
    """모주문번호"""
    ac_no: str = Field(..., title="계좌번호")
    """계좌번호"""
    is_cd: str = Field(..., title="종목코드")
    """종목코드"""
    s_b_ccd: str = Field(..., title="매도매수유형 1:매도 2:매수")
    """매도매수유형 1:매도 2:매수"""
    ordr_ccd: str = Field(..., title="정정취소유형 1:신규 2:정정 3:취소")
    """정정취소유형 1:신규 2:정정 3:취소"""
    ordr_typ_cd: Literal["1", "2", "3", "4"] = Field(..., title="주문유형코드")
    """주문유형코드 1:시장가 2:지정가 3:Stop Market 4:Stop Limit"""
    ordr_typ_prd_ccd: str = Field(..., title="주문기간코드")
    """주문기간 코드"""
    ordr_aplc_strt_dt: str = Field(..., title="주문적용시작일자")
    """주문 적용 시작일자"""
    ordr_aplc_end_dt: str = Field(..., title="주문적용종료일자")
    """주문 적용 종료일자"""
    ordr_prc: str = Field(..., title="주문가격")
    """주문 가격"""
    cndt_ordr_prc: str = Field(..., title="주문조건가격")
    """주문 조건 가격"""
    ordr_q: str = Field(..., title="주문수량")
    """주문 수량"""
    ordr_tm: str = Field(..., title="주문시간")
    """주문 시간"""
    cnfr_q: str = Field(..., title="호가확인수량")
    """호가 확인 수량"""
    rfsl_cd: str = Field(..., title="호가거부사유코드")
    """호가 거부 사유 코드"""
    text: str = Field(..., title="호가거부사유코드명")
    """호가 거부 사유 코드명"""
    userid: str = Field(..., title="사용자ID")
    """사용자ID"""


class TC2RealResponse(BaseModel):
    header: Optional[TC2RealResponseHeader]
    body: Optional[TC2RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드")
    rsp_msg: str = Field(..., title="응답 메시지")
    error_msg: Optional[str] = Field(None, title="오류 메시지")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
