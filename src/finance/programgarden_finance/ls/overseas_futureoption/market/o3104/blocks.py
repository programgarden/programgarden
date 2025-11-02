from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3104RequestHeader(BlockRequestHeader):
    pass


class O3104ResponseHeader(BlockResponseHeader):
    pass


class O3104InBlock(BaseModel):
    """
    o3104InBlock 데이터 블록

    Attributes:
        gubun (Literal["0", "1", "2"]): 조회구분 (0:일별 1:주별 2:월별)
        shcode (str): 단축코드
        date (str): 조회일자 (YYYYMMDD)
    """
    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="조회구분",
        description="조회구분 (0:일별 1:주별 2:월별)"
    )

    shcode: str = Field(
        ...,
        title="단축코드",
        description="단축코드 (8자리)"
    )

    date: str = Field(
        ...,
        title="조회일자",
        description="조회일자 (YYYYMMDD)"
    )


class O3104Request(BaseModel):
    """
    o3104 API 요청 전체 구조
    """
    header: O3104RequestHeader = O3104RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3104",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더"""
    body: dict[Literal["o3104InBlock"], O3104InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3104InBlock')"
    )
    """입력 데이터 블록"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3104"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3104OutBlock1(BaseModel):
    """
    o3104OutBlock1 데이터 블록 리스트 항목

    Attributes:
        chedate (str): 일자 (YYYYMMDD)
        price (float): 현재가
        sign (str): 대비구분
        change (float): 대비
        diff (float): 등락율
        open (float): 시가
        high (float): 고가
        low (float): 저가
        cgubun (str): 체결구분
        volume (int): 누적거래량
    """
    chedate: str = Field(
        ...,
        title="일자",
        description="일자 (YYYYMMDD)"
    )

    price: float = Field(
        ...,
        title="현재가",
        description="현재가"
    )

    sign: str = Field(
        ...,
        title="대비구분",
        description="대비구분"
    )

    change: float = Field(
        ...,
        title="대비",
        description="대비"
    )

    diff: float = Field(
        ...,
        title="등락율",
        description="등락율"
    )

    open: float = Field(
        ...,
        title="시가",
        description="시가"
    )

    high: float = Field(
        ...,
        title="고가",
        description="고가"
    )

    low: float = Field(
        ...,
        title="저가",
        description="저가"
    )

    cgubun: str = Field(
        ...,
        title="체결구분",
        description="체결구분"
    )

    volume: int = Field(
        ...,
        title="누적거래량",
        description="누적거래량"
    )


class O3104Response(BaseModel):
    """
    o3104 API 응답 전체 구조
    """
    header: Optional[O3104ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block1: List[O3104OutBlock1] = Field(
        ...,
        title="출력 블록 리스트",
        description="o3104 응답의 출력 블록 리스트"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답 코드", description="응답 코드")
    rsp_msg: str = Field(..., title="응답 메시지", description="응답 메시지")
    error_msg: Optional[str] = Field(None, title="오류 메시지", description="오류 메시지 (있으면)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
