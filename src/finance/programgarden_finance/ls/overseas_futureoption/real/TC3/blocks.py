"""Pydantic models for LS Securities OpenAPI TC3 (Overseas Futures Order Execution / Fill).

TC3 is a Real-time WebSocket TR that pushes per-fill events for
overseas-futures orders (the exchange-side execution that follows TC2's
order-response confirmation). The ``TC3RealRequestBody`` carries the
WebSocket subscription envelope; the ``TC3RealResponseBody`` carries the
per-fill push payload (fill metadata, prices, quantities, post-fill
average / position fields, fees, currency, expiry / spread / LME
attributes).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Code classifiers documented in the in-source Korean comments
      (``s_b_ccd``, ``ordr_ccd``, ``svc_id``) are listed verbatim.
    - All numeric fields (price, quantity, P&L, fees) are typed ``str`` in
      source — preserved verbatim. Stringified-numeric scale not declared.
    - The ``clr_pl_amt`` (청산손익) field's sign convention, currency,
      and computation formula are NOT declared in the available source —
      consume as returned by LS. No PnL formula inferred per
      ``feedback_no_inferred_formulas``.
    - The ``fcm_fee`` field carries an ambiguous in-source label
      (``title="매입잔고수량"`` while the docstring notes "또는 FCM 수수료
      필드") — preserved verbatim with the ambiguity surfaced in description.
    - The ``exec_prdt_tp_code`` field's source ``title`` matches
      ``ord_prdt_tp_code``'s title (``"주문상품구분코드"``) but its
      docstring describes "실행 상품 구분 코드" — preserved with the
      English clarifier in title.
    - Account number placeholders use ``"12345678901"`` per safety policy.
    - Spread / LME / 만기 fields are populated only for relevant contracts;
      blank otherwise.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class TC3RealRequestHeader(BlockRealRequestHeader):
    """TC3 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class TC3RealResponseHeader(BlockRealResponseHeader):
    """TC3 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class TC3RealRequestBody(BaseModel):
    """TC3RealRequestBody — WebSocket subscription envelope for order-execution push.

    TC3 is typically subscribed account-wide; ``tr_key`` is optional.
    """

    tr_cd: str = Field(
        default="TC3",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'TC3'.",
        examples=["TC3"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short futures symbol, optional)",
        description=(
            "Optional short overseas-futures contract symbol. May be left "
            "empty for account-wide subscription. Max 8 characters."
        ),
        examples=["", "ESZ25   "],
    )


class TC3RealRequest(BaseModel):
    header: TC3RealRequestHeader = Field(
        TC3RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="TC3 WebSocket subscription header block (token + tr_type)."
    )
    body: TC3RealRequestBody = Field(
        ...,
        title="입력 데이터 블록 (Input body block)",
        description=(
            "해외선물 주문체결 input body — TR code and optional symbol key "
            "(account-wide subscription if omitted)."
        ),
    )


class TC3RealResponseBody(BaseModel):
    """TC3RealResponseBody — order-execution / fill push payload.

    Carries WS line metadata, service-ID classifier (CH01 = fill), order
    identifiers, account / symbol, side / new-modify-cancel classifier,
    fill quantity / price / time, post-fill position metrics (average
    purchase price, purchase amount, clearing P&L), fees, current price,
    currency, expiry, product-type classifiers, spread (sprd) attributes,
    and LME-specific fields populated only for relevant contracts.
    """

    lineseq: str = Field(
        ...,
        title="라인일련번호 (Line sequence number)",
        description="Line-level sequence number assigned by LS for the push frame.",
        examples=["1", "0001"],
    )
    key: str = Field(
        ...,
        title="KEY (LS-side push key)",
        description="LS-side push key associated with this event; consume as returned by LS.",
        examples=["12345678901"],
    )
    user: str = Field(
        ...,
        title="조작자ID (Operator ID)",
        description="Operator (user) ID that originated the order action.",
        examples=["USER01"],
    )
    svc_id: str = Field(
        ...,
        title="서비스ID (Service ID)",
        description="Service-ID classifier. 'CH01' = fill / execution event.",
        examples=["CH01"],
    )
    ordr_dt: str = Field(
        ...,
        title="주문일자 (Order date)",
        description="Order date in YYYYMMDD format.",
        examples=["20260506"],
    )
    brn_cd: str = Field(
        ...,
        title="지점번호 (Branch number)",
        description="LS branch number; consume as returned by LS.",
        examples=["001"],
    )
    ordr_no: str = Field(
        ...,
        title="주문번호 (Order number)",
        description="Order number for the event, as a string.",
        examples=["100001"],
    )
    orgn_ordr_no: str = Field(
        ...,
        title="원주문번호 (Original order number)",
        description="Original order number this event references (0 / blank when not applicable).",
        examples=["0", "100001"],
    )
    mthr_ordr_no: str = Field(
        ...,
        title="모주문번호 (Parent order number)",
        description="Parent order number for grouped orders; consume as returned by LS.",
        examples=["0"],
    )
    ac_no: str = Field(
        ...,
        title="계좌번호 (Account number)",
        description="Account number the event belongs to. Placeholder used in examples — never real.",
        examples=["12345678901"],
    )
    is_cd: str = Field(
        ...,
        title="종목코드 (Symbol / contract code)",
        description="Overseas-futures contract code for the order (root + expiry).",
        examples=["ESZ25", "NQU26"],
    )
    s_b_ccd: str = Field(
        ...,
        title="매도매수유형 (Sell/buy classifier)",
        description="Sell/buy classifier. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )
    ordr_ccd: str = Field(
        ...,
        title="정정취소유형 (New/modify/cancel classifier)",
        description="Order-action classifier. '1' = new (신규), '2' = modify (정정), '3' = cancel (취소).",
        examples=["1", "2", "3"],
    )
    ccls_q: str = Field(
        ...,
        title="체결수량 (Fill quantity)",
        description="Fill quantity for this execution event (contracts), as a string.",
        examples=["1", "5"],
    )
    ccls_prc: str = Field(
        ...,
        title="체결가격 (Fill price)",
        description=(
            "Fill price for this execution event in the contract's quote "
            "currency, as a string. Decimal scale not declared in available "
            "source."
        ),
        examples=["5025.25"],
    )
    ccls_no: str = Field(
        ...,
        title="체결번호 (Fill number)",
        description="Exchange-assigned fill identifier, as a string.",
        examples=["1"],
    )
    ccls_tm: str = Field(
        ...,
        title="체결시간 (Fill time)",
        description="Fill time stamp in HHMMSS format. Time zone not declared in available source.",
        examples=["093015"],
    )
    avg_byng_uprc: str = Field(
        ...,
        title="매입평균단가 (Average purchase unit price)",
        description=(
            "Average purchase unit price for the holding after the fill, "
            "as a string. Currency / scale not declared in available source."
        ),
        examples=["5020.50"],
    )
    byug_amt: str = Field(
        ...,
        title="매입금액 (Purchase amount)",
        description=(
            "Total purchase amount for the holding, as a string. Currency / "
            "scale not declared. (Source uses the spelling 'byug_amt' — "
            "preserved verbatim.)"
        ),
        examples=["50205.00"],
    )
    clr_pl_amt: str = Field(
        ...,
        title="청산손익 (Clearing / close P&L)",
        description=(
            "Clearing / close P&L attributable to this fill, as a string. "
            "Sign convention, currency, and computation formula not declared "
            "in available source — consume as returned by LS."
        ),
        examples=["0", "125.00", "-75.50"],
    )
    ent_fee: str = Field(
        ...,
        title="위탁수수료 (Brokerage / consigned fee)",
        description=(
            "Brokerage / consigned fee for the fill, as a string. Currency "
            "not declared in available source."
        ),
        examples=["0.50"],
    )
    fcm_fee: str = Field(
        ...,
        title="매입잔고수량 (Source label ambiguous — may also denote FCM fee)",
        description=(
            "Source declares ``title='매입잔고수량'`` (purchase holding "
            "quantity) but the in-source docstring notes the field may "
            "alternatively represent an FCM fee. Both interpretations are "
            "preserved verbatim from source — consume as returned by LS "
            "and do not infer one over the other."
        ),
        examples=["0", "0.25"],
    )
    userid: str = Field(
        ...,
        title="사용자ID (User ID)",
        description="LS user ID associated with the order.",
        examples=["USER01"],
    )
    now_prc: str = Field(
        ...,
        title="현재가격 (Current price)",
        description=(
            "Current market price for the contract at the time of the push, "
            "as a string. Scale not declared in available source."
        ),
        examples=["5025.25"],
    )
    crncy_cd: str = Field(
        ...,
        title="통화코드 (Currency code)",
        description=(
            "Currency code for prices on this event (e.g., 'USD', 'KRW'). "
            "Complete set of supported currencies not declared in available "
            "source."
        ),
        examples=["USD", "KRW"],
    )
    mtrt_dt: str = Field(
        ...,
        title="만기일자 (Maturity / expiry date)",
        description="Contract maturity / expiry date in YYYYMMDD format.",
        examples=["20251219"],
    )
    ord_prdt_tp_code: str = Field(
        ...,
        title="주문상품구분코드 (Order product type code)",
        description=(
            "Order product type classifier. Complete enum mapping not "
            "declared in available source; consume as returned by LS."
        ),
        examples=["1"],
    )
    exec_prdt_tp_code: str = Field(
        ...,
        title="주문상품구분코드 (Execution product type code)",
        description=(
            "Execution product type classifier (per source docstring '실행 "
            "상품 구분 코드' — distinct from ``ord_prdt_tp_code`` despite "
            "sharing the same source ``title`` label). Complete enum "
            "mapping not declared; consume as returned by LS."
        ),
        examples=["1"],
    )
    sprd_base_isu_yn: str = Field(
        ...,
        title="스프레드종목여부 (Spread-instrument flag)",
        description="Spread-instrument flag. 'Y' = spread instrument, 'N' = outright.",
        examples=["Y", "N"],
    )
    ccls_dt: str = Field(
        ...,
        title="체결일자 (Fill date)",
        description="Fill date in YYYYMMDD format.",
        examples=["20260506"],
    )
    filler2: str = Field(
        ...,
        title="FILLER2 (Reserved area 2)",
        description="Reserved area; consume as returned by LS.",
        examples=[""],
    )
    sprd_is_cd: str = Field(
        ...,
        title="스프레드종목코드 (Spread instrument code)",
        description=(
            "Spread instrument code for spread fills; blank otherwise. "
            "LS-internal spread-symbol encoding is not declared in "
            "available source — consume as returned by LS, do not assume "
            "a particular leg-pair format."
        ),
        examples=[""],
    )
    lme_prdt_ccd: str = Field(
        ...,
        title="LME상품유형 (LME product-type code)",
        description=(
            "LME product-type classifier (populated for LME contracts; "
            "blank otherwise). Code mapping not declared in available source."
        ),
        examples=[""],
    )
    lme_sprd_prc: str = Field(
        ...,
        title="LME스프레드가격 (LME spread price)",
        description=(
            "LME spread price as a string (populated for LME contracts; "
            "blank otherwise). Scale not declared."
        ),
        examples=[""],
    )
    last_now_prc: str = Field(
        ...,
        title="최종현재가격 (Last current price)",
        description=(
            "Most recent current price snapshot for the contract, as a "
            "string. Distinguishing semantics vs. ``now_prc`` not declared "
            "in available source; consume as returned by LS."
        ),
        examples=["5025.25"],
    )
    bf_mtrt_dt: str = Field(
        ...,
        title="이전만기일자 (Previous maturity date)",
        description=(
            "Previous maturity date in YYYYMMDD format (blank when not "
            "applicable, e.g. for non-rolled positions)."
        ),
        examples=["", "20250920"],
    )
    clr_q: str = Field(
        ...,
        title="청산수량 (Clearing / close quantity)",
        description=(
            "Clearing / close quantity (contracts) attributable to the "
            "fill, as a string. Sign convention not declared in available "
            "source."
        ),
        examples=["0", "1"],
    )


class TC3RealResponse(BaseModel):
    header: Optional[TC3RealResponseHeader]
    body: Optional[TC3RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
