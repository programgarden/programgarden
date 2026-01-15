"""
HKEX 선물 OVC 테스트
- HSIG26: 항셍지수 선물
- HCEIG26: 항셍중국기업지수 선물
- HTIG26: 항셍테크지수 선물
"""
import asyncio
import os
from programgarden_finance import LS, OVC
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()


async def run_example():
    ls = LS.get_instance()

    # 해외선물 모의투자 키 사용
    appkey = os.getenv("APPKEY_FUTURE") or os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET_FUTURE") or os.getenv("APPSECRET")
    
    print(f"Using appkey: {appkey[:8]}..." if appkey else "No appkey found")
    
    login_result = ls.login(
        appkey=appkey,
        appsecretkey=appsecret
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    print("로그인 성공!")

    def on_message(resp: OVC.OVCRealResponse):
        print(f"=== OVC 수신 ===")
        print(f"  resp type: {type(resp)}")
        print(f"  resp: {resp}")
        if hasattr(resp, 'body') and resp.body:
            print(f"  body.symbol: {resp.body.symbol}")
            print(f"  body.curpr: {resp.body.curpr}")
            print(f"  body.totq: {resp.body.totq}")

    client = ls.overseas_futureoption().real()
    await client.connect()
    print("WebSocket 연결됨")

    ovc = client.OVC()
    
    # HKEX 선물 심볼 (8자리 패딩)
    symbols = [
        "HSIG26  ",   # 항셍지수 선물 2026년 2월물
        "HCEIG26 ",   # 항셍중국기업지수 선물
        "HTIG26  ",   # 항셍테크지수 선물
    ]
    
    print(f"구독 심볼: {symbols}")
    print(f"심볼 길이: {[len(s) for s in symbols]}")
    
    ovc.add_ovc_symbols(symbols=symbols)
    ovc.on_ovc_message(on_message)
    
    print("30초 대기 중...")
    await asyncio.sleep(30)
    
    print("테스트 종료")

if __name__ == "__main__":
    asyncio.run(run_example())
