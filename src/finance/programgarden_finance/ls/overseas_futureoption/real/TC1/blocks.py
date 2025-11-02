from typing import Literal, Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class TC1RealRequestHeader(BlockRealRequestHeader):
    pass


class TC1RealResponseHeader(BlockRealResponseHeader):
    # response header requires tr_cd
    tr_cd: str = Field(..., title="거래 CD", description="LS증권 거래코드")


class TC1RealRequestBody(BaseModel):
    tr_cd: str = Field("TC1", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드")


class TC1RealRequest(BaseModel):
    header: TC1RealRequestHeader = Field(
        TC1RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록",
        description="TC1 API 요청을 위한 헤더 데이터 블록"
    )
    body: TC1RealRequestBody = Field(
        ...,
        title="입력 데이터 블록",
        description="TC1 입력 데이터 블록",
    )


class TC1RealResponseBody(BaseModel):
    lineseq: str = Field(..., title="라인일련번호")
    """라인일련번호"""
    key: str = Field(..., title="KEY")
    """KEY"""
    user: str = Field(..., title="조작자ID")
    """조작자ID"""
    svc_id: str = Field(..., title="서비스ID HO01:주문ACK HO04:주문Pending")
    """서비스ID HO01:주문ACK HO04:주문Pending"""
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
    ordr_typ_cd: Literal["1", "2", "3", "4"] = Field(..., title="주문유형코드 1:시장가 2:지정가 3:Stop Market 4:Stop Limit")
    """주문유형코드 1:시장가 2:지정가 3:Stop Market 4:Stop Limit"""
    ordr_typ_prd_ccd: str = Field(..., title="주문기간코드")
    """주문기간코드"""
    ordr_aplc_strt_dt: str = Field(..., title="주문적용시작일자")
    """주문적용시작일자"""
    ordr_aplc_end_dt: str = Field(..., title="주문적용종료일자")
    """주문적용종료일자"""
    ordr_prc: float = Field(..., title="주문가격")
    """주문가격"""
    cndt_ordr_prc: float = Field(..., title="주문조건가격")
    """주문조건가격"""
    ordr_q: int = Field(..., title="주문수량")
    """주문수량"""
    ordr_tm: str = Field(..., title="주문시간")
    """주문시간"""
    userid: str = Field(..., title="사용자ID")
    """사용자ID"""


class TC1RealResponse(BaseModel):
    header: Optional[TC1RealResponseHeader]
    body: Optional[TC1RealResponseBody]

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
