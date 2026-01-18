"""
VolumeSpike 실제 데이터 테스트

LS증권 API로 실제 과거 데이터를 가져와서 VolumeSpike 조건을 테스트합니다.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드
load_dotenv("/Users/jyj/ls_projects/programgarden/.env")

# 패키지 경로 추가
sys.path.insert(0, "/Users/jyj/ls_projects/programgarden/src/finance")
sys.path.insert(0, "/Users/jyj/ls_projects/programgarden/src/community")

from programgarden_finance import LS
from programgarden_community.plugins.strategy_conditions.volume_spike import (
    volume_spike_condition,
)


async def test_volumespike_with_real_data():
    """실제 데이터로 VolumeSpike 테스트"""
    print("=" * 70)
    print("VolumeSpike 실제 데이터 테스트")
    print("=" * 70)
    
    # LS증권 로그인
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    
    if not appkey or not appsecret:
        print("❌ .env에서 APPKEY/APPSECRET을 찾을 수 없습니다.")
        return
    
    ls = LS()
    success = ls.login(appkey=appkey, appsecretkey=appsecret)
    if not success:
        print("❌ LS증권 로그인 실패")
        return
    
    print("✅ LS증권 로그인 성공")
    
    # 테스트 종목
    symbols = [
        {"exchange": "NASDAQ", "symbol": "AAPL", "keysymbol": "82AAPL", "exchcd": "82"},
        {"exchange": "NASDAQ", "symbol": "TSLA", "keysymbol": "82TSLA", "exchcd": "82"},
        {"exchange": "NASDAQ", "symbol": "NVDA", "keysymbol": "82NVDA", "exchcd": "82"},
    ]
    
    # 과거 6개월 데이터 조회
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\n📅 조회 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"📊 조회 종목: {[s['symbol'] for s in symbols]}")
    print("-" * 70)
    
    # 각 종목의 과거 데이터 조회
    from programgarden_finance import g3204
    
    volume_data = {}
    
    for sym in symbols:
        print(f"\n[{sym['symbol']}] 과거 데이터 조회 중...")
        
        try:
            chart = ls.overseas_stock().chart().차트일주월년별조회(
                g3204.G3204InBlock(
                    sujung="Y",
                    delaygb="R",
                    keysymbol=sym["keysymbol"],
                    exchcd=sym["exchcd"],
                    symbol=sym["symbol"],
                    gubun="2",  # 일봉
                    qrycnt=180,  # 최근 180일
                    comp_yn="N",
                    sdate=start_date.strftime("%Y%m%d"),
                    edate=end_date.strftime("%Y%m%d"),
                )
            )
            
            result = await chart.req_async()
            
            if result and hasattr(result, 'block1') and result.block1:
                # 거래량 데이터 추출
                volumes = [int(item.volume) for item in result.block1 if hasattr(item, 'volume')]
                current_volume = volumes[-1] if volumes else 0
                
                volume_data[sym["symbol"]] = {
                    "volumes": volumes[:-1],  # 현재일 제외한 과거 데이터
                    "current_volume": current_volume,
                }
                
                print(f"  ✅ {len(volumes)}일 데이터 조회 완료")
                print(f"     최근 거래량: {current_volume:,}")
                print(f"     20일 평균: {sum(volumes[-21:-1]) // 20 if len(volumes) > 20 else 'N/A':,}")
            else:
                print(f"  ⚠️ 데이터 없음")
                
        except Exception as e:
            print(f"  ❌ 조회 실패: {e}")
    
    if not volume_data:
        print("\n❌ 조회된 데이터가 없습니다.")
        return
    
    # VolumeSpike 조건 테스트 (다양한 multiplier로)
    print("\n" + "=" * 70)
    print("VolumeSpike 조건 평가")
    print("=" * 70)
    
    for multiplier in [1.3, 1.5, 2.0]:
        print(f"\n📈 multiplier = {multiplier}")
        print("-" * 50)
        
        result = await volume_spike_condition(
            symbols=[s["symbol"] for s in symbols],
            volume_data=volume_data,
            fields={"period": 20, "multiplier": multiplier},
        )
        
        print(f"  passed_symbols: {result['passed_symbols']}")
        print(f"  failed_symbols: {result['failed_symbols']}")
        print(f"  result: {result['result']}")
        
        for sym, val in result['values'].items():
            status = "📈 급증" if sym in result['passed_symbols'] else "📊 정상"
            print(f"  {sym}: ratio={val['ratio']}배 {status}")
    
    # 전체 기간에서 급증일 찾기
    print("\n" + "=" * 70)
    print("📅 최근 30일 중 급증일 탐색 (multiplier=1.5)")
    print("=" * 70)
    
    for sym in symbols:
        sym_name = sym["symbol"]
        if sym_name not in volume_data:
            continue
            
        all_volumes = volume_data[sym_name]["volumes"]
        if len(all_volumes) < 21:
            continue
        
        spike_days = []
        for i in range(20, min(50, len(all_volumes))):
            avg = sum(all_volumes[i-20:i]) / 20
            current = all_volumes[i]
            ratio = current / avg if avg > 0 else 0
            
            if ratio >= 1.5:
                spike_days.append({
                    "day_ago": len(all_volumes) - i,
                    "volume": current,
                    "avg": avg,
                    "ratio": round(ratio, 2),
                })
        
        print(f"\n[{sym_name}] 급증일 {len(spike_days)}개")
        for day in spike_days[:5]:  # 최근 5개만 출력
            print(f"  {day['day_ago']}일 전: {day['volume']:,} / 평균 {int(day['avg']):,} = {day['ratio']}배")


if __name__ == "__main__":
    asyncio.run(test_volumespike_with_real_data())
