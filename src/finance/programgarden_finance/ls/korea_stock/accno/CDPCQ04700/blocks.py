from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CDPCQ04700RequestHeader(BlockRequestHeader):
    """CDPCQ04700 요청용 Header"""
    pass


class CDPCQ04700ResponseHeader(BlockResponseHeader):
    """CDPCQ04700 응답용 Header"""
    pass


class CDPCQ04700InBlock1(BaseModel):
    """
    CDPCQ04700InBlock1 - 계좌 거래내역 조회 입력 블록

    Attributes:
        QryTp (str): 조회구분 (기본 "0")
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        QrySrtDt (str): 조회시작일 (YYYYMMDD)
        QryEndDt (str): 조회종료일 (YYYYMMDD)
        SrtNo (int): 시작번호 (기본 0)
        PdptnCode (str): 상품유형코드 (기본 "01")
        IsuLgclssCode (str): 종목대분류코드 (기본 "01")
        IsuNo (str): 종목번호 (기본 "")
    """
    QryTp: str = Field(
        default="0",
        title="조회구분",
        description="조회구분"
    )
    """ 조회구분 """
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """ 계좌번호 """
    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="비밀번호"
    )
    """ 비밀번호 """
    QrySrtDt: str = Field(
        default="",
        title="조회시작일",
        description="조회시작일 (YYYYMMDD)"
    )
    """ 조회시작일 """
    QryEndDt: str = Field(
        default="",
        title="조회종료일",
        description="조회종료일 (YYYYMMDD)"
    )
    """ 조회종료일 """
    SrtNo: int = Field(
        default=0,
        title="시작번호",
        description="시작번호 (페이지네이션)"
    )
    """ 시작번호 """
    PdptnCode: str = Field(
        default="01",
        title="상품유형코드",
        description="상품유형코드"
    )
    """ 상품유형코드 """
    IsuLgclssCode: str = Field(
        default="01",
        title="종목대분류코드",
        description="종목대분류코드"
    )
    """ 종목대분류코드 """
    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목번호"
    )
    """ 종목번호 """


class CDPCQ04700Request(BaseModel):
    """
    CDPCQ04700 API 요청 - 계좌 거래내역

    Attributes:
        header (CDPCQ04700RequestHeader)
        body (dict[Literal["CDPCQ04700InBlock1"], CDPCQ04700InBlock1])
    """
    header: CDPCQ04700RequestHeader = CDPCQ04700RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CDPCQ04700",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CDPCQ04700InBlock1"], CDPCQ04700InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CDPCQ04700"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CDPCQ04700OutBlock1(BaseModel):
    """
    CDPCQ04700OutBlock1 - 입력 echo-back 블록

    Attributes:
        QryTp (str): 조회구분
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        QrySrtDt (str): 조회시작일
        QryEndDt (str): 조회종료일
        SrtNo (int): 시작번호
        PdptnCode (str): 상품유형코드
        IsuLgclssCode (str): 종목대분류코드
        IsuNo (str): 종목번호
    """
    QryTp: str = Field(default="0", title="조회구분", description="조회구분")
    """ 조회구분 """
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """ 계좌번호 """
    Pwd: str = Field(default="", title="비밀번호", description="비밀번호")
    """ 비밀번호 """
    QrySrtDt: str = Field(default="", title="조회시작일", description="조회시작일 (YYYYMMDD)")
    """ 조회시작일 """
    QryEndDt: str = Field(default="", title="조회종료일", description="조회종료일 (YYYYMMDD)")
    """ 조회종료일 """
    SrtNo: int = Field(default=0, title="시작번호", description="시작번호")
    """ 시작번호 """
    PdptnCode: str = Field(default="01", title="상품유형코드", description="상품유형코드")
    """ 상품유형코드 """
    IsuLgclssCode: str = Field(default="01", title="종목대분류코드", description="종목대분류코드")
    """ 종목대분류코드 """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """


class CDPCQ04700OutBlock2(BaseModel):
    """
    CDPCQ04700OutBlock2 - 거래내역 요약 블록

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNm (str): 계좌명
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    AcntNm: str = Field(default="", title="계좌명", description="계좌명")
    """ 계좌명 """


class CDPCQ04700OutBlock3(BaseModel):
    """
    CDPCQ04700OutBlock3 - 거래내역 배열 블록

    Attributes:
        TrdDt (str): 거래일자
        TrdNo (int): 거래번호
        TpCodeNm (str): 구분코드명
        SmryNm (str): 적요명
        TrdQty (int): 거래수량
        TrdAmt (int): 거래금액
        AdjstAmt (int): 정산금액
        CmsnAmt (int): 수수료
        IsuNm (str): 종목명
        IsuNo (str): 종목번호
        EvrTax (int): 제세금
        TrxTime (str): 처리시각
        BnsTpCode (str): 매매구분
        TrdPrc (float): 거래단가
    """
    TrdDt: str = Field(default="", title="거래일자", description="거래일자")
    """ 거래일자 """
    TrdNo: int = Field(default=0, title="거래번호", description="거래번호")
    """ 거래번호 """
    TpCodeNm: str = Field(default="", title="구분코드명", description="구분코드명")
    """ 구분코드명 """
    SmryNm: str = Field(default="", title="적요명", description="적요명")
    """ 적요명 """
    TrdQty: int = Field(default=0, title="거래수량", description="거래수량")
    """ 거래수량 """
    TrdAmt: int = Field(default=0, title="거래금액", description="거래금액")
    """ 거래금액 """
    AdjstAmt: int = Field(default=0, title="정산금액", description="정산금액")
    """ 정산금액 """
    CmsnAmt: int = Field(default=0, title="수수료", description="수수료")
    """ 수수료 """
    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """ 종목명 """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    EvrTax: int = Field(default=0, title="제세금", description="제세금")
    """ 제세금 """
    TrxTime: str = Field(default="", title="처리시각", description="처리시각")
    """ 처리시각 """
    BnsTpCode: str = Field(default="", title="매매구분", description="매매구분")
    """ 매매구분 """
    TrdPrc: float = Field(default=0.0, title="거래단가", description="거래단가")
    """ 거래단가 """


class CDPCQ04700Response(BaseModel):
    """
    CDPCQ04700 API 전체 응답 - 계좌 거래내역

    Attributes:
        header (Optional[CDPCQ04700ResponseHeader])
        block1 (Optional[CDPCQ04700OutBlock1]): 입력 echo-back
        block2 (Optional[CDPCQ04700OutBlock2]): 거래내역 요약
        block3 (List[CDPCQ04700OutBlock3]): 거래내역 배열
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CDPCQ04700ResponseHeader] = None
    block1: Optional[CDPCQ04700OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CDPCQ04700OutBlock2] = Field(
        None,
        title="거래내역 요약",
        description="계좌명 및 레코드 수 요약 정보"
    )
    block3: List[CDPCQ04700OutBlock3] = Field(
        default_factory=list,
        title="거래내역 배열",
        description="일별 거래내역 목록"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str = Field(default="", title="응답코드", description="응답코드")
    rsp_msg: str = Field(default="", title="응답메시지", description="응답메시지")
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
