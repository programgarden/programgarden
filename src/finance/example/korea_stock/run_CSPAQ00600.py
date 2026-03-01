import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAQ00600

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAQ00600():
    """CSPAQ00600 계좌별신용한도조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 신용한도 조회 (삼성전자 A005930 기준)
    m = ls.국내주식().계좌().계좌별신용한도조회(
        CSPAQ00600.CSPAQ00600InBlock1(IsuNo="A005930", OrdPrc=50000.0)
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    item = response.block2
    if item is None:
        logger.info("신용한도 데이터 없음 (신용계좌가 아닌 경우 조회 불가)")
        return
    logger.info("=" * 60)
    logger.info(f"계좌명: {item.AcntNm}")
    logger.info(f"종목명: {item.IsuNm}")
    logger.info(f"신용융자한도: {item.SloanLmtAmt:,}")
    logger.info(f"신용융자합계: {item.SloanAmtSum:,}")
    logger.info(f"주문가능금액: {item.OrdAbleAmt:,}")
    logger.info(f"주문가능수량: {item.OrdAbleQty:,}")
    logger.info(f"예탁자산합계: {item.DpsastSum:,}")
    logger.info(f"담보유지비율: {item.PldgMaintRat:.2f}%")
    logger.info(f"증거금률: {item.MgnRat:.2f}%")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_req_CSPAQ00600()
