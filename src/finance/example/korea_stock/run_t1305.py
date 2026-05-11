import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1305

logger = logging.getLogger(__name__)

load_dotenv()


# LS-declared enum mapping for ``T1305OutBlock1.sign`` (1=상한 / 2=상승 /
# 3=보합 / 4=하한 / 5=하락). h_sign and l_sign LS-declared enum:
# 2=상승 / 3=보합 / 5=하락 (codes 1 and 4 not present per LS declaration).
# ``o_sign`` enum mapping is NOT declared in the LS source available to
# this codebase — printed as raw value returned by LS.
# Sign conventions of change / o_change / h_change / l_change / fpvolume /
# covolume / ppvolume are NOT declared in available LS source — printed as
# returned. Currency unit of price fields is NOT declared in available source;
# LS labels value and marketcap as "(단위:백만)" only.
_SIGN_GLYPH = {"1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"}
_HSL_SIGN_GLYPH = {"2": "△", "3": "-", "5": "▽"}


def test_req_t1305():
    """t1305 기간별주가 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 인디에프(001200) 의 일봉 조회 (KRX, 1건).
    m_t1305 = ls.국내주식().시세().기간별주가(
        t1305.T1305InBlock(
            shcode="001200",
            dwmcode=1,       # 1=일(daily) / 2=주(weekly) / 3=월(monthly)
            date="",         # 첫 조회시 빈 문자열, 연속 조회시 이전 OutBlock date
            idx=0,           # LS 명세: 사용안함 — int 0 전송
            cnt=1,           # LS 명세: 1 이상
            exchgubun="K",   # K=KRX / N=NXT / U=통합
        )
    )

    response = m_t1305.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회 date: {response.cont_block.date}, cnt: {response.cont_block.cnt}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 140)
    logger.info(
        f"{'날짜':>10} {'종가':>8} {'sign':>4} {'전일대비':>9} {'등락률':>8} "
        f"{'체결강도':>9} {'거래량':>12} {'거래대금(백만)':>14} {'시총(백만)':>12} "
        f"{'o_sign':>6} {'h_sign':>6} {'l_sign':>6}"
    )
    logger.info("-" * 140)

    for item in response.block:
        sign_glyph = _SIGN_GLYPH.get(item.sign, item.sign)
        h_glyph = _HSL_SIGN_GLYPH.get(item.h_sign, item.h_sign)
        l_glyph = _HSL_SIGN_GLYPH.get(item.l_sign, item.l_sign)
        # o_sign: raw output (enum mapping not declared in LS source)
        logger.info(
            f"{item.date:>10} {item.close:>8,} {sign_glyph:>4} "
            f"{item.change:>+9,} {item.diff:>+7.2f}% "
            f"{item.chdegree:>9.2f} {item.volume:>12,} "
            f"{item.value:>14,} {item.marketcap:>12,} "
            f"{item.o_sign:>6} {h_glyph:>6} {l_glyph:>6}"
        )


def test_occurs_req_t1305():
    """t1305 기간별주가 연속조회 테스트 (date cursor 기반 전체 페이지 수집)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1305 = ls.국내주식().시세().기간별주가(
        t1305.T1305InBlock(
            shcode="005930",
            dwmcode=1,       # 1=일봉
            date="",
            idx=0,
            cnt=900,
            exchgubun="K",
        )
    )

    responses = m_t1305.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 일봉 행: {total}건")


if __name__ == "__main__":
    test_req_t1305()
