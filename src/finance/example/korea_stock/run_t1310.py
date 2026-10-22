import logging
import os

from dotenv import load_dotenv

from programgarden_finance import LS, t1310

logger = logging.getLogger(__name__)

load_dotenv()


# LS does NOT declare a ``T1310OutBlock1.sign`` enum mapping (unlike t1302
# where 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 is published). For t1310
# we therefore print ``sign`` as the raw single-character code returned by
# LS, without glyph translation. Likewise, the currency unit of ``price``,
# the sign convention of ``change`` / ``revolume`` / ``rechecnt``, the
# bucket-start vs. bucket-end interpretation of ``chetime``, and the
# precise structure of the ``cts_time`` cursor (observed to contain
# embedded null bytes) are not declared in available LS source — values
# are printed as returned by LS without unit annotations.


def test_req_t1310():
    """t1310 주식당일전일분틱조회 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 한솔홀딩스(001200) 당일 분 단위 시세 (KRX). LS official example 와 동일.
    m_t1310 = ls.국내주식().시세().주식당일전일분틱조회(
        t1310.T1310InBlock(
            daygb="0",       # 0=당일 / 1=전일
            timegb="0",      # 0=분 / 1=틱
            shcode="001200",
            endtime="",      # 첫 조회시 빈 문자열, 연속 조회시는 cts_time 으로 이어감
            cts_time="",     # 첫 조회시 빈 문자열, 다음 조회시 이전 cts_time
            exchgubun="K",   # K=KRX / N=NXT / U=통합
        )
    )

    response = m_t1310.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        # cts_time 은 LS-defined opaque token (embedded null bytes 가능)
        logger.info(f"연속조회 cts_time (repr): {response.cont_block.cts_time!r}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 110)
    logger.info(
        f"{'시간':>10} {'현재가':>8} {'sign':>4} {'전일대비':>9} {'등락률':>8} "
        f"{'체결강도':>9} {'거래량':>11} {'순체결량':>11} {'순체결건수':>10}"
    )
    logger.info("-" * 110)

    for item in response.block:
        # chetime / sign 모두 LS 가 반환한 raw 값 그대로 (glyph 변환 / 정규화 금지).
        logger.info(
            f"{item.chetime!r:>10} {item.price:>8,} {item.sign:>4} "
            f"{item.change:>+9,} {item.diff:>+7.2f}% "
            f"{item.chdegree:>9.2f} {item.volume:>11,} "
            f"{item.revolume:>+11,} {item.rechecnt:>+10,}"
        )


def test_occurs_req_t1310():
    """t1310 주식당일전일분틱조회 연속조회 테스트 (cts_time cursor 기반)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1310 = ls.국내주식().시세().주식당일전일분틱조회(
        t1310.T1310InBlock(
            daygb="0",
            timegb="0",
            shcode="001200",
            endtime="",
            cts_time="",
            exchgubun="K",
        )
    )

    responses = m_t1310.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 분틱 행: {total}건")


if __name__ == "__main__":
    test_req_t1310()
