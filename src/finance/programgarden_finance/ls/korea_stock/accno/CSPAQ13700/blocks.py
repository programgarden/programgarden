from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ13700RequestHeader(BlockRequestHeader):
    """CSPAQ13700 요청용 Header"""
    pass


class CSPAQ13700ResponseHeader(BlockResponseHeader):
    """CSPAQ13700 응답용 Header"""
    pass


class CSPAQ13700InBlock1(BaseModel):
    """
    CSPAQ13700InBlock1 - 현물계좌 주문체결내역 조회 입력 블록

    Attributes:
        OrdMktCode (str): 주문시장코드 (기본 "00")
        BnsTpCode (str): 매매구분코드 (기본 "0")
        IsuNo (str): 종목번호 (기본 "")
        ExecYn (str): 체결여부 (기본 "0")
        OrdDt (str): 주문일자 (YYYYMMDD)
        SrtOrdNo2 (int): 시작주문번호2 (기본 999999999)
        BkseqTpCode (str): 역순구분코드 (기본 "0")
        OrdPtnCode (str): 주문패턴코드 (기본 "00")
    """
    OrdMktCode: str = Field(
        default="00",
        title="주문시장코드",
        description="주문시장코드"
    )
    """ 주문시장코드 """
    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드",
        description="매매구분코드"
    )
    """ 매매구분코드 """
    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목번호"
    )
    """ 종목번호 """
    ExecYn: str = Field(
        default="0",
        title="체결여부",
        description="체결여부"
    )
    """ 체결여부 """
    OrdDt: str = Field(
        default="",
        title="주문일자",
        description="주문일자 (YYYYMMDD)"
    )
    """ 주문일자 """
    SrtOrdNo2: int = Field(
        default=999999999,
        title="시작주문번호2",
        description="시작주문번호2"
    )
    """ 시작주문번호2 """
    BkseqTpCode: str = Field(
        default="0",
        title="역순구분코드",
        description="역순구분코드"
    )
    """ 역순구분코드 """
    OrdPtnCode: str = Field(
        default="00",
        title="주문패턴코드",
        description="주문패턴코드"
    )
    """ 주문패턴코드 """


class CSPAQ13700Request(BaseModel):
    """
    CSPAQ13700 API 요청 - 현물계좌 주문체결내역 조회

    Attributes:
        header (CSPAQ13700RequestHeader)
        body (dict[Literal["CSPAQ13700InBlock1"], CSPAQ13700InBlock1])
    """
    header: CSPAQ13700RequestHeader = CSPAQ13700RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ13700",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAQ13700InBlock1"], CSPAQ13700InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ13700"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAQ13700OutBlock1(BaseModel):
    """
    CSPAQ13700OutBlock1 - 입력 echo-back 블록

    Attributes:
        OrdMktCode (str): 주문시장코드
        BnsTpCode (str): 매매구분코드
        IsuNo (str): 종목번호
        ExecYn (str): 체결여부
        OrdDt (str): 주문일자
        SrtOrdNo2 (int): 시작주문번호2
        BkseqTpCode (str): 역순구분코드
        OrdPtnCode (str): 주문패턴코드
    """
    OrdMktCode: str = Field(default="00", title="주문시장코드", description="주문시장코드")
    """ 주문시장코드 """
    BnsTpCode: str = Field(default="0", title="매매구분코드", description="매매구분코드")
    """ 매매구분코드 """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    ExecYn: str = Field(default="0", title="체결여부", description="체결여부")
    """ 체결여부 """
    OrdDt: str = Field(default="", title="주문일자", description="주문일자 (YYYYMMDD)")
    """ 주문일자 """
    SrtOrdNo2: int = Field(default=999999999, title="시작주문번호2", description="시작주문번호2")
    """ 시작주문번호2 """
    BkseqTpCode: str = Field(default="0", title="역순구분코드", description="역순구분코드")
    """ 역순구분코드 """
    OrdPtnCode: str = Field(default="00", title="주문패턴코드", description="주문패턴코드")
    """ 주문패턴코드 """


