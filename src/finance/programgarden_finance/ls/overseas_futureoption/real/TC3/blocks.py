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
      필드") — the upstream ambiguity is still preserved verbatim, but a
      2026-09-12 owner observation (~90% confidence) says the value actually
      carried is the FCM (해외 브로커) fee, not a holding quantity: do not
      parse it as a quantity. 미관측 — 라이브 TC3 프레임으로 대조하지 않았다
      (출처: 오너 진술 2026-09-12).
    - The ``exec_prdt_tp_code`` field's source ``title`` matches
      ``ord_prdt_tp_code``'s title (``"주문상품구분코드"``) but its
      docstring describes "실행 상품 구분 코드" — preserved with the
      English clarifier in title.
    - Account number placeholders use ``"12345678901"`` per safety policy.
    - Spread / LME / 만기 fields are populated only for relevant contracts;
      empty otherwise. 여기서 "비어 있다" 는 키가 없다는 뜻이 아니다 — 이
      응답 모델의 필드는 전부 ``Field(...)`` required 이므로 스키마상 항상
      존재하고 값만 빈 문자열('')이다. 소비 측 판별은 hasattr / ``is None``
      이 아니라 ``== ''`` 로 해야 한다 — body 가 성공적으로 검증된 뒤라면
      hasattr/None 분기는 발화하지 않는다. 다만 ``TC3RealResponse.body``
      자체는 ``Optional[TC3RealResponseBody]`` 라서, 프레임에 body 가 없거나
      required 키가 빠져 검증이 실패하면 ``real_base`` 가 ``body=None`` 을
      콜백에 넘긴다 (``ls/real_base.py`` 의 ``body=... if resp_body else
      None`` 분기와 검증 예외 분기 — 2026-09-12 기준 각각 342행 / 350행).
      즉 None 검사는 ``response.body`` 객체 자체에 대해서는 필요하고,
      검증을 통과한 body **안의 개별 필드**에 대해서만 불필요하다.
    - 단, ``lme_prdt_ccd`` 의 "blank otherwise" 는 오너 진술("일반
      해외선물이면 '0'", 2026-09-12, ~90% 확신)과 충돌한다 — 양쪽을 그 필드
      description 에 병기했고 라이브 프레임으로만 결론낼 수 있다(미해결).
    - ``sprd_base_isu_yn`` 은 스프레드 여부를 가리는 판별 플래그다. 오너의
      "sprd_* 는 스프레드 상품에만" 포괄 진술이 이 판별 플래그에까지
      적용되는지는 오너가 말한 바 없어 미확인이며, 상류는 아웃라이트에도
      'N' 이 실린다고 선언한다 — 해당 필드 description 참조.
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
        description=(
            "Line-level sequence number assigned by LS for the push frame. "
            "Owner reports it is always blank (2026-09-12, ~90% confidence); "
            "unverified in-repo — 저장소 내 라이브 TC3 프레임으로 대조한 바 "
            "없다. 오너 진술이 맞다면 채워진 적이 없으므로 정렬/중복제거 키로 "
            "쓰지 말 것. 아래 examples 는 상류 선언값이며 관측값이 아니다. "
            "(출처: 오너 진술 2026-09-12)"
        ),
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
        description=(
            "Order number for the event, as a string. 주문 접수 시 발행되며 "
            "체결 단위로 유일하지 않다 — 1주문이 분할체결되면 동일 값이 여러 "
            "체결 푸시에 반복 등장한다. 체결 단위 식별 / 중복제거 키로 쓰지 "
            "말 것(``ccls_no`` 참조). (출처: 오너 진술 2026-09-12)"
        ),
        examples=["100001"],
    )
    orgn_ordr_no: str = Field(
        ...,
        title="원주문번호 (Original order number)",
        description=(
            "Original order number this event references ('0' / 빈 "
            "문자열('') when not applicable). Conditionally populated: "
            "'' / '0' on new (신규) orders, carries the original order number "
            "only on modify (정정) / cancel (취소) orders — 판정은 ``ordr_ccd`` "
            "와 교차 확인할 것. 값이 안 채워지는 경우에도 필드는 스키마상 항상 "
            "존재(required)하므로 판별은 hasattr / ``is None`` 이 아니라 "
            "``== ''`` / ``== '0'`` 으로 하라. "
            "(출처: 오너 진술 2026-09-12, ~90% 확신 · 라이브 프레임 미관측)"
        ),
        examples=["", "0", "100001"],
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
        description=(
            "Exchange-assigned fill identifier, as a string. 체결이 성립할 때 "
            "발행된다 — 1주문이 분할체결되면 동일한 ``ordr_no`` 에 대해 N 개의 "
            "``ccls_no`` 가 발행된다. 따라서 체결 단위 식별 / 중복제거 키는 "
            "``ordr_no`` 가 아니라 ``ccls_no`` 여야 한다. "
            "(출처: 오너 진술 2026-09-12)"
        ),
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
            "alternatively represent an FCM fee. Both upstream readings are "
            "kept on record, and the upstream label remains ambiguous. "
            "2026-09-12 owner observation (~90% confidence): this field "
            "carries the FCM (foreign broker) fee, not a holding quantity — "
            "do not parse as quantity. 상류 라벨과 오너 관측이 갈리므로 값 "
            "자체는 LS 가 준 그대로 소비하되, 잔고 수량 목적의 파싱은 금지. "
            "(출처: 오너 진술 2026-09-12 · 라이브 프레임 미관측)"
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
        description=(
            "Spread-instrument flag. Upstream declares 'Y' = spread "
            "instrument, 'N' = outright (즉 상류 기준으로는 아웃라이트 "
            "체결에도 'N' 이 실린다). Owner observation (2026-09-12, ~90% "
            "confidence) says the ``sprd_*`` family is filled in only for "
            "spread-product trades; 다만 그 포괄 진술이 '스프레드 여부를 "
            "가리는 이 판별 플래그' 에까지 적용되는지는 오너가 말한 바 없어 "
            "미확인이다 — 판별 플래그마저 비면 스프레드 여부를 알 방법이 "
            "사라지므로 상류 해석이 오히려 유력하다. CONFLICT UNRESOLVED: "
            "라이브 프레임으로 확정되기 전까지 'N' 과 빈 문자열('')을 모두 "
            "비(非)스프레드로 취급하라. 값이 안 채워지는 경우에도 필드는 "
            "스키마상 항상 존재(required)하며 빈 문자열('')로 온다 — 판별은 "
            "hasattr / ``is None`` 이 아니라 ``== ''`` 로 할 것. "
            "(출처: 오너 진술 2026-09-12 · 라이브 프레임 미관측)"
        ),
        examples=["Y", "N", ""],
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
        description=(
            "Reserved area; consume as returned by LS. Owner reports it is "
            "always blank (2026-09-12, ~90% confidence); unverified in-repo — "
            "저장소 내 라이브 TC3 프레임으로 대조한 바 없다. 더미 필드이므로 "
            "의미 있는 값이 실려 오는 경우를 가정하지 말 것. "
            "(출처: 오너 진술 2026-09-12)"
        ),
        examples=[""],
    )
    sprd_is_cd: str = Field(
        ...,
        title="스프레드종목코드 (Spread instrument code)",
        description=(
            "Spread instrument code for spread fills; empty otherwise. "
            "LS-internal spread-symbol encoding is not declared in "
            "available source — consume as returned by LS, do not assume "
            "a particular leg-pair format. Owner observation (2026-09-12, "
            "~90% confidence): populated only when a spread product is "
            "traded — 일반 해외선물 체결에서는 빈 문자열('')로 온다. 필드는 "
            "스키마상 항상 존재(required)하며 값만 비어 있으므로, 판별은 "
            "hasattr / ``is None`` 이 아니라 ``== ''`` 로 할 것. "
            "(출처: 오너 진술 2026-09-12 · 라이브 프레임 미관측)"
        ),
        examples=[""],
    )
    lme_prdt_ccd: str = Field(
        ...,
        title="LME상품유형 (LME product-type code)",
        description=(
            "LME product-type classifier. Upstream source: populated for "
            "LME contracts, blank otherwise. Owner observation (2026-09-12, "
            "~90% confidence): ordinary (non-LME) overseas futures carry "
            "'0', LME items carry '1' / '2'. CONFLICT UNRESOLVED — 상류는 "
            "비LME 를 공백이라 하고 오너는 '0' 이라 한다; 어느 쪽도 버리지 "
            "않고 병기하며 라이브 프레임을 받아야 결론난다(live frame "
            "needed). 잠정 지침으로 소비 측이 '' 와 '0' 을 모두 'LME 상품 "
            "아님' 으로 동일 취급할 수는 있으나, 이는 오너 해석 쪽으로 충돌을 "
            "닫는 선택이다 — 상류 해석('populated for LME contracts, blank "
            "otherwise')이 맞다면 '0' 은 값이 실린 상태 = LME 계약일 수 있어 "
            "이 잠정 규칙은 LME 계약을 비LME 로 접는 오분류 위험을 안는다. "
            "Code mapping otherwise not declared in available source. "
            "아래 examples 는 상류 선언('')과 오너 진술('0' / '1' / '2')을 "
            "합집합으로 나열한 것이며 관측값이 아니다. "
            "(출처: 오너 진술 2026-09-12 · 라이브 프레임 미관측)"
        ),
        examples=["", "0", "1", "2"],
    )
    lme_sprd_prc: str = Field(
        ...,
        title="LME스프레드가격 (LME spread price)",
        description=(
            "LME spread price as a string (populated for LME contracts; "
            "empty otherwise). Scale not declared. Owner observation "
            "(2026-09-12, ~90% confidence): filled in only when a spread "
            "product is traded — 일반 해외선물 체결에서는 빈 문자열('')로 "
            "온다. 필드는 스키마상 항상 존재(required)하며 값만 비어 "
            "있으므로, 판별은 hasattr / ``is None`` 이 아니라 ``== ''`` 로 할 "
            "것. (출처: 오너 진술 2026-09-12 · 라이브 프레임 미관측)"
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
