"""주식주문접수(SC0) 실시간 예제

주식 주문 접수 이벤트를 실시간으로 수신합니다.
SC0~SC4는 하나만 등록해도 5개 주문 이벤트가 모두 활성화됩니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.SC0.blocks import SC0RealResponse

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

    def on_message(resp: SC0RealResponse):
        if resp.body:
            b = resp.body
            print(f"[SC0 주문접수] 주문번호:{b.ordno} 종목:{b.shtcode}({b.hname}) "
                  f"구분:{b.ordchegb} 수량:{b.ordqty} 가격:{b.ordprice} 매매:{b.bnstp}")
        else:
            print(f"[SC0] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    sc0 = client.SC0()
    sc0.on_sc0_message(on_message)

    print("SC0 주문접수 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
