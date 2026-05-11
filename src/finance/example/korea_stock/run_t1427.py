import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1427

logger = logging.getLogger(__name__)

load_dotenv()


# LS-declared enum mapping for ``T1427OutBlock1.sign``
# (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). Currency unit of price /
# lmtprice / open / high / low / change fields, sign convention of
# ``change``, ``lmtdaycnt`` counting window, ``rate`` reference base and
# row ordering are NOT declared in available source; values are printed
# as returned by LS without unit annotations.

_SIGN_GLYPH = {"1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"}


def test_req_t1427_upper():
    """t1427 상한직전 종목 조회 — 단건 (signgubun=1)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 상한직전 — 전체 시장, 등락률 임계치 없음, 대상제외 없음, 전일 상하한 제외.
    m_t1427 = ls.국내주식().시세().상하한가직전(
        t1427.T1427InBlock(
            qrygb="1",        # 1=20종목씩 조회 / 그외=전체조회
            gubun="0",        # 0=전체 / 1=KOSPI / 2=KOSDAQ
            signgubun="1",    # 1=상한직전 / 2=하한직전
            diff=0,
            jc_num=0,
            sprice=0,
            eprice=0,
            volume=0,
            idx=0,
            jshex="c",        # 전일 상/하한가 종목 제외
        )
    )

    response = m_t1427.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(
            f"총 결과 cnt: {response.cont_block.cnt}, 연속조회 idx: {response.cont_block.idx}"
        )

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 140)
    logger.info(
        f"{'종목코드':>8} {'한글명':>16} {'현재가':>10} {'sign':>4} "
        f"{'전일대비':>10} {'등락률':>8} {'거래량':>12} {'거래증가율':>10} "
        f"{'상/하한가':>10} {'대비율':>9} {'시가':>8} {'고가':>8} {'저가':>8} "
        f"{'연속':>4} {'거래대금':>10} {'시가총액':>10}"
    )
    logger.info("-" * 140)

    for item in response.block:
        glyph = _SIGN_GLYPH.get(item.sign, item.sign)
        logger.info(
            f"{item.shcode:>8} {item.hname:>16} {item.price:>10,} {glyph:>4} "
            f"{item.change:>+10,} {item.diff:>+7.2f}% {item.volume:>12,} "
            f"{item.diff_vol:>+9.2f}% {item.lmtprice:>10,} {item.rate:>+8.2f}% "
            f"{item.open:>8,} {item.high:>8,} {item.low:>8,} {item.lmtdaycnt:>4} "
            f"{item.value:>10,} {item.total:>10,}"
        )


def test_req_t1427_lower():
    """t1427 하한직전 종목 조회 — 단건 (signgubun=2)."""

    logging.basicConfig(level=logging.INFO)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1427 = ls.국내주식().시세().상하한가직전(
        t1427.T1427InBlock(
            qrygb="1",
            gubun="0",
            signgubun="2",     # 하한직전
            diff=0,
            jc_num=0,
            sprice=0,
            eprice=0,
            volume=0,
            idx=0,
            jshex="c",
        )
    )

    response = m_t1427.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        return

    logger.info(f"하한직전 조회 건수: {len(response.block)}건")
    for item in response.block:
        logger.info(
            f"{item.shcode} {item.hname} 현재가={item.price:,} "
            f"등락률={item.diff:+.2f}% 하한가={item.lmtprice:,}"
        )


def test_occurs_req_t1427():
    """t1427 상한직전 연속조회 테스트 (idx cursor 기반 전체 페이지 수집)."""

    logging.basicConfig(level=logging.INFO)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1427 = ls.국내주식().시세().상하한가직전(
        t1427.T1427InBlock(
            qrygb="1",
            gubun="0",
            signgubun="1",
            diff=0,
            jc_num=0,
            sprice=0,
            eprice=0,
            volume=0,
            idx=0,
            jshex="c",
        )
    )

    responses = m_t1427.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 행: {total}건")


if __name__ == "__main__":
    test_req_t1427_upper()
