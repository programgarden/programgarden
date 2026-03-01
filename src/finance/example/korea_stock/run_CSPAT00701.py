import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, CSPAT00701

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_CSPAT00701():
    """CSPAT00701 현물정정주문 테스트 (존재하지 않는 주문번호로 안전 테스트)"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 존재하지 않는 주문번호로 정정 시도 → 오류 응답 확인 (안전 테스트)
    m_modify = ls.국내주식().주문().현물정정주문(
        CSPAT00701.CSPAT00701InBlock1(
            OrgOrdNo=999999,        # 존재하지 않는 주문번호
            IsuNo="005930",         # 삼성전자
            OrdQty=1,
            OrdprcPtnCode="00",     # 지정가
            OrdCndiTpCode="0",
            OrdPrc=100,
        )
    )

    response = m_modify.req()

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")

    if response.block1:
        b1 = response.block1
        logger.info(f"=== 정정 입력 확인 ===")
        logger.info(f"원주문번호: {b1.OrgOrdNo} | 종목: {b1.IsuNo}")
        logger.info(f"수량: {b1.OrdQty} | 가격: {b1.OrdPrc}")

    if response.block2:
        b2 = response.block2
        logger.info(f"=== 정정 결과 ===")
        logger.info(f"주문번호: {b2.OrdNo} | 모주문번호: {b2.PrntOrdNo}")
        logger.info(f"주문시각: {b2.OrdTime}")
        logger.info(f"계좌명: {b2.AcntNm} | 종목명: {b2.IsuNm}")


if __name__ == "__main__":
    test_req_CSPAT00701()
