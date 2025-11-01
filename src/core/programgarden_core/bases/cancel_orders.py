"""Scaffolding for overseas order cancellation strategy payloads.

EN:
    Provide response schemas and abstract classes used to cancel overseas stock
    or futures orders.

KO:
    해외 주식/선물 주문을 취소할 때 사용하는 응답 스키마와 추상 클래스를
    제공합니다.
"""

from typing import Literal, TypedDict

from programgarden_core.bases.base import BaseOrderOverseasStock, BaseOrderOverseasFutures


class BaseCancelOrderOverseasStockResponseType(TypedDict):
    """Response schema for overseas stock cancellation strategies.

    EN:
        Captures the fields needed to cancel an outstanding stock order.

    KO:
        미체결 주식 주문을 취소하는 데 필요한 필드를 담습니다.
    """

    success: bool
    """EN: Indicates whether the strategy approved the cancellation.
    KO: 성공여부(전략이 취소 요청을 위해 계산을 통과했는지 여부입니다.)"""

    ord_ptn_code: Literal["08"]
    """EN: Order type code (``08`` means cancellation request).
    KO: 주문유형코드(``08`` 은 취소 요청을 의미합니다.)"""

    org_ord_no: str
    """EN: Original order number targeted for cancellation.
    KO: 원주문번호(취소 대상 번호입니다.)"""

    ord_mkt_code: Literal["81", "82"]
    """EN: Market code (81: NYSE/AMEX, 82: NASDAQ).
    KO: 주문시장코드(81: 뉴욕/아멕스, 82: 나스닥입니다.)"""

    shtn_isu_no: str
    """EN: Short symbol identifier (e.g., ``TSLA``).
    KO: 단축종목번호(예: ``TSLA`` 입니다.)"""

    ord_qty: int
    """EN: Quantity to cancel.
    KO: 주문수량(취소하려는 수량입니다.)"""

    ovrs_ord_prc: float = 0.0
    """EN: Stored order price for reference (defaults to ``0`` when unused).
    KO: 해외주문가(참조용 값이며 사용하지 않으면 ``0`` 입니다.)"""

    ordprc_ptn_code: Literal["00", "M1", "M2", "03", "M3", "M4"]
    """EN: Price type code mirroring original order settings.
    KO: 호가유형코드(원주문 설정을 반영합니다. 00: 지정가, M1: LOO, M2: LOC, 03: 시장가, M3: MOO, M4: MOC입니다.)"""

    bns_tp_code: Literal["1", "2"]
    """EN: Buy/sell code (1: sell, 2: buy).
    KO: 매매구분코드(1은 매도, 2는 매수입니다.)"""

    brk_tp_code: str = ""
    """EN: Optional broker code.
    KO: 중개인구분코드(선택 입력 항목입니다.)"""


class BaseCancelOrderOverseasStock(BaseOrderOverseasStock[BaseCancelOrderOverseasStockResponseType]):
    """Abstract base for overseas stock cancellation strategies.

    EN:
        Extend and implement :meth:`execute` to emit
        :class:`BaseCancelOrderOverseasStockResponseType` payloads.

    KO:
        취소 주문을 하기 위한 전략을 계산하고 주문에 필요한 데이터를 반환합니다.
        그래서 이 클래스를 확장하고 :meth:`execute` 를 구현하여
        :class:`BaseCancelOrderOverseasStockResponseType` 페이로드를 생성하세요.
    """

    product = "overseas_stock"
    """EN: Literal indicating stock cancellation workflow.
    KO: 주식 취소 워크플로의 상품군을 나타내는 literal 값입니다."""


class BaseCancelOrderOverseasFuturesResponseType(TypedDict, total=False):
    """Response schema for overseas futures cancellation strategies.

    EN:
        Describes the fields needed to request cancellation of futures orders.

    KO:
        해외선물 주문 취소를 요청할 때 필요한 필드를 설명합니다.
    """

    success: bool
    """EN: Flag indicating the strategy authorizes cancellation.
    KO: 성공여부(전략이 취소를 허용하는지 여부입니다.)"""

    ord_dt: str
    """EN: Order date (``YYYYMMDD`` format).
    KO: 주문일자(``YYYYMMDD`` 형식입니다.)"""

    isu_code_val: str
    """EN: Instrument code value.
    KO: 종목코드값(응답 필드 값입니다.)"""

    ovrs_futs_org_ord_no: str
    """EN: Original futures order number targeted for cancellation.
    KO: 해외선물원주문번호(취소 대상 번호입니다.)"""

    futs_ord_tp_code: Literal["3"]
    """EN: Futures order type code (``3`` indicates cancellation).
    KO: 선물주문구분코드(``3`` 은 취소를 의미합니다.)"""

    prdt_tp_code: str = ""
    """EN: Optional product type code.
    KO: 상품구분코드(빈값으로 해도됩니다.)"""

    exch_code: str = ""
    """EN: Optional exchange code (mock trading may use ``HKEX``).
    KO: 거래소코드(빈값으로 해도 되며, 모의투자 시 ``HKEX`` 를 사용해도 되고 빈값으로 둬도 됩니다)"""


class BaseCancelOrderOverseasFutures(BaseOrderOverseasFutures[BaseCancelOrderOverseasFuturesResponseType]):
    """Abstract base for overseas futures cancellation strategies.

    EN:
        Extend and implement :meth:`execute` to emit
        :class:`BaseCancelOrderOverseasFuturesResponseType` payloads.

    KO:
        해외선물 취소 주문 전략 기본 클래스이고 이 클래스를 확장하고 :meth:`execute` 를 구현하여
        :class:`BaseCancelOrderOverseasFuturesResponseType` 페이로드를 생성하세요.
    """

    product = "overseas_futures"
    """EN: Literal indicating futures cancellation workflow.
    KO: 선물 취소 워크플로의 상품 유형을 나타내는 literal 값입니다."""
