import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1702

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1702():
    """t1702 외인기관종목별동향 테스트"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 최근 1개월 순매수(0) 수량(1) 일간(0) 조회
    m = ls.국내주식().외인기관().외인기관종목별동향(
        t1702.T1702InBlock(
            shcode="005930",
            fromdt="20260201",
            todt="20260228",
            volvalgb="1",
            msmdgb="0",
            gubun="0",
        )
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(f"{'일자':>10} {'종가':>10} {'거래량':>12} {'개인':>12} {'외인계':>12} {'기관계':>12}")
    logger.info("-" * 100)

    for item in response.block:
        logger.info(
            f"{item.date:>10} {item.close:>10,} {item.volume:>12,} "
            f"{item.tjj0008:>12,} {item.tjj0018:>12,} {item.tjj0017:>12,}"
        )


if __name__ == "__main__":
    test_req_t1702()
