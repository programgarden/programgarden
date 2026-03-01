import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CDPCQ04700

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CDPCQ04700():
    """CDPCQ04700 계좌 거래내역 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 최근 1개월 거래내역 조회
    m = ls.국내주식().계좌().계좌거래내역(
        CDPCQ04700.CDPCQ04700InBlock1(QrySrtDt="20260201", QryEndDt="20260228")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 요약
    summary = response.block2
    logger.info(f"계좌명: {summary.AcntNm}")

    logger.info(f"\n거래내역: {len(response.block3)}건")
    if not response.block3:
        logger.info("해당 기간 거래내역 없음")
        return

    logger.info("=" * 130)
    logger.info(f"{'거래일':>10} {'구분':>8} {'종목명':<14} {'수량':>8} {'단가':>10} {'거래금액':>12} {'수수료':>8} {'세금':>8}")
    logger.info("-" * 130)

    for item in response.block3:
        logger.info(
            f"{item.TrdDt:>10} {item.TpCodeNm:>8} {item.IsuNm:<14} "
            f"{item.TrdQty:>8,} {item.TrdPrc:>10,.0f} {item.TrdAmt:>12,} "
            f"{item.CmsnAmt:>8,} {item.EvrTax:>8,}"
        )


if __name__ == "__main__":
    test_req_CDPCQ04700()
