"""KOSDAQ 호가잔량(HA_) 실시간 예제

카카오게임즈(293490) 실시간 10단계 호가잔량 데이터를 수신합니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.HA_.blocks import HA_RealResponse

logger = logging.getLogger(__name__)
load_dotenv()


async def run_example():
    ls = LS.get_instance()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )
    if login_result is False:
        logger.error("로그인 실패")
        return

    def on_message(resp: HA_RealResponse):
        if resp.body:
            b = resp.body
            print(f"[HA_ KOSDAQ호가] {b.shcode} | 시간:{b.hotime} "
                  f"매도1:{b.offerho1}({b.offerrem1}) 매수1:{b.bidho1}({b.bidrem1}) "
                  f"총매도잔량:{b.totofferrem} 총매수잔량:{b.totbidrem}")
        else:
            print(f"[HA_] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    ha = client.HA_()
    ha.add_ha__symbols(symbols=["293490"])
    ha.on_ha__message(on_message)

    print("HA_ KOSDAQ 호가잔량 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
