import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, FOCCQ33600

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_FOCCQ33600():
    """FOCCQ33600 계좌 기간별 수익률 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 최근 1개월 일별(1) 수익률 조회
    m = ls.국내주식().계좌().계좌기간별수익률(
        FOCCQ33600.FOCCQ33600InBlock1(QrySrtDt="20260201", QryEndDt="20260228", TermTp="1")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 요약
    summary = response.block2
    logger.info("=" * 60)
    logger.info(f"계좌명: {summary.AcntNm}")
    logger.info(f"매매약정금액: {summary.BnsctrAmt:,}")
    logger.info(f"입금: {summary.MnyinAmt:,}")
    logger.info(f"출금: {summary.MnyoutAmt:,}")
    logger.info(f"투자원금평잔: {summary.InvstAvrbalPramt:,}")
    logger.info(f"투자손익: {summary.InvstPlAmt:,}")
    logger.info(f"투자수익률: {summary.InvstErnrat:.2f}%")
    logger.info("=" * 60)

    logger.info(f"\n기간별 수익률: {len(response.block3)}건")
    if not response.block3:
        logger.info("해당 기간 데이터 없음")
        return

    logger.info("=" * 100)
    logger.info(f"{'기준일':>10} {'기초평가':>14} {'기말평가':>14} {'평가손익':>14} {'기간수익률':>10}")
    logger.info("-" * 100)

    for item in response.block3:
        logger.info(
            f"{item.BaseDt:>10} {item.FdEvalAmt:>14,} {item.EotEvalAmt:>14,} "
            f"{item.EvalPnlAmt:>14,} {item.TermErnrat:>9.2f}%"
        )


if __name__ == "__main__":
    test_req_FOCCQ33600()
