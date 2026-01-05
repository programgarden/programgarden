"""Scaffolding for overseas order modification strategy payloads.

EN:
    Provide response schemas and abstract strategy bases for amending existing
    overseas stock or futures orders.

KO:
    해외 주식/선물 정정 주문을 위해 필요한 응답 스키마와 추상 전략 베이스를
    제공합니다.
"""

from typing import Literal, TypedDict

from programgarden_core.bases.base import BaseOrderOverseasStock, BaseOrderOverseasFutures


class BaseModifyOrderOverseasStockResponseType(TypedDict):
    """Response schema for overseas stock order modifications.

    EN:
        Defines payloads used to modify existing stock orders, including
        references to original order numbers.

    KO:
        원주문 번호를 포함해 해외 주식 주문 정정 시 사용되는 페이로드 구조를
        정의합니다.
    """

    success: bool
    """EN: Flag indicating whether the strategy approves the modification.
    KO: 성공여부(전략 검증이 정정을 허용하는지 나타내는 플래그입니다.)"""

    ord_ptn_code: Literal["07"] = "07"
    """EN: Order type code (``07`` represents modify request).
    KO: 주문유형코드(``07`` 은 정정 요청을 의미합니다.)"""

    org_ord_no: int
    """EN: Original order number being amended.
    KO: 원주문번호(정정 대상 번호입니다.)"""

    ord_mkt_code: Literal["81", "82"]
    """EN: Market code (81: NYSE/AMEX, 82: NASDAQ).
    KO: 주문시장코드(81: 뉴욕/아멕스, 82: 나스닥입니다.)"""

    shtn_isu_no: str
    """EN: Short symbol identifier (e.g., ``TSLA``).
    KO: 단축종목번호(예: ``TSLA`` 입니다.)"""

    ord_qty: int
    """EN: Updated quantity to submit.
    KO: 주문수량(새로 제출할 수량입니다.)"""

    ovrs_ord_prc: float
    """EN: Revised order price.
    KO: 해외주문가(정정 후 주문 가격입니다.)"""

    ordprc_ptn_code: Literal["00", "M1", "M2", "03", "M3", "M4"]
    """EN: Price type code (00: limit, 03: market, etc.).
    KO: 호가유형코드(00: 지정가, M1: LOO, M2: LOC, 03: 시장가, M3: MOO, M4: MOC 등입니다.)"""

    bns_tp_code: Literal["1", "2"]
    """EN: Buy/sell code (1: sell, 2: buy).
    KO: 매매구분코드(1은 매도, 2는 매수입니다.)"""

    brk_tp_code: str = ""
    """EN: Optional broker code.
    KO: 중개인구분코드(선택 입력 항목입니다.)"""


class BaseModifyOrderOverseasStock(BaseOrderOverseasStock[BaseModifyOrderOverseasStockResponseType]):
    """Abstract base for overseas stock modify-order strategies.

    EN:
        Extend and implement :meth:`execute` to emit
        :class:`BaseModifyOrderOverseasStockResponseType` payloads.

    KO:
        정정매수를 하기 위한 전략을 계산하고 정정매수를 위한 값을 던져줍니다. 그리고 이 클래스를 확장하고 :meth:`execute` 를 구현하여
        :class:`BaseModifyOrderOverseasStockResponseType` 페이로드를 생성하세요.
    """


class BaseModifyOrderOverseasFuturesResponseType(TypedDict, total=False):
    """Response schema for overseas futures order modifications.

    EN:
        Encapsulates the fields required when adjusting derivative orders.

    KO:
        해외선물 주문을 정정할 때 필요한 필드를 캡슐화합니다.
    """

    success: bool
    """EN: Flag indicating the modification is allowed.
    KO: 성공여부(전략 통과로 정정이 허용되는지 여부입니다.)"""

    ord_dt: str
    """EN: Order date (``YYYYMMDD`` format).
    KO: 주문일자(``YYYYMMDD`` 형식입니다.)"""

    ovrs_futs_org_ord_no: str
    """EN: Original futures order number.
    KO: 해외선물원주문번호(정정 대상 번호입니다.)"""

    isu_code_val: str
    """EN: Instrument code value.
    KO: 종목코드값(응답 필드 값입니다.)"""

    futs_ord_tp_code: Literal["2"]
    """EN: Futures order type code (``2`` represents modification).
    KO: 선물주문구분코드(``2`` 는 정정을 의미합니다.)"""

    bns_tp_code: Literal["1", "2"]
    """EN: Buy/sell code (1: sell, 2: buy).
    KO: 매매구분코드(1은 매도, 2는 매수입니다.)"""

    futs_ord_ptn_code: Literal["2"]
    """EN: Order pattern code (``2`` indicates limit order).
    KO: 선물주문유형코드(``2`` 는 지정가 주문을 의미합니다.)"""

    crcy_code_val: str = ""
    """EN: Optional currency code value.
    KO: 통화코드값(선택 입력 항목입니다.)"""

    ovrs_drvt_ord_prc: float
    """EN: Revised derivative order price.
    KO: 해외파생주문가격(정정 후 주문 가격입니다.)"""

    cndi_ord_prc: float
    """EN: Conditional order price, if applicable.
    KO: 조건주문가격(필요 시 사용하는 값입니다.)"""

    ord_qty: int
    """EN: Updated quantity.
    KO: 주문수량(정정 후 제출할 수량입니다.)"""

    exch_code: str
    """EN: Exchange code (mock trading may require ``HKEX``).
    KO: 거래소코드(모의투자의 경우 ``HKEX`` 로 고정될 수 있습니다.)"""

    ovrs_drvt_prdt_code: str = ""
    """EN: Optional derivative product code.
    KO: 해외파생상품코드(선택 입력 항목입니다.)"""

    due_yymm: str = ""
    """EN: Optional expiration year/month.
    KO: 만기연월(선택 입력 항목입니다.)"""


class BaseModifyOrderOverseasFutures(BaseOrderOverseasFutures[BaseModifyOrderOverseasFuturesResponseType]):
    """Abstract base for overseas futures modify-order strategies.

    EN:
        Extend and implement :meth:`execute` to emit
        :class:`BaseModifyOrderOverseasFuturesResponseType` payloads.

    KO:
        해외선물 정정 주문 전략 기본 클래스이며, 이 클래스를 확장하고 :meth:`execute` 를 구현하여
        :class:`BaseModifyOrderOverseasFuturesResponseType` 페이로드를 생성하세요.
    """
