import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAQ12200

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAQ12200():
    """CSPAQ12200 현물계좌예수금 주문가능금액 총평가조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 주식잔고(0) 기본 조회
    m = ls.국내주식().계좌().현물계좌예수금주문가능금액총평가조회(
        CSPAQ12200.CSPAQ12200InBlock1(BalCreTp="0")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    item = response.block2
    logger.info("=" * 60)
    logger.info(f"계좌명: {item.AcntNm}")
    logger.info(f"지점명: {item.BrnNm}")
    logger.info(f"예수금: {item.Dps:,}")
    logger.info(f"대용금액: {item.SubstAmt:,}")
    logger.info(f"현금주문가능금액: {item.MnyOrdAbleAmt:,}")
    logger.info(f"현금출금가능금액: {item.MnyoutAbleAmt:,}")
    logger.info(f"대용주문가능금액: {item.SubstOrdAbleAmt:,}")
    logger.info(f"증거금현금: {item.MgnMny:,}")
    logger.info(f"증거금대용: {item.MgnSubst:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_req_CSPAQ12200()