class CSPAQ13700OutBlock2(BaseModel):
    """
    CSPAQ13700OutBlock2 - 주문체결 요약 블록

    Attributes:
        RecCnt (int): 레코드갯수
        SellExecAmt (int): 매도체결금액
        BuyExecAmt (int): 매수체결금액
        SellExecQty (int): 매도체결수량
        BuyExecQty (int): 매수체결수량
        SellOrdQty (int): 매도주문수량
        BuyOrdQty (int): 매수주문수량
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    SellExecAmt: int = Field(default=0, title="매도체결금액", description="매도체결금액")
    """ 매도체결금액 """
    BuyExecAmt: int = Field(default=0, title="매수체결금액", description="매수체결금액")
    """ 매수체결금액 """
    SellExecQty: int = Field(default=0, title="매도체결수량", description="매도체결수량")
    """ 매도체결수량 """
    BuyExecQty: int = Field(default=0, title="매수체결수량", description="매수체결수량")
    """ 매수체결수량 """
    SellOrdQty: int = Field(default=0, title="매도주문수량", description="매도주문수량")
    """ 매도주문수량 """
    BuyOrdQty: int = Field(default=0, title="매수주문수량", description="매수주문수량")
    """ 매수주문수량 """


class CSPAQ13700OutBlock3(BaseModel):
    """
    CSPAQ13700OutBlock3 - 주문체결내역 배열 블록

    Attributes:
        OrdDt (str): 주문일자
        OrdNo (int): 주문번호
        OrgOrdNo (int): 원주문번호
        IsuNo (str): 종목번호
        IsuNm (str): 종목명
        BnsTpCode (str): 매매구분코드
        BnsTpNm (str): 매매구분명
        OrdQty (int): 주문수량
        OrdPrc (float): 주문단가
        ExecQty (int): 체결수량
        ExecPrc (float): 체결단가
        ExecTrxTime (str): 체결처리시각
        LastExecTime (str): 최종체결시각
        OrdprcPtnCode (str): 주문가유형코드
        OrdprcPtnNm (str): 주문가유형명
        OrdCndiTpCode (str): 주문조건구분코드
        AllExecQty (int): 전체체결수량
        OrdTime (str): 주문시각
        OpDrtnNo (str): 운용지시번호
        RmnOrdQty (int): 잔여주문수량
        OrdGb (str): 주문구분
        Rectgb (str): 접수구분
    """
    OrdDt: str = Field(default="", title="주문일자", description="주문일자")
    """ 주문일자 """
    OrdNo: int = Field(default=0, title="주문번호", description="주문번호")
    """ 주문번호 """
    OrgOrdNo: int = Field(default=0, title="원주문번호", description="원주문번호")
    """ 원주문번호 """
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """ 종목번호 """
    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """ 종목명 """
    BnsTpCode: str = Field(default="", title="매매구분코드", description="매매구분코드")
    """ 매매구분코드 """
    BnsTpNm: str = Field(default="", title="매매구분명", description="매매구분명")
    """ 매매구분명 """
    OrdQty: int = Field(default=0, title="주문수량", description="주문수량")
    """ 주문수량 """
    OrdPrc: float = Field(default=0.0, title="주문단가", description="주문단가")
    """ 주문단가 """
    ExecQty: int = Field(default=0, title="체결수량", description="체결수량")
    """ 체결수량 """
    ExecPrc: float = Field(default=0.0, title="체결단가", description="체결단가")
    """ 체결단가 """
    ExecTrxTime: str = Field(default="", title="체결처리시각", description="체결처리시각")
    """ 체결처리시각 """
    LastExecTime: str = Field(default="", title="최종체결시각", description="최종체결시각")
    """ 최종체결시각 """
    OrdprcPtnCode: str = Field(default="", title="주문가유형코드", description="주문가유형코드")
    """ 주문가유형코드 """
    OrdprcPtnNm: str = Field(default="", title="주문가유형명", description="주문가유형명")
    """ 주문가유형명 """
    OrdCndiTpCode: str = Field(default="", title="주문조건구분코드", description="주문조건구분코드")
    """ 주문조건구분코드 """
    AllExecQty: int = Field(default=0, title="전체체결수량", description="전체체결수량")
    """ 전체체결수량 """
    OrdTime: str = Field(default="", title="주문시각", description="주문시각")
    """ 주문시각 """
    OpDrtnNo: str = Field(default="", title="운용지시번호", description="운용지시번호")
    """ 운용지시번호 """
    RmnOrdQty: int = Field(default=0, title="잔여주문수량", description="잔여주문수량")
    """ 잔여주문수량 """
    OrdGb: str = Field(default="", title="주문구분", description="주문구분")
    """ 주문구분 """
    Rectgb: str = Field(default="", title="접수구분", description="접수구분")
    """ 접수구분 """


class CSPAQ13700Response(BaseModel):
    """
    CSPAQ13700 API 전체 응답 - 현물계좌 주문체결내역 조회

    Attributes:
        header (Optional[CSPAQ13700ResponseHeader])
        block1 (Optional[CSPAQ13700OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAQ13700OutBlock2]): 주문체결 요약 데이터
        block3 (List[CSPAQ13700OutBlock3]): 주문체결내역 배열
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAQ13700ResponseHeader] = None
    block1: Optional[CSPAQ13700OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAQ13700OutBlock2] = Field(
        None,
        title="주문체결 요약 데이터",
        description="주문체결 요약 정보 (체결금액/수량 합계)"
    )
    block3: List[CSPAQ13700OutBlock3] = Field(
        default_factory=list,
        title="주문체결내역 배열",
        description="주문별 체결내역 목록"
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
