import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPBQ00200

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPBQ00200():
    """CSPBQ00200 현물계좌 증거금률별 주문가능수량 조회 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 매수(2) 삼성전자(A005930) 50000원 기준 주문가능수량 조회
    m = ls.국내주식().계좌().현물계좌증거금률별주문가능수량조회(
        CSPBQ00200.CSPBQ00200InBlock1(BnsTpCode="2", IsuNo="A005930", OrdPrc=50000.0)
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    item = response.block2
    if item is None:
        logger.info("주문가능수량 데이터 없음")
        return
    logger.info("=" * 60)
    logger.info(f"계좌명: {item.AcntNm}")
    logger.info(f"종목명: {item.IsuNm}")
    logger.info(f"예수금: {item.Dps:,}")
    logger.info(f"대용금액: {item.SubstAmt:,}")
    logger.info(f"현금주문가능금액: {item.MnyOrdAbleAmt:,}")
    logger.info(f"주문가능수량: {item.OrdAbleQty:,}")
    logger.info(f"주문가능금액: {item.OrdAbleAmt:,}")
    logger.info(f"증거금률100% 주문가능: {item.MgnRat100pctOrdAbleAmt:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_req_CSPBQ00200()
