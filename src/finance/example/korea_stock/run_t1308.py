"""t1308 (주식시간대별체결조회챠트) reference run script.

LS-declared enum mapping for ``T1308OutBlock1.sign`` (per xingAPI
reference): 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락.

Field semantics LS does NOT declare (consume as returned by LS without
unit annotations):
    - Currency unit of price / open / high / low / change.
    - Sign convention of ``change``.
    - Exact format of ``chetime`` (HHMMSS vs HHMM00).
    - Cumulative-vs-per-bucket relationship of volume / mdvolume /
      msvolume / mdchecnt / mschecnt relative to ``cvolume``.
    - Bucket scope of OHLC (per row time bucket vs daily aggregate).
    - Token structure of ``ex_shcode``.
"""

import logging
import os

from dotenv import load_dotenv

from programgarden_finance import LS, t1308

logger = logging.getLogger(__name__)

load_dotenv()


_SIGN_GLYPH = {"1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"}


def test_req_t1308():
    """t1308 주식시간대별체결조회챠트 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 의 1분봉 시간대별 봉 데이터 조회 (KRX).
    m_t1308 = ls.국내주식().시세().주식시간대별체결조회챠트(
        t1308.T1308InBlock(
            shcode="005930",
            starttime="",     # 빈 문자열 = 장시작시간 이후 전체
            endtime="",       # 빈 문자열 = 장종료시간 이전 전체
            bun_term="01",    # 1분 간격 (2자리 zero-padded)
            exchgubun="K",    # K=KRX / N=NXT / U=통합
        )
    )

    response = m_t1308.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.out_block:
        logger.info(f"ex_shcode: {response.out_block.ex_shcode}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 120)
    logger.info(
        f"{'시간':>8} {'현재가':>8} {'sign':>4} {'전일대비':>9} {'등락률':>8} "
        f"{'체결강도(거래량)':>15} {'체결강도(건수)':>14} "
        f"{'거래량':>11} {'시가':>8} {'고가':>8} {'저가':>8}"
    )
    logger.info("-" * 120)

    for item in response.block:
        glyph = _SIGN_GLYPH.get(item.sign, item.sign)
        logger.info(
            f"{item.chetime:>8} {item.price:>8,} {glyph:>4} "
            f"{item.change:>+9,} {item.diff:>+7.2f}% "
            f"{item.chdegvol:>15.2f} {item.chdegcnt:>14.2f} "
            f"{item.volume:>11,} {item.open:>8,} {item.high:>8,} {item.low:>8,}"
        )


if __name__ == "__main__":
    test_req_t1308()
