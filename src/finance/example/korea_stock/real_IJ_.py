"""업종지수(IJ_) 실시간 예제

KOSPI 업종지수(001)의 실시간 데이터를 수신합니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.IJ_.blocks import IJ_RealResponse

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

    def on_message(resp: IJ_RealResponse):
        if resp.body:
            b = resp.body
            print(f"[IJ_ 업종지수] {b.upcode} | 지수:{b.jisu} 부호:{b.sign} 전일대비:{b.change} "
                  f"등락률:{b.drate}% 거래량:{b.volume} 시간:{b.time}")
        else:
            print(f"[IJ_] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    ij = client.IJ_()
    ij.add_ij__symbols(symbols=["001"])
    ij.on_ij__message(on_message)

    print("IJ_ 업종지수 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
