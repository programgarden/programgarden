"""KOSPI 체결(S3_) 실시간 예제

삼성전자(005930) 실시간 체결 데이터를 수신합니다.
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.S3_.blocks import S3_RealResponse

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

    def on_message(resp: S3_RealResponse):
        if resp.body:
            b = resp.body
            print(f"[S3_ KOSPI체결] {b.shcode} | 현재가:{b.price} 전일대비:{b.sign}{b.change} "
                  f"등락률:{b.drate}% 거래량:{b.cvolume} 시간:{b.chetime}")
        else:
            print(f"[S3_] rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}")

    client = ls.korea_stock().real()
    await client.connect()

    s3 = client.S3_()
    s3.add_s3__symbols(symbols=["005930"])
    s3.on_s3__message(on_message)

    print("S3_ KOSPI 체결 실시간 수신 대기 중... (Ctrl+C로 종료)")
    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_example())
