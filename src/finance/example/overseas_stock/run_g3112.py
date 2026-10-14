import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3112
import asyncio

logger = logging.getLogger(__name__)

load_dotenv()


async def test_req_g3112():
    """g3112 해외주식 시세순위 조회 (미국 전체, 전일대비상승률)"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 요청 값은 LS 가이드 g3112 기본입력 그대로:
    # delaygb R, natcode US(미국), exgubun 1(전체), rankgubun 0(전일대비상승률)
    m_g3112 = ls.overseas_stock().시세().시세순위(
        g3112.G3112InBlock(
            delaygb="R",
            natcode="US",
            exgubun="1",
            rankgubun="0",
            cts_value="",
        )
    )

    response = await m_g3112.req_async()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
    if response.block:
        logger.info(f"연속구분(cts_value): {response.block.cts_value!r}, 레코드카운트: {response.block.rec_count!r}")

    for rank, item in enumerate(response.block1, 1):
        logger.info(
            f"{rank:>3} {item.keysymbol:<10} {item.symbol:<8} {item.korname:<16} "
            f"현재가 {item.price} 등락률 {item.rate}% 거래량 {item.volume}"
        )


if __name__ == "__main__":
    asyncio.run(test_req_g3112())
