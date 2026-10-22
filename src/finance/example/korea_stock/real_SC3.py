"""주식주문취소(SC3) 실시간 예제

주식 주문 취소 확인 이벤트를 실시간으로 수신합니다.
SC0~SC4는 하나만 등록해도 5개 주문 이벤트가 모두 활성화됩니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.SC3.blocks import SC3RealResponse

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

    def on_message(resp: SC3RealResponse):
        if resp.body:
            b = resp.body
            print(f"[SC3 주문취소] 종목:{b.shtnIsuno}({b.Isunm}) "
                  f"주문유형:{b.ordxctptncode} 매매구분:{b.bnstp}")
        else:
            print(f"[SC3] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    sc3 = client.SC3()
    sc3.on_sc3_message(on_message)

    print("SC3 주문취소 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
