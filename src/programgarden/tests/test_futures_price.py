"""해외선물 현재가 조회 (REST API) - OVC 없이 바로 조회"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    from programgarden_finance import LS
    from programgarden_finance.ls.overseas_futureoption.market.o3102 import o3102
    
    ls = LS()
    appkey = os.getenv('APPKEY_FUTURE_FAKE')
    appsecret = os.getenv('APPSECRET_FUTURE_FAKE')
    
    print('Using futures mock keys')
    
    if not ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=True):
        print('Login failed')
        return
    
    print('Login success!')
    
    # 테스트할 종목들
    symbols = ['HSIG26', 'HCEIG26', 'HTIG26']
    
    for symbol in symbols:
        # 해외선물 현재가 조회
        result = ls.overseas_futureoption().market().해외선물현재가조회(
            body=o3102.O3102InBlock(symbol=symbol.ljust(8))
        )
        
        resp = await result.req_async()
        
        if resp and hasattr(resp, 'block'):
            block = resp.block
            curpr = getattr(block, 'Curpr', '') or getattr(block, 'curpr', '')
            open_p = getattr(block, 'Open', '') or getattr(block, 'open', '')
            high = getattr(block, 'High', '') or getattr(block, 'high', '')
            low = getattr(block, 'Low', '') or getattr(block, 'low', '')
            totq = getattr(block, 'Totq', '') or getattr(block, 'totq', '')
            
            print(f'{symbol}: 현재가={curpr}, 시가={open_p}, 고가={high}, 저가={low}, 거래량={totq}')
        else:
            print(f'{symbol}: 조회 실패 - {resp}')

if __name__ == '__main__':
    asyncio.run(main())
