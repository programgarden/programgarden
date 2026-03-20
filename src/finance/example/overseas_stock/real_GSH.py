"""
해외주식 실시간 호가(GSH) 예제

⚠️ LS증권 API 제약 (해외주식 한정):
- 호가 가격(offerho/bidho 1~10): 정상 제공
- 개별 잔량(offerrem/bidrem 2~10): 항상 0 (미제공)
  → offerrem1/bidrem1에 총잔량이 합산되어 나옴
- 호가 건수(offerno/bidno): 항상 0 (미제공)
- 개별 호가단계별 잔량이 필요하면 REST API(g3106)를 사용하세요
- 해외선물/국내주식은 개별 단계별 데이터 정상 제공됨
"""
import asyncio
import os
from programgarden_finance import LS
import logging
logger = logging.getLogger(__name__)
from dotenv import load_dotenv

from programgarden_finance.ls.overseas_stock.real.GSH import GSHRealResponse

load_dotenv()


async def run_example():

    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    def on_message(resp: GSHRealResponse):
        print(f"Received: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    gsh = client.GSH()
    gsh.add_gsh_symbols(symbols=["81SOXL"])
    gsh.on_gsh_message(on_message)

    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
