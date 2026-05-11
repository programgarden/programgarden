import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1488

logger = logging.getLogger(__name__)

load_dotenv()


# The output ``T1488OutBlock1.sign`` (전일대비구분) enum mapping is NOT
# declared by LS for t1488 in the source available to this codebase — value
# is printed verbatim without glyph substitution. Currency unit of price /
# quote / change fields, sign convention of ``change``, ``cnt`` counting
# window and row ordering are likewise undeclared; values are printed as
# returned by LS without unit annotations.


def test_req_t1488():
    """t1488 예상체결가등락율상위조회 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 예상체결가 기준 상승 등락률 상위 종목 조회 (전체 시장, 장전, 관리종목 제외).
    m_t1488 = ls.국내주식().시세().예상체결가등락율상위조회(
        t1488.T1488InBlock(
            gubun="0",           # 0=전체 / 1=KOSPI / 2=KOSDAQ
            sign="1",            # 1=상승 / 2=하락
            jgubun="1",          # 1=장전 / 2=장후 / 3=직전대비
            jongchk="0x00000080",  # 관리종목 제외
            idx=0,
            volume="0",          # 0=전체 / 1=1만+ / 2=5만+ / ... / 5=백만+
            yesprice=0,
            yeeprice=0,
            yevolume=0,
        )
    )

    response = m_t1488.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회 idx: {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 130)
    logger.info(
        f"{'종목코드':>8} {'한글명':>16} {'현재가':>10} {'sign':>4} "
        f"{'전일대비':>10} {'등락률':>8} {'누적거래량':>12} "
        f"{'매도호가':>10} {'매수호가':>10} {'매도잔량':>10} {'매수잔량':>10} "
        f"{'연속일수':>6} {'증거금율':>6} {'전일거래량':>12}"
    )
    logger.info("-" * 130)

    for item in response.block:
        logger.info(
            f"{item.shcode:>8} {item.hname:>16} {item.price:>10,} {item.sign:>4} "
            f"{item.change:>+10,} {item.diff:>+7.2f}% {item.volume:>12,} "
            f"{item.offerho:>10,} {item.bidho:>10,} {item.offerrem:>10,} {item.bidrem:>10,} "
            f"{item.cnt:>6} {item.jkrate:>6} {item.jnilvolume:>12,}"
        )


def test_occurs_req_t1488():
    """t1488 예상체결가등락율상위조회 연속조회 테스트 (idx cursor 기반 전체 페이지 수집)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1488 = ls.국내주식().시세().예상체결가등락율상위조회(
        t1488.T1488InBlock(
            gubun="0",
            sign="1",
            jgubun="1",
            jongchk="0x00000080",
            idx=0,
            volume="0",
            yesprice=0,
            yeeprice=0,
            yevolume=0,
        )
    )

    responses = m_t1488.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 행: {total}건")


if __name__ == "__main__":
    test_req_t1488()
