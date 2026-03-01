import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAT00601

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAT00601():
    """CSPAT00601 현물주문 테스트 (지정가 매수 → 체결 안 되는 낮은 가격)"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 저가 종목 지정가 매수 (체결 안 되는 낮은 가격으로 테스트)
    # 예수금 3만원 이내로 테스트
    m_order = ls.국내주식().주문().현물주문(
        CSPAT00601.CSPAT00601InBlock1(
            IsuNo="005930",         # 삼성전자
            OrdQty=1,               # 1주
            OrdPrc=100,             # 100원 (하한가 미달로 주문 거부 예상 → 안전 테스트)
            BnsTpCode="2",          # 매수
            OrdprcPtnCode="00",     # 지정가
            MgntrnCode="000",       # 보통
            LoanDt="",
            OrdCndiTpCode="0",      # 조건없음
        )
    )

    response = m_order.req()

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        return

    if response.block1:
        b1 = response.block1
        bns = {"1": "매도", "2": "매수"}.get(b1.BnsTpCode, b1.BnsTpCode)
        logger.info(f"=== 주문 입력 확인 ===")
        logger.info(f"종목: {b1.IsuNo} | {bns} | 수량: {b1.OrdQty} | 가격: {b1.OrdPrc}")
        logger.info(f"호가유형: {b1.OrdprcPtnCode} | 신용: {b1.MgntrnCode}")

    if response.block2:
        b2 = response.block2
        logger.info(f"=== 주문 결과 ===")
        logger.info(f"주문번호: {b2.OrdNo}")
        logger.info(f"주문시각: {b2.OrdTime}")
        logger.info(f"주문금액: {b2.OrdAmt:,}원")
        logger.info(f"계좌명: {b2.AcntNm} | 종목명: {b2.IsuNm}")


if __name__ == "__main__":
    test_req_CSPAT00601()
