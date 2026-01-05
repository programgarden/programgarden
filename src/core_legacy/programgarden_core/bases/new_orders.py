"""Scaffolding for constructing overseas new-order strategy payloads.

EN:
    Define TypedDict responses and abstract strategy mixins that downstream
    packages extend when placing new stock or futures orders.

KO:
    해외 주식/선물 신규 주문 시 하위 패키지가 확장하는 TypedDict 응답과 추상
    전략 베이스 클래스를 정의합니다.
"""

from typing import Literal, TypedDict

from programgarden_core.bases.base import BaseOrderOverseasStock, BaseOrderOverseasFutures


class BaseNewOrderOverseasStockResponseType(TypedDict):
    """Response schema for overseas stock order strategies.

    EN:
        Contains the minimum data that :class:`BaseNewOrderOverseasStock`
        strategies must produce to execute an order.

    KO:
        주문을 넣기 위한 반환값 데이터로써, :class:`BaseNewOrderOverseasStock` 전략이 주문 실행을 위해 제공해야 하는
        필수 데이터를 정의합니다.
    """

    success: bool
    """EN: Flag indicating the strategy passed validation.
    KO: 성공여부(전략 검증이 통과했는지 나타내는 플래그입니다.)"""

    ord_ptn_code: Literal["01", "02"]
    """EN: Order direction (``01`` sell, ``02`` buy).
    KO: 주문유형코드(``01`` 은 매도, ``02`` 는 매수입니다.)"""

    ord_mkt_code: Literal["81", "82"]
    """EN: Market code (81: NYSE/AMEX, 82: NASDAQ).
    KO: 주문시장코드(81: 뉴욕/아멕스, 82: 나스닥입니다.)"""

    shtn_isu_no: str
    """EN: Short symbol identifier (e.g., ``TSLA``).
    KO: 단축종목번호(예: ``TSLA`` 입니다.)"""

    ord_qty: int
    """EN: Quantity to submit with the order.
    KO: 주문수량(주문에 제출할 수량입니다.)"""

    ovrs_ord_prc: float
    """EN: Overseas order price.
    KO: 해외주문가(해외 시장에서 사용할 주문 가격입니다.)"""

    ordprc_ptn_code: Literal["00", "M1", "M2", "03", "M3", "M4"]
    """EN: Price type code (00: limit, 03: market, etc.).
    KO: 호가유형코드(00: 지정가, M1: LOO, M2: LOC, 03: 시장가, M3: MOO, M4: MOC 입니다.)"""

    brk_tp_code: str = ""
    """EN: Optional broker code.
    KO: 중개인구분코드(선택 입력 항목입니다.)"""

    crcy_code: str = "USD"
    """EN: Currency code, defaults to ``USD``.
    KO: 통화코드(기본값은 ``USD`` 입니다.)"""

    pnl_rat: float = 0.0
    """EN: Profit/loss ratio supported for analytics.
    KO: 손익율(분석용 손익률입니다.)"""

    pchs_amt: float = 0.0
    """EN: Purchase amount for reference.
    KO: 매입금액(참고용 금액입니다.)"""

    bns_tp_code: Literal["1", "2"]
    """EN: Buy/sell code (1: sell, 2: buy).
    KO: 매매구분코드(1은 매도, 2는 매수입니다.)"""


class BaseNewOrderOverseasStock(BaseOrderOverseasStock[BaseNewOrderOverseasStockResponseType]):
    """Abstract base for overseas stock new-order strategies.

    EN:
        Extend this class and implement :meth:`execute` to generate
        :class:`BaseNewOrderOverseasStockResponseType` payloads.

    KO:
        매수 또는 매도를 하기 위한 전략을 계산하고 주문에 필요한 값을 반환합니다. 이 클래스를 확장하고 :meth:`execute` 를 구현하여
        :class:`BaseNewOrderOverseasStockResponseType` 페이로드를 생성하세요.
    """


class BaseNewOrderOverseasFuturesResponseType(TypedDict):
    """Response schema for overseas futures order strategies.

    EN:
        Defines the minimum payload needed to submit new futures orders.

    KO:
        해외 선물 신규 주문에 필요한 최소 페이로드를 정의합니다.
    """

    success: bool
    """EN: Indicator that strategy checks succeeded.
    KO: 성공여부(전략 검증이 성공했음을 나타냅니다.)"""

    ord_dt: str
    """EN: Order date (``YYYYMMDD`` format).
    KO: 주문일자(``YYYYMMDD`` 형식입니다.)"""

    isu_code_val: str
    """EN: Instrument code (e.g., ``ADM23``).
    KO: 종목코드값(예: ``ADM23`` 입니다.)"""

    futs_ord_tp_code: Literal["1"] = "1"
    """EN: Futures order type code (``1`` represents new order).
    KO: 선물주문구분코드(``1`` 은 신규 주문입니다.)"""

    bns_tp_code: Literal["1", "2"]
    """EN: Buy/sell code (1: sell, 2: buy).
    KO: 매매구분코드(1은 매도, 2는 매수입니다.)"""

    abrd_futs_ord_ptn_code: Literal["1", "2"]
    """EN: Order pattern code (1: market, 2: limit).
    KO: 해외선물주문유형코드(1은 시장가, 2는 지정가입니다.)"""

    ovrs_drvt_ord_prc: float
    """EN: Order price for the derivative contract.
    KO: 해외파생주문가격(파생상품 주문 가격입니다.)"""

    cndi_ord_prc: float
    """EN: Conditional order price, if applicable.
    KO: 조건주문가격(필요 시 사용하는 값이고 평소에는 0.0 또는 None으로 두면 됩니다.)"""

    ord_qty: int
    """EN: Quantity to submit with the order.
    KO: 주문수량(제출할 수량입니다.)"""

    exch_code: str
    """EN: Exchange code (mock trading may require ``HKEX``).
    KO: 거래소코드(빈값으로 두어도 됩니다. 모의투자의 경우 ``HKEX`` 로 고정될 수 있고 빈값으로 해도 됩니다.)"""

    prdt_code: str = ""
    """EN: Optional product code.
    KO: 상품코드(빈값으로 둬도 됩니다.)"""

    due_yymm: str = ""
    """EN: Optional expiration year/month.
    KO: 만기연월(빈값으로 둬도 됩니다.)"""

    crcy_code: str = ""
    """EN: Optional currency code.
    KO: 통화코드(빈값으로 둬도 됩니다.)"""


class BaseNewOrderOverseasFutures(BaseOrderOverseasFutures[BaseNewOrderOverseasFuturesResponseType]):
    """Abstract base for overseas futures new-order strategies.

    EN:
        Extend this class and implement :meth:`execute` to produce
        :class:`BaseNewOrderOverseasFuturesResponseType` payloads.

    KO:
        해외선물 신규 주문 전략 기본 클래스이며, 이 클래스를 확장하고 :meth:`execute` 를 구현하여
        :class:`BaseNewOrderOverseasFuturesResponseType` 페이로드를 생성하세요.
    """
