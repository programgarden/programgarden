"""HKEX 선물 종목 조회 및 OVC 테스트"""
import asyncio
import os
import sys
from pathlib import Path

# 루트 디렉토리의 .env 로드
root_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from programgarden_finance import LS, o3101, OVC

def get_hkex_symbols():
    """HKEX 종목 마스터 조회"""
    ls = LS.get_instance()
    # 해외선물 모의투자 키 사용
    appkey = os.getenv('APPKEY_FUTURE_FAKE')
    appsecret = os.getenv('APPSECRET_FUTURE_FAKE')
    print(f'appkey: {appkey[:10] if appkey else "None"}...')
    print(f'appsecret: {appsecret[:10] if appsecret else "None"}...')
    
    result = ls.login(
        appkey=appkey, 
        appsecretkey=appsecret,
        paper_trading=True
    )
    print(f'login result: {result}')

    result = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(gubun='1')
    )
    resp = result.req()

    # resp.block (리스트 형태)
    if resp and hasattr(resp, 'block') and resp.block:
        # HKEX 종목만 필터링
        hkex_items = [
            item for item in resp.block 
            if getattr(item, 'ExchCd', '') == 'HKEX'
        ]
        print(f'=== HKEX 종목 ({len(hkex_items)}개) ===')
        symbols = []
        for item in hkex_items:
            symbol = getattr(item, 'Symbol', '')
            name = getattr(item, 'SymbolNm', '')
            dlstrt = getattr(item, 'DlStrtTm', '')
            dlend = getattr(item, 'DlEndTm', '')
            # 항셍, 미니항셍, H-Share, Tech 관련만 출력
            if any(k in name for k in ['Hang Seng', 'H-Share', 'Mini', 'TECH']):
                print(f'{symbol:12} | {dlstrt}-{dlend} | {name}')
            symbols.append(symbol)
        return symbols
    else:
        print('조회 실패')
        return []


async def test_ovc(symbols):
    """OVC 실시간 테스트"""
    ls = LS.get_instance()
    
    received_data = {}
    
    def on_message(resp):
        if resp.body:
            sym = resp.body.symbol.strip() if resp.body.symbol else ''
            price = resp.body.curpr
            print(f'OVC: {sym} = {price}')
            received_data[sym] = price
        else:
            print(f'OVC 응답 (body=None): rsp_cd={resp.rsp_cd}')

    client = ls.overseas_futureoption().real()
    await client.connect()
    print('\nWebSocket 연결됨')

    ovc = client.OVC()
    
    # 미니항셍(HMH), 항셍(HSI), 미니H-Share(HMCE), 항셍테크(HTI) 우선 - 근월물(F=1월)
    priority_prefixes = ['HMHF', 'HSIF', 'HMCEF', 'HTIF', 'HCEIF']
    test_symbols = []
    for prefix in priority_prefixes:
        for s in symbols:
            if s.startswith(prefix):
                test_symbols.append(s)
                break
    
    if not test_symbols:
        test_symbols = symbols[:5]
    
    print(f'\n테스트 종목: {test_symbols[:5]}')
    
    # 8자리 패딩
    padded = [s.ljust(8) for s in test_symbols[:5]]
    print(f'패딩 적용: {padded}')
    
    ovc.add_ovc_symbols(symbols=padded)
    ovc.on_ovc_message(on_message)
    
    print('\n20초 대기 중...')
    await asyncio.sleep(20)
    
    print(f'\n수신된 데이터: {received_data}')
    await client.close()


if __name__ == "__main__":
    symbols = get_hkex_symbols()
    if symbols:
        asyncio.run(test_ovc(symbols))
