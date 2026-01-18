"""해외선물 마스터 조회 - 홍콩거래소 종목 확인"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    from programgarden_finance import LS, o3101
    
    ls = LS()
    appkey = os.getenv('APPKEY_FUTURE_FAKE')
    appsecret = os.getenv('APPSECRET_FUTURE_FAKE')
    
    print(f'Using futures mock keys')
    
    if not ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=True):
        print('Login failed')
        return
    
    print('Login success!')
    
    # 해외선물 마스터 조회 (gubun=1: 전체)
    result = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(gubun='1')
    )
    
    resp = await result.req_async()
    
    # 응답 구조 확인: block 또는 block1
    items = getattr(resp, 'block', None) or getattr(resp, 'block1', None) or []
    
    if items:
        print(f'\n총 {len(items)}개 종목')
        print('\n=== 홍콩거래소(HKEX) 종목 ===')
        hkex_items = []
        for item in items:
            # 대문자 속성명 사용: Symbol, ExchCd
            exchcd = getattr(item, 'ExchCd', '') or getattr(item, 'exchcd', '')
            symbol = (getattr(item, 'Symbol', '') or getattr(item, 'symbol', '')).strip()
            kornam = (getattr(item, 'SymbolNm', '') or getattr(item, 'kornam', '')).strip()
            
            # 홍콩 거래소: HKEX
            if 'HKEX' in exchcd.upper():
                hkex_items.append((symbol, exchcd, kornam))
        
        for symbol, exchcd, kornam in hkex_items:
            print(f'{symbol:12} | {exchcd:6} | {kornam}')
        
        print(f'\n홍콩거래소(HKEX) 종목: {len(hkex_items)}개')
        
        # 거래시간 확인 (DlStrtTm, DlEndTm)
        print('\n=== 거래시간 확인 (홍콩 주요 종목) ===')
        for item in items:
            symbol = (getattr(item, 'Symbol', '') or getattr(item, 'symbol', '')).strip()
            exchcd = getattr(item, 'ExchCd', '') or getattr(item, 'exchcd', '')
            if 'HKEX' in exchcd and symbol in ['HSIG26', 'HCEIG26', 'HTIG26']:
                strt = getattr(item, 'DlStrtTm', '') or getattr(item, 'dlsttm', '')
                end = getattr(item, 'DlEndTm', '') or getattr(item, 'dlendtm', '')
                print(f'{symbol}: {strt} ~ {end} (한국시간)')
    else:
        print(f'No data: {resp}')

if __name__ == '__main__':
    asyncio.run(main())
