from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class TC3RealRequestHeader(BlockRealRequestHeader):
    pass


class TC3RealResponseHeader(BlockRealResponseHeader):
    pass


class TC3RealRequestBody(BaseModel):
    tr_cd: str = Field("TC3", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드")


class TC3RealRequest(BaseModel):
    header: TC3RealRequestHeader = Field(
        TC3RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록",
        description="TC3 API 요청을 위한 헤더 데이터 블록"
    )
    body: TC3RealRequestBody = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 주문체결 입력 데이터 블록",
    )


class TC3RealResponseBody(BaseModel):
    lineseq: str = Field(..., title="라인일련번호")
    """라인일련번호"""

    key: str = Field(..., title="KEY")
    """KEY"""

    user: str = Field(..., title="조작자ID")
    """조작자ID"""

    svc_id: str = Field(..., title="서비스ID CH01")
    """서비스ID CH01"""

    ordr_dt: str = Field(..., title="주문일자")
    """주문일자 (YYYYMMDD 형식)"""

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

    ccls_q: str = Field(..., title="체결수량")
    """체결 수량"""

    ccls_prc: str = Field(..., title="체결가격")
    """체결 가격"""

    ccls_no: str = Field(..., title="체결번호")
    """체결번호"""

    ccls_tm: str = Field(..., title="체결시간")
    """체결시간 (HHMMSS 형식)"""

    avg_byng_uprc: str = Field(..., title="매입평균단가")
    """매입 평균 단가"""

    byug_amt: str = Field(..., title="매입금액")
    """매입 금액"""

    clr_pl_amt: str = Field(..., title="청산손익")
    """청산 손익"""

    ent_fee: str = Field(..., title="위탁수수료")
    """위탁 수수료"""

    fcm_fee: str = Field(..., title="매입잔고수량")
    """매입 잔고 수량 (또는 FCM 수수료 필드)"""

    userid: str = Field(..., title="사용자ID")
    """사용자 ID"""

    now_prc: str = Field(..., title="현재가격")
    """현재 가격"""

    crncy_cd: str = Field(..., title="통화코드")
    """통화 코드 (예: USD, KRW 등)"""

    mtrt_dt: str = Field(..., title="만기일자")
    """만기일자 (YYYYMMDD 형식)"""

    ord_prdt_tp_code: str = Field(..., title="주문상품구분코드")
    """주문 상품 구분 코드"""

    exec_prdt_tp_code: str = Field(..., title="주문상품구분코드")
    """실행 상품 구분 코드"""

    sprd_base_isu_yn: str = Field(..., title="스프레드종목여부")
    """스프레드 종목 여부 (Y/N)"""

    ccls_dt: str = Field(..., title="체결일자")
    """체결일자 (YYYYMMDD 형식)"""

    filler2: str = Field(..., title="FILLER2")
    """예비 필드 (FILLER2)"""

    sprd_is_cd: str = Field(..., title="스프레드종목코드")
    """스프레드 종목 코드"""

    lme_prdt_ccd: str = Field(..., title="LME상품유형")
    """LME 상품 유형 코드"""

    lme_sprd_prc: str = Field(..., title="LME스프레드가격")
    """LME 스프레드 가격"""

    last_now_prc: str = Field(..., title="최종현재가격")
    """최종 현재 가격"""

    bf_mtrt_dt: str = Field(..., title="이전만기일자")
    """이전 만기일자 (YYYYMMDD 형식)"""

    clr_q: str = Field(..., title="청산수량")
    """청산 수량"""


class TC3RealResponse(BaseModel):
    header: Optional[TC3RealResponseHeader]
    body: Optional[TC3RealResponseBody]

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
