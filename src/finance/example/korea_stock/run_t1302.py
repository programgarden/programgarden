import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1302

logger = logging.getLogger(__name__)

load_dotenv()


# LS-declared enum mapping for ``T1302OutBlock1.sign`` (1=상한 / 2=상승 /
# 3=보합 / 4=하한 / 5=하락). Other field semantics (currency unit of price
# fields, bucket-start vs bucket-end interpretation of ``chetime``, sign
# convention of ``change`` / ``revolume`` / ``rechecnt``) are NOT declared
# in the LS source available to this codebase — values are printed as
# returned by LS without unit annotations.
_SIGN_GLYPH = {"1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"}


def test_req_t1302():
    """t1302 주식분별주가조회 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 의 30초봉 조회 (KRX, 최대 50건).
    m_t1302 = ls.국내주식().시세().주식분별주가조회(
        t1302.T1302InBlock(
            shcode="005930",
            gubun="0",       # 0=30초 / 1=1분 / 2=3분 / 3=5분 / 4=10분 / 5=30분 / 6=60분
            time="",         # 첫 조회시 빈 문자열, 연속 조회시 이전 cts_time
            cnt=50,          # LS 명세: 1 이상 900 이하
            exchgubun="K",   # K=KRX / N=NXT / U=통합
        )
    )

    response = m_t1302.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회 cts_time: {response.cont_block.cts_time}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 110)
    logger.info(
        f"{'시간':>8} {'종가':>8} {'sign':>4} {'전일대비':>9} {'등락률':>8} "
        f"{'체결강도':>9} {'거래량':>11} {'순매수체결량':>13} {'순체결건수':>10}"
    )
    logger.info("-" * 110)

    for item in response.block:
        glyph = _SIGN_GLYPH.get(item.sign, item.sign)
        logger.info(
            f"{item.chetime:>8} {item.close:>8,} {glyph:>4} "
            f"{item.change:>+9,} {item.diff:>+7.2f}% "
            f"{item.chdegree:>9.2f} {item.volume:>11,} "
            f"{item.revolume:>+13,} {item.rechecnt:>+10,}"
        )


def test_occurs_req_t1302():
    """t1302 주식분별주가조회 연속조회 테스트 (cts_time cursor 기반 전체 페이지 수집)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1302 = ls.국내주식().시세().주식분별주가조회(
        t1302.T1302InBlock(
            shcode="005930",
            gubun="1",       # 1분봉
            time="",
            cnt=900,
            exchgubun="K",
        )
    )

    responses = m_t1302.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 분봉 행: {total}건")


if __name__ == "__main__":
    test_req_t1302()
