import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1537

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1537():
    """t1537 테마종목별시세 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 테마코드로 종목별 시세 조회 (t1531/t1532에서 조회한 코드 사용)
    # 예: "0404" (폴더블폰, t1532 삼성전자 조회로 확인)
    m = ls.국내주식().업종테마().테마종목별시세(
        t1537.T1537InBlock(tmcode="0404")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 요약 정보
    summary = response.cont_block
    logger.info(f"테마명: {summary.tmname}, 상승종목: {summary.upcnt}/{summary.tmcnt}")

    logger.info(f"\n구성종목: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'종목명':<14} {'현재가':>10} {'전일대비':>10} {'등락률':>8} {'거래량':>12}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.hname:<14} {item.price:>10,} {sign_str}{item.change:>+9,} "
            f"{item.diff:>+7.2f}% {item.volume:>12,}"
        )


if __name__ == "__main__":
    test_req_t1537()
