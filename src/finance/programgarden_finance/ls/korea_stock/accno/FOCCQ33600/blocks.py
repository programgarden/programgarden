from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class FOCCQ33600RequestHeader(BlockRequestHeader):
    """FOCCQ33600 요청용 Header"""
    pass


class FOCCQ33600ResponseHeader(BlockResponseHeader):
    """FOCCQ33600 응답용 Header"""
    pass


class FOCCQ33600InBlock1(BaseModel):
    """
    FOCCQ33600InBlock1 - 주식 계좌 기간별 수익률 상세 입력 블록

    Attributes:
        QrySrtDt (str): 조회시작일 (YYYYMMDD)
        QryEndDt (str): 조회종료일 (YYYYMMDD)
        TermTp (str): 기간구분 (기본 "1": 1:일별 2:주별 3:월별)
    """
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
    TermTp: Literal["1", "2", "3"] = Field(
        default="1",
        title="기간구분",
        description="기간구분 (1:일별 2:주별 3:월별)"
    )
    """ 기간구분 """


class FOCCQ33600Request(BaseModel):
    """
    FOCCQ33600 API 요청 - 주식 계좌 기간별 수익률 상세

    Attributes:
        header (FOCCQ33600RequestHeader)
        body (dict[Literal["FOCCQ33600InBlock1"], FOCCQ33600InBlock1])
    """
    header: FOCCQ33600RequestHeader = FOCCQ33600RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="FOCCQ33600",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["FOCCQ33600InBlock1"], FOCCQ33600InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="FOCCQ33600"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class FOCCQ33600OutBlock1(BaseModel):
    """
    FOCCQ33600OutBlock1 - 입력 echo-back 블록

    Attributes:
        QrySrtDt (str): 조회시작일
        QryEndDt (str): 조회종료일
        TermTp (str): 기간구분
    """
    QrySrtDt: str = Field(default="", title="조회시작일", description="조회시작일 (YYYYMMDD)")
    """ 조회시작일 """
    QryEndDt: str = Field(default="", title="조회종료일", description="조회종료일 (YYYYMMDD)")
    """ 조회종료일 """
    TermTp: str = Field(default="1", title="기간구분", description="기간구분 (1:일별 2:주별 3:월별)")
    """ 기간구분 """


class FOCCQ33600OutBlock2(BaseModel):
    """
    FOCCQ33600OutBlock2 - 수익률 요약 블록

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNm (str): 계좌명
        BnsctrAmt (int): 매매약정금액
        MnyinAmt (int): 입금
        MnyoutAmt (int): 출금
        InvstAvrbalPramt (int): 투자원금평잔
        InvstPlAmt (int): 투자손익
        InvstErnrat (float): 투자수익률
    """
    RecCnt: int = Field(default=0, title="레코드갯수", description="레코드갯수")
    """ 레코드갯수 """
    AcntNm: str = Field(default="", title="계좌명", description="계좌명")
    """ 계좌명 """
    BnsctrAmt: int = Field(default=0, title="매매약정금액", description="매매약정금액")
    """ 매매약정금액 """
    MnyinAmt: int = Field(default=0, title="입금", description="입금")
    """ 입금 """
    MnyoutAmt: int = Field(default=0, title="출금", description="출금")
    """ 출금 """
    InvstAvrbalPramt: int = Field(default=0, title="투자원금평잔", description="투자원금평잔")
    """ 투자원금평잔 """
    InvstPlAmt: int = Field(default=0, title="투자손익", description="투자손익")
    """ 투자손익 """
    InvstErnrat: float = Field(default=0.0, title="투자수익률", description="투자수익률")
    """ 투자수익률 """


class FOCCQ33600OutBlock3(BaseModel):
    """
    FOCCQ33600OutBlock3 - 기간별 수익률 상세 배열 블록

    Attributes:
        BaseDt (str): 기준일
        FdEvalAmt (int): 기초평가
        EotEvalAmt (int): 기말평가
        InvstAvrbalPramt (int): 투자원금평잔
        BnsctrAmt (int): 매매약정
        MnyinSecinAmt (int): 입금고액
        MnyoutSecoutAmt (int): 출금고액
        EvalPnlAmt (int): 평가손익
        TermErnrat (float): 기간수익률
        Idx (float): 지수
    """
    BaseDt: str = Field(default="", title="기준일", description="기준일")
    """ 기준일 """
    FdEvalAmt: int = Field(default=0, title="기초평가", description="기초평가")
    """ 기초평가 """
    EotEvalAmt: int = Field(default=0, title="기말평가", description="기말평가")
    """ 기말평가 """
    InvstAvrbalPramt: int = Field(default=0, title="투자원금평잔", description="투자원금평잔")
    """ 투자원금평잔 """
    BnsctrAmt: int = Field(default=0, title="매매약정", description="매매약정")
    """ 매매약정 """
    MnyinSecinAmt: int = Field(default=0, title="입금고액", description="입금고액")
    """ 입금고액 """
    MnyoutSecoutAmt: int = Field(default=0, title="출금고액", description="출금고액")
    """ 출금고액 """
    EvalPnlAmt: int = Field(default=0, title="평가손익", description="평가손익")
    """ 평가손익 """
    TermErnrat: float = Field(default=0.0, title="기간수익률", description="기간수익률")
    """ 기간수익률 """
    Idx: float = Field(default=0.0, title="지수", description="지수")
    """ 지수 """


class FOCCQ33600Response(BaseModel):
    """
    FOCCQ33600 API 전체 응답 - 주식 계좌 기간별 수익률 상세

    Attributes:
        header (Optional[FOCCQ33600ResponseHeader])
        block1 (Optional[FOCCQ33600OutBlock1]): 입력 echo-back
        block2 (Optional[FOCCQ33600OutBlock2]): 수익률 요약 데이터
        block3 (List[FOCCQ33600OutBlock3]): 기간별 수익률 상세 배열
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[FOCCQ33600ResponseHeader] = None
    block1: Optional[FOCCQ33600OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="입력 파라미터 echo-back 블록"
    )
    block2: Optional[FOCCQ33600OutBlock2] = Field(
        None,
        title="수익률 요약 데이터",
        description="계좌 전체 기간 수익률 요약"
    )
    block3: List[FOCCQ33600OutBlock3] = Field(
        default_factory=list,
        title="기간별 수익률 상세 배열",
        description="일별/주별/월별 수익률 상세 목록"
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
