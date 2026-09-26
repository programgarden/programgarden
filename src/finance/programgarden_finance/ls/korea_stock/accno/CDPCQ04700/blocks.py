"""Pydantic models for LS Securities OpenAPI CDPCQ04700 (Account Transaction History).

CDPCQ04700 returns the account transaction history (deposit / withdrawal /
trade ledger) for a date range. The reviewed REST contract has five blocks:
    - ``CDPCQ04700OutBlock1`` (block1): echo-back of the input parameters.
    - ``CDPCQ04700OutBlock2`` (block2): summary — account display name and
      record count.
    - ``CDPCQ04700OutBlock3`` (block3): per-transaction detail rows
      including transaction date, classification, summary text, quantity /
      amount, fees and taxes.
    - ``CDPCQ04700OutBlock4`` (block4): PnL/turnover/commission summary.
    - ``CDPCQ04700OutBlock5`` (block5): inflow/outflow/trade summary.

The schema is not evidence that LS populates every field for every account or
query. Check raw_payload and model_fields_set before treating a value as an
observed fact. Missing, null, blank and explicit zero are distinct. In particular,
aggregate MnyinAmt alone does not establish a USD deposit. See
``docs/cdpcq04700_contract.md`` for the source and remaining live-evidence gaps.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from copy import deepcopy
from decimal import Decimal
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CDPCQ04700RequestHeader(BlockRequestHeader):
    """CDPCQ04700 request header. Inherits the standard LS request header schema."""
    pass


class CDPCQ04700ResponseHeader(BlockResponseHeader):
    """CDPCQ04700 response header. Standard LS response header schema."""
    pass


class CDPCQ04700InBlock1(BaseModel):
    """CDPCQ04700InBlock1 — input block for account transaction history.

    Specify the date range with ``QrySrtDt`` / ``QryEndDt`` (YYYYMMDD).
    The default asset-class filter is domestic stock. The official contract
    also declares 05 (overseas stock), but actual account/field coverage must be
    verified separately. Use 00 only when an all-asset query is intended.
    """

    RecCnt: int = Field(default=1, description="Record count in the official REST request example.")
    QryTp: str = Field(
        default="0",
        title="조회구분 (Query mode)",
        description=(
            "Official query modes: 0 all, 1 cash deposits/withdrawals, 2 security "
            "transfers, 3 trades, 4 currency exchange, 9 other. A query mode "
            "does not prove actual field population or monetary completeness."
        ),
        examples=["0", "1"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description=(
            "Legacy SDK input retained for compatibility. The reviewed REST "
            "request table does not include this field; do not infer its "
            "account-selection behavior. The diagnostic example omits it."
        ),
        examples=["", "12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password)",
        description=(
            "Legacy SDK input retained for compatibility. The reviewed REST "
            "request table does not include this field. Do not supply or log "
            "an account password for the diagnostic example."
        ),
        examples=[""],
    )
    QrySrtDt: str = Field(
        default="",
        title="조회시작일 (Query start date, YYYYMMDD)",
        description=(
            "Inclusive lower bound of the query date range, formatted as "
            "YYYYMMDD."
        ),
        examples=["", "20260101", "20260201"],
    )
    QryEndDt: str = Field(
        default="",
        title="조회종료일 (Query end date, YYYYMMDD)",
        description=(
            "Inclusive upper bound of the query date range, formatted as "
            "YYYYMMDD."
        ),
        examples=["", "20260131", "20260228"],
    )
    SrtNo: int = Field(
        default=0,
        title="시작번호 (Pagination start number)",
        description=(
            "Starting record number. The official example starts at 0. "
            "The reviewed field table does not define a continuation algorithm; "
            "do not infer one from the largest transaction number."
        ),
        examples=[0, 100],
    )
    PdptnCode: str = Field(
        default="01",
        title="상품유형코드 (Product type code)",
        description=(
            "The official REST table specifies 01. Do not infer additional "
            "product codes from another TR."
        ),
        examples=["01"],
    )
    IsuLgclssCode: str = Field(
        default="01",
        title="종목대분류코드 (Asset major-class code)",
        description=(
            "Official asset classes: 00 all, 01 stocks, 02 bonds, 03 futures, "
            "04 funds, 05 overseas stocks, 06 overseas derivatives. Default 01 "
            "does not establish overseas-stock cash-transfer coverage."
        ),
        examples=["01", "02"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "Instrument filter, length 12. The official REST example uses an "
            "ISIN (KR7000020008). Empty requests an unfiltered symbol scope."
        ),
        examples=["", "KR7000020008"],
    )


class CDPCQ04700Request(BaseModel):
    """CDPCQ04700 full request envelope (header + body + setup options)."""

    header: CDPCQ04700RequestHeader = CDPCQ04700RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CDPCQ04700",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CDPCQ04700InBlock1"], CDPCQ04700InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CDPCQ04700",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class _ResponseBlock(BaseModel):
    """Keep undocumented fields for diagnostics; presence is model_fields_set.

    Existing defaults remain compatible. A default value is not a broker fact.
    Extra fields are preserved, not declared validated financial evidence.
    """

    model_config = ConfigDict(extra="allow")


class CDPCQ04700OutBlock1(_ResponseBlock):
    """CDPCQ04700OutBlock1 — input echo-back block."""

    QryTp: str = Field(
        default="0",
        title="조회구분 (Query mode)",
        description="Echo of the input ``QryTp``.",
        examples=["0", "1"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Echo of the input ``AcntNo``. Length 11.",
        examples=["", "12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password marker)",
        description="Always returned redacted by the server.",
        examples=[""],
    )
    QrySrtDt: str = Field(
        default="",
        title="조회시작일 (Query start date, YYYYMMDD)",
        description="Echo of the input ``QrySrtDt``.",
        examples=["", "20260101"],
    )
    QryEndDt: str = Field(
        default="",
        title="조회종료일 (Query end date, YYYYMMDD)",
        description="Echo of the input ``QryEndDt``.",
        examples=["", "20260131"],
    )
    SrtNo: int | Literal[""] | None = Field(
        default=0,
        title="시작번호 (Pagination start number)",
        description="Echo of the input ``SrtNo``.",
        examples=[0, 100],
    )
    PdptnCode: str = Field(
        default="01",
        title="상품유형코드 (Product type code)",
        description="Echo of the input ``PdptnCode``.",
        examples=["01", "02"],
    )
    IsuLgclssCode: str = Field(
        default="01",
        title="종목대분류코드 (Asset major-class code)",
        description="Echo of the input ``IsuLgclssCode``.",
        examples=["01", "02"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="Echo of the input ``IsuNo``.",
        examples=["", "A005930"],
    )

    # Additional fields from the reviewed official REST contract.
    RecCnt: int | Literal[""] | None = Field(default=None, title="레코드갯수",
        description="Broker-reported RecCnt. Documented length 5; actual population and currency semantics are not guaranteed.")


class CDPCQ04700OutBlock2(_ResponseBlock):
    """CDPCQ04700OutBlock2 — transaction history summary block.

    Returns the account display name and the count of transaction records
    returned for the requested date range.
    """

    RecCnt: int | Literal[""] | None = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of transaction rows returned in ``block3``.",
        examples=[0, 27, 312],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account display name)",
        description="Korean display name of the account.",
        examples=["", "홍길동"],
    )


class CDPCQ04700OutBlock3(_ResponseBlock):
    """CDPCQ04700OutBlock3 — per-transaction detail row.

    Each row describes one transaction (deposit / withdrawal / trade
    settlement) with quantity, amount, fees and taxes. Trade rows additionally
    populate the symbol, side, quantity and unit price fields.
    """

    TrdDt: str = Field(
        default="",
        title="거래일자 (Transaction date, YYYYMMDD)",
        description="Trading / settlement date of the transaction.",
        examples=["", "20260203", "20260307"],
    )
    TrdNo: int | Literal[""] | None = Field(
        default=0,
        title="거래번호 (Transaction number)",
        description="LS-assigned transaction number for the date.",
        examples=[1, 27, 312],
    )
    TpCodeNm: str = Field(
        default="",
        title="구분코드명 (Classification display name)",
        description=(
            "Korean display name of the transaction classification (e.g., "
            "매수, 매도, 입금, 출금)."
        ),
        examples=["", "매수", "매도", "입금"],
    )
    SmryNm: str = Field(
        default="",
        title="적요명 (Summary text)",
        description=(
            "Free-form Korean summary text attached by LS to the transaction."
        ),
        examples=["", "유가증권매수", "유가증권매도"],
    )
    TrdQty: int | Literal[""] | None = Field(
        default=0,
        title="거래수량 (Transaction quantity)",
        description="Quantity of the transaction (shares for trade rows).",
        examples=[0, 10, 100],
    )
    TrdAmt: int | Literal[""] | None = Field(
        default=0,
        title="거래금액 (Transaction amount)",
        description="Transaction amount. Currency: KRW.",
        examples=[0, 700_000, 7_000_000],
    )
    AdjstAmt: int | Literal[""] | None = Field(
        default=0,
        title="정산금액 (Settled amount)",
        description=(
            "Settled amount net of fees and taxes. Currency: KRW."
        ),
        examples=[0, 698_500, 6_985_000],
    )
    CmsnAmt: int | Literal[""] | None = Field(
        default=0,
        title="수수료 (Fee)",
        description="Brokerage fee for this transaction. Currency: KRW.",
        examples=[0, 1_500],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name. Empty for non-trade rows.",
        examples=["", "삼성전자", "SK하이닉스"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code. Empty for non-trade rows."
        ),
        examples=["", "A005930"],
    )
    EvrTax: int | Literal[""] | None = Field(
        default=0,
        title="제세금 (Tax)",
        description="Securities transaction tax and other taxes. Currency: KRW.",
        examples=[0, 7_500],
    )
    TrxTime: str = Field(
        default="",
        title="처리시각 (Processing time)",
        description=(
            "Server-side processing timestamp. Format follows LS convention "
            "(HHMMSS or HHMMSSmmm) — consume as returned."
        ),
        examples=["", "093015", "153000"],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분 (Side code)",
        description=(
            "Side code for trade rows. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    TrdPrc: float | Literal[""] | None = Field(
        default=0.0,
        title="거래단가 (Transaction unit price)",
        description=(
            "Per-share transaction price for trade rows. Currency: KRW. "
            "LS may serialize this value as a string; Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 70_000.0, 250_000.0],
    )

    # Additional fields from the reviewed official REST contract.
    AcntNo: str | None = Field(default=None, title="계좌번호",
        description="Broker-reported AcntNo. Documented length 20; actual population and currency semantics are not guaranteed.")
    SmryNo: str | None = Field(default=None, title="적요번호",
        description="Broker summary code; preserve the exact code and do not infer a universal deposit classification.")
    CancTpNm: str | None = Field(default=None, title="취소구분",
        description="Broker cancellation classification text. Do not count cancelled/reversed events as new funding.")
    Trtax: int | Literal[""] | None = Field(default=None, title="거래세",
        description="Broker-reported Trtax. Documented length 16; actual population and currency semantics are not guaranteed.")
    FcurrAdjstAmt: Decimal | Literal[""] | None = Field(default=None, title="외화정산금액",
        description="Foreign-currency settled amount. Interpret only with the same row currency and verified transaction classification.")
    OvdSum: int | Literal[""] | None = Field(default=None, title="연체합",
        description="Broker-reported OvdSum. Documented length 16; actual population and currency semantics are not guaranteed.")
    DpsBfbalAmt: int | Literal[""] | None = Field(default=None, title="예수금전잔금액",
        description="Deposit balance before the transaction; not the amount of the new deposit.")
    SellPldgRfundAmt: int | Literal[""] | None = Field(default=None, title="매도담보상환금",
        description="Broker-reported SellPldgRfundAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    DpspdgLoanBfbalAmt: int | Literal[""] | None = Field(default=None, title="예탁담보대출전잔금액",
        description="Broker-reported DpspdgLoanBfbalAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    TrdmdaNm: str | None = Field(default=None, title="거래매체명",
        description="Broker-reported TrdmdaNm. Documented length 40; actual population and currency semantics are not guaranteed.")
    OrgTrdNo: int | Literal[""] | None = Field(default=None, title="원거래번호",
        description="Original transaction number. Cancellation/reversal semantics require verified broker evidence.")
    TrdUprc: Decimal | Literal[""] | None = Field(default=None, title="거래단가",
        description="Officially documented transaction unit price. The compatibility TrdPrc field is not an alias.")
    FcurrCmsnAmt: Decimal | Literal[""] | None = Field(default=None, title="외화수수료금액",
        description="Broker-reported FcurrCmsnAmt. Documented length 15.2; actual population and currency semantics are not guaranteed.")
    RfundDiffAmt: int | Literal[""] | None = Field(default=None, title="상환차이금액",
        description="Broker-reported RfundDiffAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    RepayAmtSum: int | Literal[""] | None = Field(default=None, title="변제금합계",
        description="Broker-reported RepayAmtSum. Documented length 16; actual population and currency semantics are not guaranteed.")
    SecCrbalQty: int | Literal[""] | None = Field(default=None, title="유가증권금잔수량",
        description="Broker-reported SecCrbalQty. Documented length 16; actual population and currency semantics are not guaranteed.")
    CslLoanRfundIntrstAmt: int | Literal[""] | None = Field(default=None, title="매도대금담보대출상환이자금액",
        description="Broker-reported CslLoanRfundIntrstAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    DpspdgLoanCrbalAmt: int | Literal[""] | None = Field(default=None, title="예탁담보대출금잔금액",
        description="Broker-reported DpspdgLoanCrbalAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    Inouno: int | Literal[""] | None = Field(default=None, title="출납번호",
        description="Broker-reported Inouno. Documented length 10; actual population and currency semantics are not guaranteed.")
    ChckAmt: int | Literal[""] | None = Field(default=None, title="수표금액",
        description="Broker-reported ChckAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    TaxSumAmt: int | Literal[""] | None = Field(default=None, title="세금합계금액",
        description="Broker-reported TaxSumAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    FcurrTaxSumAmt: Decimal | Literal[""] | None = Field(default=None, title="외화세금합계금액",
        description="Broker-reported FcurrTaxSumAmt. Documented length 26.6; actual population and currency semantics are not guaranteed.")
    IntrstUtlfee: int | Literal[""] | None = Field(default=None, title="이자이용료",
        description="Broker-reported IntrstUtlfee. Documented length 16; actual population and currency semantics are not guaranteed.")
    MnyDvdAmt: int | Literal[""] | None = Field(default=None, title="배당금액",
        description="Broker-reported dividend amount, documented length 16. Population, currency and gross/net basis are not guaranteed. It is not independently evidence of an overseas USD dividend. Reconcile transaction identity, explicit currency, cash effect, withholding and cancellations; blank/zero is not proof of no dividend.")
    RcvblOcrAmt: int | Literal[""] | None = Field(default=None, title="미수발생금액",
        description="Broker-reported RcvblOcrAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    TrxBrnNo: str | None = Field(default=None, title="처리지점번호",
        description="Broker-reported TrxBrnNo. Documented length 3; actual population and currency semantics are not guaranteed.")
    TrxBrnNm: str | None = Field(default=None, title="처리지점명",
        description="Broker-reported TrxBrnNm. Documented length 40; actual population and currency semantics are not guaranteed.")
    DpspdgLoanAmt: int | Literal[""] | None = Field(default=None, title="예탁담보대출금액",
        description="Broker-reported DpspdgLoanAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    DpspdgLoanRfundAmt: int | Literal[""] | None = Field(default=None, title="예탁담보대출상환금액",
        description="Broker-reported DpspdgLoanRfundAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BasePrc: Decimal | Literal[""] | None = Field(default=None, title="기준가",
        description="Broker-reported BasePrc. Documented length 13.2; actual population and currency semantics are not guaranteed.")
    DpsCrbalAmt: int | Literal[""] | None = Field(default=None, title="예수금금잔금액",
        description="Broker-reported DpsCrbalAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BoaAmt: int | Literal[""] | None = Field(default=None, title="과표",
        description="Broker-reported BoaAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    MnyoutAbleAmt: int | Literal[""] | None = Field(default=None, title="출금가능금액",
        description="Broker-reported MnyoutAbleAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BcrLoanOcrAmt: int | Literal[""] | None = Field(default=None, title="수익증권담보대출발생금",
        description="Broker-reported BcrLoanOcrAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BcrLoanBfbalAmt: int | Literal[""] | None = Field(default=None, title="수익증권담보대출전잔금",
        description="Broker-reported BcrLoanBfbalAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BnsBasePrc: Decimal | Literal[""] | None = Field(default=None, title="매매기준가",
        description="Broker-reported BnsBasePrc. Documented length 20.1; actual population and currency semantics are not guaranteed.")
    TaxchrBasePrc: Decimal | Literal[""] | None = Field(default=None, title="과세기준가",
        description="Broker-reported TaxchrBasePrc. Documented length 20.1; actual population and currency semantics are not guaranteed.")
    TrdUnit: int | Literal[""] | None = Field(default=None, title="거래좌수",
        description="Broker-reported TrdUnit. Documented length 16; actual population and currency semantics are not guaranteed.")
    BalUnit: int | Literal[""] | None = Field(default=None, title="잔고좌수",
        description="Broker-reported BalUnit. Documented length 16; actual population and currency semantics are not guaranteed.")
    EvalAmt: int | Literal[""] | None = Field(default=None, title="평가금액",
        description="Broker-reported EvalAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BcrLoanRfundAmt: int | Literal[""] | None = Field(default=None, title="수익증권담보대출상환금",
        description="Broker-reported BcrLoanRfundAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BcrLoanCrbalAmt: int | Literal[""] | None = Field(default=None, title="수익증권담보대출금잔금",
        description="Broker-reported BcrLoanCrbalAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    AddMgnOcrTotamt: int | Literal[""] | None = Field(default=None, title="추가증거금발생총액",
        description="Broker-reported AddMgnOcrTotamt. Documented length 16; actual population and currency semantics are not guaranteed.")
    AddMnyMgnOcrAmt: int | Literal[""] | None = Field(default=None, title="추가현금증거금발생금액",
        description="Broker-reported AddMnyMgnOcrAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    AddMgnDfryTotamt: int | Literal[""] | None = Field(default=None, title="추가증거금납부총액",
        description="Broker-reported AddMgnDfryTotamt. Documented length 16; actual population and currency semantics are not guaranteed.")
    AddMnyMgnDfryAmt: int | Literal[""] | None = Field(default=None, title="추가현금증거금납부금액",
        description="Broker-reported AddMnyMgnDfryAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BnsplAmt: int | Literal[""] | None = Field(default=None, title="매매손익금액",
        description="Broker-reported BnsplAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    Ictax: int | Literal[""] | None = Field(default=None, title="소득세",
        description="Broker-reported Ictax. Documented length 16; actual population and currency semantics are not guaranteed.")
    Ihtax: int | Literal[""] | None = Field(default=None, title="주민세",
        description="Broker-reported Ihtax. Documented length 16; actual population and currency semantics are not guaranteed.")
    LoanDt: str | None = Field(default=None, title="대출일",
        description="Broker-reported LoanDt. Documented length 8; actual population and currency semantics are not guaranteed.")
    CrcyCode: str | None = Field(default=None, title="통화코드",
        description="Broker-reported currency code. Missing or blank currency must not be assumed to mean USD.")
    FcurrAmt: Decimal | Literal[""] | None = Field(default=None, title="외화금액",
        description="Foreign-currency amount; the field alone does not establish an external cash deposit.")
    FcurrTrdAmt: Decimal | Literal[""] | None = Field(default=None, title="외화거래금액",
        description=("Reported amount under the foreign-transaction field name. Also observed populated "
                     "on a transfer with blank currency and zero foreign balances. Never infer USD from "
                     "this field name; reconcile explicit currency, classification and balance changes."))
    FcurrDps: Decimal | Literal[""] | None = Field(default=None, title="외화예수금",
        description="Foreign-currency deposit balance, not a cash-transfer event.")
    FcurrDpsBfbalAmt: Decimal | Literal[""] | None = Field(default=None, title="외화예수금전잔금액",
        description="Foreign-currency deposit balance before the transaction; not a cash-transfer amount.")
    OppAcntNm: str | None = Field(default=None, title="상대계좌명",
        description="Broker-reported OppAcntNm. Documented length 40; actual population and currency semantics are not guaranteed.")
    OppAcntNo: str | None = Field(default=None, title="상대계좌번호",
        description="Broker-reported OppAcntNo. Documented length 20; actual population and currency semantics are not guaranteed.")
    LoanRfundAmt: int | Literal[""] | None = Field(default=None, title="대출상환금액",
        description="Broker-reported LoanRfundAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    LoanIntrstAmt: int | Literal[""] | None = Field(default=None, title="대출이자금액",
        description="Broker-reported LoanIntrstAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    AskpsnNm: str | None = Field(default=None, title="의뢰인명",
        description="Broker-reported AskpsnNm. Documented length 40; actual population and currency semantics are not guaranteed.")
    OrdDt: str | None = Field(default=None, title="주문일자",
        description="Broker-reported OrdDt. Documented length 8; actual population and currency semantics are not guaranteed.")
    TrdXchrat: Decimal | Literal[""] | None = Field(default=None, title="거래환율",
        description="Broker-reported TrdXchrat. Documented length 15.4; actual population and currency semantics are not guaranteed.")
    RdctCmsn: Decimal | Literal[""] | None = Field(default=None, title="감면수수료",
        description="Broker-reported RdctCmsn. Documented length 21.4; actual population and currency semantics are not guaranteed.")
    FcurrStmpTx: Decimal | Literal[""] | None = Field(default=None, title="외화인지세",
        description="Broker-reported FcurrStmpTx. Documented length 21.4; actual population and currency semantics are not guaranteed.")
    FcurrElecfnTrtax: Decimal | Literal[""] | None = Field(default=None, title="외화전자금융거래세",
        description="Broker-reported FcurrElecfnTrtax. Documented length 21.4; actual population and currency semantics are not guaranteed.")
    FcstckTrtax: Decimal | Literal[""] | None = Field(default=None, title="외화증권거래세",
        description="Broker-reported FcstckTrtax. Documented length 21.4; actual population and currency semantics are not guaranteed.")


class CDPCQ04700OutBlock4(_ResponseBlock):
    """Optional broker summary; missing values are not verified zero amounts."""

    RecCnt: int | Literal[""] | None = Field(default=None, title="레코드갯수",
        description="Broker-reported RecCnt. Documented length 5; actual population and currency semantics are not guaranteed.")
    PnlSumAmt: int | Literal[""] | None = Field(default=None, title="손익합계금액",
        description="Broker-reported PnlSumAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    CtrctAsm: int | Literal[""] | None = Field(default=None, title="약정누계",
        description="Broker-reported CtrctAsm. Documented length 16; actual population and currency semantics are not guaranteed.")
    CmsnAmtSumAmt: int | Literal[""] | None = Field(default=None, title="수수료합계금액",
        description="Broker-reported CmsnAmtSumAmt. Documented length 16; actual population and currency semantics are not guaranteed.")


class CDPCQ04700OutBlock5(_ResponseBlock):
    """Optional broker summary; missing values are not verified zero amounts."""

    RecCnt: int | Literal[""] | None = Field(default=None, title="레코드갯수",
        description="Broker-reported RecCnt. Documented length 5; actual population and currency semantics are not guaranteed.")
    MnyinAmt: int | Literal[""] | None = Field(default=None, title="입금금액",
        description="Reported aggregate cash inflow. This field does not identify USD or prove that every deposit is returned.")
    SecinAmt: int | Literal[""] | None = Field(default=None, title="입고금액",
        description="Broker-reported SecinAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    MnyoutAmt: int | Literal[""] | None = Field(default=None, title="출금금액",
        description="Reported aggregate cash outflow. Currency and actual field population require separate verification.")
    SecoutAmt: int | Literal[""] | None = Field(default=None, title="출고금액",
        description="Broker-reported SecoutAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    DiffAmt: int | Literal[""] | None = Field(default=None, title="차이금액",
        description="Broker-reported DiffAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    DiffAmt0: int | Literal[""] | None = Field(default=None, title="차이금액0",
        description="Broker-reported DiffAmt0. Documented length 16; actual population and currency semantics are not guaranteed.")
    SellQty: int | Literal[""] | None = Field(default=None, title="매도수량",
        description="Broker-reported SellQty. Documented length 16; actual population and currency semantics are not guaranteed.")
    SellAmt: int | Literal[""] | None = Field(default=None, title="매도금액",
        description="Broker-reported SellAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    SellCmsn: int | Literal[""] | None = Field(default=None, title="매도수수료",
        description="Broker-reported SellCmsn. Documented length 16; actual population and currency semantics are not guaranteed.")
    EvrTax: int | Literal[""] | None = Field(default=None, title="제세금",
        description="Broker-reported EvrTax. Documented length 19; actual population and currency semantics are not guaranteed.")
    FcurrSellAdjstAmt: Decimal | Literal[""] | None = Field(default=None, title="외화매도정산금액",
        description="Broker-reported FcurrSellAdjstAmt. Documented length 25.4; actual population and currency semantics are not guaranteed.")
    BuyQty: int | Literal[""] | None = Field(default=None, title="매수수량",
        description="Broker-reported BuyQty. Documented length 16; actual population and currency semantics are not guaranteed.")
    BuyAmt: int | Literal[""] | None = Field(default=None, title="매수금액",
        description="Broker-reported BuyAmt. Documented length 16; actual population and currency semantics are not guaranteed.")
    BuyCmsn: int | Literal[""] | None = Field(default=None, title="매수수수료",
        description="Broker-reported BuyCmsn. Documented length 16; actual population and currency semantics are not guaranteed.")
    ExecTax: int | Literal[""] | None = Field(default=None, title="체결세금",
        description="Broker-reported ExecTax. Documented length 16; actual population and currency semantics are not guaranteed.")
    FcurrBuyAdjstAmt: Decimal | Literal[""] | None = Field(default=None, title="외화매수정산금액",
        description="Broker-reported FcurrBuyAdjstAmt. Documented length 25.4; actual population and currency semantics are not guaranteed.")


class CDPCQ04700Response(BaseModel):
    """CDPCQ04700 full API response envelope."""

    header: Optional[CDPCQ04700ResponseHeader] = None
    block1: Optional[CDPCQ04700OutBlock1] = Field(
        default=None,
        title="CDPCQ04700OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters.",
    )
    block2: Optional[CDPCQ04700OutBlock2] = Field(
        default=None,
        title="CDPCQ04700OutBlock2 (Transaction summary)",
        description="Account display name and record count for the date range.",
    )
    block3: List[CDPCQ04700OutBlock3] = Field(
        default_factory=list,
        title="CDPCQ04700OutBlock3 (Per-transaction detail list)",
        description="List of per-transaction rows for the requested date range.",
    )
    block4: CDPCQ04700OutBlock4 | None = None
    block5: CDPCQ04700OutBlock5 | None = None
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = Field(default="", title="Response code")
    rsp_msg: str = Field(default="", title="Response message")
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_payload: Any = PrivateAttr(default_factory=dict)
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_payload(self) -> Any:
        """Original JSON copy for presence/blank/zero checks; may contain private account data.

        May retain a malformed non-object envelope for diagnostics. Excluded
        from model_dump/repr. Never print or publish without redaction.
        Actual currency coverage and deposit semantics still require observation.
        """
        return deepcopy(self._raw_payload)


    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
