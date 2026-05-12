"""t1410 (초저유동성조회) reference run script.

LS does NOT formally declare a ``T1410OutBlock1.sign`` enum mapping in
the t1410 field specification table. The LS official example response
shipped with the t1410 spec carries sign='3' on an unchanged row
(change=0 / diff='000.00') and sign='5' on a down row (diff='-00.88')
— consistent with the 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락
convention published by sibling TRs (t1308, t1422, t1427, t1449).
Values '1', '2', '4' have not been observed in the available t1410
example response. To keep this script safe against any unobserved
sign value, we print ``sign`` as the raw single-character code
returned by LS, without glyph translation.

Other field semantics LS does NOT declare (consume as returned by LS
without unit annotations):
    - Currency unit of price / change.
    - Sign convention of ``change``.
    - Window scope of ``volume`` (intraday vs multi-day cumulative).
    - Row ordering of T1410OutBlock1 (the example response mixes price
      descending with volume ascending — no single declared sort key).
    - Structure of the ``cts_shcode`` cursor.
"""

import logging
import os

from dotenv import load_dotenv

from programgarden_finance import LS, t1410

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1410():
    """t1410 초저유동성조회 테스트 (단건)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 전체 시장(gubun="0") 첫 페이지 조회. LS official example 와 동일.
    m_t1410 = ls.국내주식().시세().초저유동성조회(
        t1410.T1410InBlock(
            gubun="0",        # 0=전체 / 1=코스피 / 2=코스닥
            cts_shcode="",    # 첫 조회시 빈 문자열, 다음 조회시 이전 cts_shcode
        )
    )

    response = m_t1410.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        # cts_shcode 는 LS-defined opaque token. Empty when no further rows.
        logger.info(f"연속조회 cts_shcode (repr): {response.cont_block.cts_shcode!r}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(
        f"{'종목코드':>8} {'한글명':>20} {'현재가':>10} {'sign':>4} "
        f"{'전일대비':>10} {'등락률':>9} {'누적거래량':>14}"
    )
    logger.info("-" * 100)

    for item in response.block:
        # sign 은 LS 가 반환한 raw 값 그대로 (glyph 변환 금지 — Option C 정책,
        # '1'/'2'/'4' 미관찰 안전성 우선).
        logger.info(
            f"{item.shcode:>8} {item.hname:>20} {item.price:>10,} {item.sign:>4} "
            f"{item.change:>+10,} {item.diff:>+7.2f}% {item.volume:>14,}"
        )


def test_occurs_req_t1410():
    """t1410 초저유동성조회 연속조회 테스트 (cts_shcode cursor 기반)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m_t1410 = ls.국내주식().시세().초저유동성조회(
        t1410.T1410InBlock(
            gubun="0",
            cts_shcode="",
        )
    )

    responses = m_t1410.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)}, 총 종목 수: {total}건")


if __name__ == "__main__":
    test_req_t1410()
