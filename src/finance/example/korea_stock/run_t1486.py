import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1486

logger = logging.getLogger(__name__)

load_dotenv()


# LS-declared enum mapping for ``T1486OutBlock1.sign`` (1=상한 / 2=상승 /
# 3=보합 / 4=하한 / 5=하락). Other field semantics (currency unit of price
# fields, bucket-start vs bucket-end interpretation of ``chetime``, sign
# convention of ``change``, the exact session window the expected-conclusion
# stream covers) are NOT declared in the LS source available to this
# codebase — values are printed as returned by LS without unit annotations.
_SIGN_GLYPH = {"1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"}


def test_req_t1486():
    """t1486 시간별예상체결가 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 흥국화재(001200) 시간별 예상체결가 조회 (KRX, 최대 20건). LS 공식 예제 종목 사용.
    m_t1486 = ls.국내주식().시세().시간별예상체결가(
        t1486.T1486InBlock(
            shcode="001200",
            cts_time="",     # 첫 조회시 빈 문자열, 연속 조회시 이전 cts_time
            cnt=20,
            exchgubun="K",   # K=KRX / N=NXT / U=통합
        )
    )

    response = m_t1486.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회 cts_time: {response.cont_block.cts_time}")
        logger.info(f"거래소별 단축코드: {response.cont_block.ex_shcode}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 110)
    logger.info(
        f"{'시간':>10} {'예상체결가':>10} {'sign':>4} {'전일대비':>9} {'등락률':>8} "
        f"{'예상체결량':>11} {'매도호가':>9} {'매수호가':>9} {'매도잔량':>10} {'매수잔량':>10}"
    )
    logger.info("-" * 110)

    for item in response.block:
        glyph = _SIGN_GLYPH.get(item.sign, item.sign)
        logger.info(
            f"{item.chetime:>10} {item.price:>10,} {glyph:>4} "
            f"{item.change:>+9,} {item.diff:>+7.2f}% "
            f"{item.cvolume:>11,} {item.offerho1:>9,} {item.bidho1:>9,} "
            f"{item.offerrem1:>10,} {item.bidrem1:>10,}"
        )


def test_occurs_req_t1486():
    """t1486 시간별예상체결가 연속조회 테스트 (cts_time cursor 기반 전체 페이지 수집)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1486 = ls.국내주식().시세().시간별예상체결가(
        t1486.T1486InBlock(
            shcode="001200",
            cts_time="",
            cnt=100,
            exchgubun="K",
        )
    )

    responses = m_t1486.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 행: {total}건")


if __name__ == "__main__":
    test_req_t1486()
