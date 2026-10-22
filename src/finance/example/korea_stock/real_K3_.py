"""KOSDAQ 체결(K3_) 실시간 예제

카카오게임즈(293490) 실시간 체결 데이터를 수신합니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.K3_.blocks import K3_RealResponse

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

    def on_message(resp: K3_RealResponse):
        if resp.body:
            b = resp.body
            print(f"[K3_ KOSDAQ체결] {b.shcode} | 현재가:{b.price} 전일대비:{b.sign}{b.change} "
                  f"등락률:{b.drate}% 거래량:{b.cvolume} 시간:{b.chetime}")
        else:
            print(f"[K3_] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    k3 = client.K3_()
    k3.add_k3__symbols(symbols=["293490"])
    k3.on_k3__message(on_message)

    print("K3_ KOSDAQ 체결 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
