import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAQ22200

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAQ22200():
    """CSPAQ22200 현물계좌예수금 주문가능금액 총평가2 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 현물계좌 예수금/주문가능금액 조회 (기본: 주식잔고)
    m_cspaq22200 = ls.국내주식().계좌().현물계좌예수금주문가능금액총평가()

    response = m_cspaq22200.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block2:
        b = response.block2
        logger.info(f"=== 계좌 정보 ===")
        logger.info(f"지점명: {b.BrnNm} | 계좌명: {b.AcntNm}")

        logger.info(f"=== 예수금 ===")
        logger.info(f"예수금: {b.Dps:,}원")
        logger.info(f"D1예수금: {b.D1Dps:,}원 | D2예수금: {b.D2Dps:,}원")

        logger.info(f"=== 주문가능금액 ===")
        logger.info(f"현금주문가능: {b.MnyOrdAbleAmt:,}원")
        logger.info(f"대용주문가능: {b.SubstOrdAbleAmt:,}원")
        logger.info(f"거래소: {b.SeOrdAbleAmt:,}원 | 코스닥: {b.KdqOrdAbleAmt:,}원")
        logger.info(f"증거금100%: {b.MgnRat100pctOrdAbleAmt:,}원")
        logger.info(f"증거금50%: {b.MgnRat50ordAbleAmt:,}원")
        logger.info(f"증거금35%: {b.MgnRat35ordAbleAmt:,}원")

        logger.info(f"=== 증거금/담보 ===")
        logger.info(f"증거금현금: {b.MgnMny:,}원 | 증거금대용: {b.MgnSubst:,}원")
        logger.info(f"대용금액: {b.SubstAmt:,}원")
        logger.info(f"미수금액: {b.RcvblAmt:,}원 | 융자금액: {b.MloanAmt:,}원")

        logger.info(f"=== 정산 ===")
        logger.info(f"전일매도정산: {b.PrdaySellAdjstAmt:,}원 | 전일매수정산: {b.PrdayBuyAdjstAmt:,}원")
        logger.info(f"금일매도정산: {b.CrdaySellAdjstAmt:,}원 | 금일매수정산: {b.CrdayBuyAdjstAmt:,}원")


if __name__ == "__main__":
    test_req_CSPAQ22200()
