import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1481

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1481():
    """t1481 시간외등락율상위 테스트 (장 종료 후 데이터 존재)"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 전체시장(0) 상승률(0) 전체종목(0) 전체거래량(0) 조회
    m = ls.국내주식().순위().시간외등락율상위(
        t1481.T1481InBlock(gubun1="0", gubun2="0", jongchk="0", volume="0")
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.cont_block:
        logger.info(f"연속조회키(idx): {response.cont_block.idx}")

    logger.info(f"조회 건수: {len(response.block)}건")
    if not response.block:
        logger.info("시간외 데이터 없음 (장 종료 후에만 존재)")
        return

    logger.info("=" * 100)
    logger.info(f"{'종목코드':>8} {'종목명':<14} {'현재가':>10} {'등락률':>8} {'거래량':>12}")
    logger.info("-" * 100)

    for item in response.block:
        sign_str = {
            "1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"
        }.get(item.sign, item.sign)

        logger.info(
            f"{item.shcode:>8} {item.hname:<14} {item.price:>10,} {sign_str}{item.diff:>+6.2f}% "
            f"{item.volume:>12,}"
        )


if __name__ == "__main__":
    test_req_t1481()
