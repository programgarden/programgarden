from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1403RequestHeader(BlockRequestHeader):
    """t1403 요청용 Header"""
    pass


class T1403ResponseHeader(BlockResponseHeader):
    """t1403 응답용 Header"""
    pass


class T1403InBlock(BaseModel):
    """
    t1403InBlock - 신규상장종목조회 입력 블록

    특정 기간(월 단위)에 신규 상장된 종목을 조회합니다.
    IPO 후 주가 흐름 분석, 신규 상장 모니터링에 활용합니다.

    Attributes:
        gubun (str): 시장구분 (0:전체 1:코스피 2:코스닥)
        styymm (str): 시작상장월 (YYYYMM 형식, 예: "202501")
        enyymm (str): 종료상장월 (YYYYMM 형식, 예: "202512")
        idx (int): 연속조회키 (최초 0, 연속조회 시 이전 OutBlock.idx)
    """
    gubun: str
    """ 시장구분 (0:전체 1:코스피 2:코스닥) """
    styymm: str
    """ 시작상장월 (YYYYMM 형식, 예: "202501") """
    enyymm: str
    """ 종료상장월 (YYYYMM 형식, 예: "202512") """
    idx: int = 0
    """ 연속조회키 (최초 0, 연속조회 시 이전 OutBlock.idx) """


class T1403Request(BaseModel):
    """
    T1403 API 요청 - 신규상장종목조회

    Attributes:
        header (T1403RequestHeader)
        body (Dict[Literal["t1403InBlock"], T1403InBlock])
    """
    header: T1403RequestHeader = T1403RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1403",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1403InBlock"], T1403InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1403"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1403OutBlock(BaseModel):
    """
    t1403OutBlock - 신규상장종목조회 연속조회 블록

    연속조회에 사용되는 idx를 반환합니다.
    다음 페이지 조회 시 이 값을 InBlock.idx에 설정합니다.

    Attributes:
        idx (int): 연속조회키
    """
    idx: int
    """ 연속조회키 (다음 페이지 조회 시 InBlock.idx에 설정) """


class T1403OutBlock1(BaseModel):
    """
    t1403OutBlock1 - 신규상장 종목 정보

    신규 상장된 종목의 현재가, 공모가, 등록일 기준 등락률 등을 제공합니다.
    공모가 대비 현재가 수익률, 상장 직후 성과 분석에 활용합니다.

    Attributes:
        hname (str): 종목명
        price (int): 현재가
        sign (str): 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락)
        change (int): 전일대비 (전일종가 대비 등락 금액)
        diff (float): 등락율(%) (전일종가 대비)
        volume (int): 누적거래량
        kmprice (int): 공모가 (IPO 공모 가격)
        date (str): 등록일 (YYYYMMDD, 상장일)
        recprice (int): 등록일기준가 (상장일 기준가)
        kmdiff (float): 기준가등락율(%) (공모가 대비 현재가 등락률)
        close (int): 등록일종가 (상장 첫날 종가)
        recdiff (float): 등록일등락율(%) (등록일종가 대비 현재가 등락률)
        shcode (str): 종목코드 6자리
    """
    hname: str
    """ 종목명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
    change: int
    """ 전일대비 (전일종가 대비 등락 금액) """
    diff: float
    """ 등락율(%) (전일종가 대비) """
    volume: int
    """ 누적거래량 """
    kmprice: int
    """ 공모가 (IPO 공모 가격) """
    date: str
    """ 등록일 (YYYYMMDD, 상장일) """
    recprice: int
    """ 등록일기준가 (상장일 기준가) """
    kmdiff: float
    """ 기준가등락율(%) (공모가 대비 현재가 등락률) """
    close: int
    """ 등록일종가 (상장 첫날 종가) """
    recdiff: float
    """ 등록일등락율(%) (등록일종가 대비 현재가 등락률) """
    shcode: str
    """ 종목코드 6자리 """


class T1403Response(BaseModel):
    """
    T1403 API 전체 응답 - 신규상장종목조회

    특정 기간 내 신규 상장 종목 리스트를 반환합니다.
    연속조회가 필요하면 cont_block.idx를 다음 요청의 InBlock.idx에 설정합니다.

    Attributes:
        header (Optional[T1403ResponseHeader])
        cont_block (Optional[T1403OutBlock]): 연속조회 블록 (idx 포함)
        block (List[T1403OutBlock1]): 신규상장 종목 리스트
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T1403ResponseHeader]
    cont_block: Optional[T1403OutBlock] = Field(
        None,
        title="연속조회 블록",
        description="연속조회키(idx)를 포함하는 블록"
    )
    block: List[T1403OutBlock1] = Field(
        default_factory=list,
        title="신규상장 종목 리스트",
        description="신규 상장 종목 리스트"
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
