"""
MACD 플러그인 가상 데이터 테스트
"""

import asyncio
import random
from datetime import datetime, timedelta
from programgarden_community.plugins.strategy_conditions.macd import (
    macd_condition,
    calculate_macd,
    calculate_macd_series,
    MACD_SCHEMA,
)


def generate_mock_ohlcv_data(symbol: str, exchange: str, days: int = 100, start_price: float = 100.0):
    """가상 OHLCV 데이터 생성"""
    data = []
    price = start_price
    base_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        # 랜덤 변동 (-3% ~ +3%)
        change_pct = random.uniform(-0.03, 0.03)
        price = price * (1 + change_pct)
        
        # OHLCV 생성
        daily_high = price * random.uniform(1.0, 1.02)
        daily_low = price * random.uniform(0.98, 1.0)
        daily_open = random.uniform(daily_low, daily_high)
        daily_close = random.uniform(daily_low, daily_high)
        volume = random.randint(1000000, 5000000)
        
        date_str = (base_date + timedelta(days=i)).strftime("%Y%m%d")
        
        data.append({
            "date": date_str,
            "symbol": symbol,
            "exchange": exchange,
            "open": round(daily_open, 2),
            "high": round(daily_high, 2),
            "low": round(daily_low, 2),
            "close": round(daily_close, 2),
            "volume": volume,
        })
    
    return data


def generate_bullish_trend_data(symbol: str, exchange: str, days: int = 100, start_price: float = 100.0):
    """상승 추세 데이터 생성 (MACD 골든크로스 유도)"""
    data = []
    price = start_price
    base_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        # 전반부: 하락/횡보, 후반부: 강한 상승
        if i < days // 2:
            change_pct = random.uniform(-0.02, 0.01)  # 약간 하락 경향
        else:
            change_pct = random.uniform(0.005, 0.025)  # 상승 경향
        
        price = price * (1 + change_pct)
        
        daily_high = price * random.uniform(1.0, 1.015)
        daily_low = price * random.uniform(0.985, 1.0)
        daily_open = random.uniform(daily_low, daily_high)
        daily_close = random.uniform(daily_low, daily_high)
        volume = random.randint(1000000, 5000000)
        
        date_str = (base_date + timedelta(days=i)).strftime("%Y%m%d")
        
        data.append({
            "date": date_str,
            "symbol": symbol,
            "exchange": exchange,
            "open": round(daily_open, 2),
            "high": round(daily_high, 2),
            "low": round(daily_low, 2),
            "close": round(daily_close, 2),
            "volume": volume,
        })
    
    return data


def generate_bearish_trend_data(symbol: str, exchange: str, days: int = 100, start_price: float = 150.0):
    """하락 추세 데이터 생성 (MACD 데드크로스 유도)"""
    data = []
    price = start_price
    base_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        # 전반부: 상승, 후반부: 강한 하락
        if i < days // 2:
            change_pct = random.uniform(-0.01, 0.02)  # 약간 상승 경향
        else:
            change_pct = random.uniform(-0.025, -0.005)  # 하락 경향
        
        price = price * (1 + change_pct)
        
        daily_high = price * random.uniform(1.0, 1.015)
        daily_low = price * random.uniform(0.985, 1.0)
        daily_open = random.uniform(daily_low, daily_high)
        daily_close = random.uniform(daily_low, daily_high)
        volume = random.randint(1000000, 5000000)
        
        date_str = (base_date + timedelta(days=i)).strftime("%Y%m%d")
        
        data.append({
            "date": date_str,
            "symbol": symbol,
            "exchange": exchange,
            "open": round(daily_open, 2),
            "high": round(daily_high, 2),
            "low": round(daily_low, 2),
            "close": round(daily_close, 2),
            "volume": volume,
        })
    
    return data


async def test_macd_calculation():
    """MACD 계산 로직 테스트"""
    print("\n" + "="*60)
    print("테스트 1: MACD 기본 계산")
    print("="*60)
    
    # 간단한 가격 시리즈
    prices = [float(i) for i in range(1, 51)]  # 1~50 상승 추세
    
    result = calculate_macd(prices, fast=12, slow=26, signal=9)
    print(f"가격 시리즈: 1 → 50 (단순 상승)")
    print(f"MACD: {result['macd']}")
    print(f"Signal: {result['signal']}")
    print(f"Histogram: {result['histogram']}")
    
    assert result['macd'] > 0, "상승 추세에서 MACD는 양수여야 함"
    print("✅ 상승 추세 MACD 계산 정상")
    
    # 하락 추세
    prices_down = [float(50 - i) for i in range(50)]  # 50 → 1 하락 추세
    result_down = calculate_macd(prices_down, fast=12, slow=26, signal=9)
    print(f"\n가격 시리즈: 50 → 1 (단순 하락)")
    print(f"MACD: {result_down['macd']}")
    print(f"Signal: {result_down['signal']}")
    print(f"Histogram: {result_down['histogram']}")
    
    assert result_down['macd'] < 0, "하락 추세에서 MACD는 음수여야 함"
    print("✅ 하락 추세 MACD 계산 정상")


async def test_macd_series():
    """MACD 시계열 계산 테스트"""
    print("\n" + "="*60)
    print("테스트 2: MACD 시계열 계산")
    print("="*60)
    
    prices = [100 + i * 0.5 + random.uniform(-2, 2) for i in range(50)]
    series = calculate_macd_series(prices, fast=12, slow=26, signal_period=9)
    
    print(f"입력 데이터 수: {len(prices)}")
    print(f"MACD 시리즈 수: {len(series)}")
    
    expected_length = max(0, len(prices) - (26 + 9) + 1)
    print(f"예상 시리즈 수: {expected_length}")
    
    if series:
        print(f"\n최근 5개 MACD 값:")
        for i, val in enumerate(series[-5:]):
            print(f"  [{len(series)-5+i}] MACD={val['macd']:.4f}, Signal={val['signal']:.4f}, Hist={val['histogram']:.4f}")
    
    print("✅ MACD 시계열 계산 정상")


async def test_macd_condition_bullish():
    """Bullish Cross 조건 테스트"""
    print("\n" + "="*60)
    print("테스트 3: Bullish Cross 조건 (상승 추세)")
    print("="*60)
    
    # 상승 추세 데이터 생성
    data = generate_bullish_trend_data("AAPL", "NASDAQ", days=100)
    
    result = await macd_condition(
        data=data,
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bullish_cross",
        },
        symbols=[{"exchange": "NASDAQ", "symbol": "AAPL"}],
    )
    
    print(f"통과 종목: {result['passed_symbols']}")
    print(f"실패 종목: {result['failed_symbols']}")
    print(f"결과: {result['result']}")
    
    if result['symbol_results']:
        sr = result['symbol_results'][0]
        print(f"\nMACD 상세:")
        print(f"  MACD: {sr.get('macd')}")
        print(f"  Signal: {sr.get('signal')}")
        print(f"  Histogram: {sr.get('histogram')}")
    
    if result['values'] and result['values'][0].get('time_series'):
        ts = result['values'][0]['time_series']
        print(f"\n시계열 데이터 수: {len(ts)}")
        print("최근 3개:")
        for entry in ts[-3:]:
            print(f"  {entry['date']}: close={entry['close']}, macd={entry['macd']:.4f}, hist={entry['histogram']:.4f}")
    
    print("✅ Bullish Cross 조건 테스트 완료")


async def test_macd_condition_bearish():
    """Bearish Cross 조건 테스트"""
    print("\n" + "="*60)
    print("테스트 4: Bearish Cross 조건 (하락 추세)")
    print("="*60)
    
    # 하락 추세 데이터 생성
    data = generate_bearish_trend_data("NVDA", "NASDAQ", days=100)
    
    result = await macd_condition(
        data=data,
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bearish_cross",
        },
        symbols=[{"exchange": "NASDAQ", "symbol": "NVDA"}],
    )
    
    print(f"통과 종목: {result['passed_symbols']}")
    print(f"실패 종목: {result['failed_symbols']}")
    print(f"결과: {result['result']}")
    
    if result['symbol_results']:
        sr = result['symbol_results'][0]
        print(f"\nMACD 상세:")
        print(f"  MACD: {sr.get('macd')}")
        print(f"  Signal: {sr.get('signal')}")
        print(f"  Histogram: {sr.get('histogram')}")
    
    print("✅ Bearish Cross 조건 테스트 완료")


async def test_macd_multiple_symbols():
    """다중 종목 테스트"""
    print("\n" + "="*60)
    print("테스트 5: 다중 종목 MACD 조건")
    print("="*60)
    
    # 여러 종목 데이터 병합
    data = []
    data.extend(generate_bullish_trend_data("AAPL", "NASDAQ", days=100))
    data.extend(generate_bearish_trend_data("MSFT", "NASDAQ", days=100))
    data.extend(generate_mock_ohlcv_data("GOOGL", "NASDAQ", days=100))
    
    result = await macd_condition(
        data=data,
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bullish_cross",
        },
        symbols=[
            {"exchange": "NASDAQ", "symbol": "AAPL"},
            {"exchange": "NASDAQ", "symbol": "MSFT"},
            {"exchange": "NASDAQ", "symbol": "GOOGL"},
        ],
    )
    
    print(f"통과 종목: {result['passed_symbols']}")
    print(f"실패 종목: {result['failed_symbols']}")
    print(f"결과: {result['result']}")
    
    print("\n종목별 결과:")
    for sr in result['symbol_results']:
        status = "✅ PASS" if {"exchange": sr["exchange"], "symbol": sr["symbol"]} in result['passed_symbols'] else "❌ FAIL"
        print(f"  {sr['symbol']}: MACD={sr['macd']:.4f}, Hist={sr['histogram']:.4f} {status}")
    
    print("✅ 다중 종목 테스트 완료")


async def test_macd_insufficient_data():
    """데이터 부족 케이스 테스트"""
    print("\n" + "="*60)
    print("테스트 6: 데이터 부족 케이스")
    print("="*60)
    
    # 최소 필요: slow(26) + signal(9) = 35일
    # 30일 데이터만 제공
    data = generate_mock_ohlcv_data("TSLA", "NASDAQ", days=30)
    
    result = await macd_condition(
        data=data,
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bullish_cross",
        },
        symbols=[{"exchange": "NASDAQ", "symbol": "TSLA"}],
    )
    
    print(f"데이터 일수: 30 (최소 필요: 35)")
    print(f"통과 종목: {result['passed_symbols']}")
    print(f"실패 종목: {result['failed_symbols']}")
    
    if result['symbol_results']:
        sr = result['symbol_results'][0]
        print(f"에러: {sr.get('error', 'N/A')}")
    
    assert len(result['failed_symbols']) == 1, "데이터 부족 시 실패 처리되어야 함"
    print("✅ 데이터 부족 케이스 처리 정상")


async def test_macd_empty_data():
    """빈 데이터 테스트"""
    print("\n" + "="*60)
    print("테스트 7: 빈 데이터 케이스")
    print("="*60)
    
    result = await macd_condition(
        data=[],
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bullish_cross",
        },
        symbols=[{"exchange": "NASDAQ", "symbol": "AAPL"}],
    )
    
    print(f"통과 종목: {result['passed_symbols']}")
    print(f"실패 종목: {result['failed_symbols']}")
    print(f"결과: {result['result']}")
    
    assert result['result'] == False, "빈 데이터에서는 결과가 False여야 함"
    print("✅ 빈 데이터 케이스 처리 정상")


async def test_field_mapping():
    """커스텀 필드 매핑 테스트"""
    print("\n" + "="*60)
    print("테스트 8: 커스텀 필드 매핑")
    print("="*60)
    
    # 다른 필드명 사용하는 데이터
    data = []
    price = 100.0
    base_date = datetime.now() - timedelta(days=50)
    
    for i in range(50):
        change_pct = random.uniform(-0.02, 0.03)
        price = price * (1 + change_pct)
        
        data.append({
            "trade_date": (base_date + timedelta(days=i)).strftime("%Y%m%d"),
            "ticker": "IBM",
            "market": "NYSE",
            "close_price": round(price, 2),
            "volume": random.randint(1000000, 5000000),
        })
    
    result = await macd_condition(
        data=data,
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bullish_cross",
        },
        field_mapping={
            "close_field": "close_price",
            "date_field": "trade_date",
            "symbol_field": "ticker",
            "exchange_field": "market",
        },
    )
    
    print(f"커스텀 필드 매핑 적용:")
    print(f"  close_field: close_price")
    print(f"  date_field: trade_date")
    print(f"  symbol_field: ticker")
    print(f"  exchange_field: market")
    
    print(f"\n통과 종목: {result['passed_symbols']}")
    print(f"실패 종목: {result['failed_symbols']}")
    
    if result['symbol_results']:
        sr = result['symbol_results'][0]
        print(f"\nMACD 상세:")
        print(f"  Symbol: {sr['symbol']}")
        print(f"  Exchange: {sr['exchange']}")
        print(f"  MACD: {sr.get('macd')}")
    
    print("✅ 커스텀 필드 매핑 테스트 완료")


async def run_all_tests():
    """모든 테스트 실행"""
    print("="*60)
    print("MACD 플러그인 테스트 시작")
    print("="*60)
    print(f"플러그인: {MACD_SCHEMA.id} v{MACD_SCHEMA.version}")
    print(f"설명: {MACD_SCHEMA.description}")
    
    random.seed(42)  # 재현성을 위한 시드 고정
    
    await test_macd_calculation()
    await test_macd_series()
    await test_macd_condition_bullish()
    await test_macd_condition_bearish()
    await test_macd_multiple_symbols()
    await test_macd_insufficient_data()
    await test_macd_empty_data()
    await test_field_mapping()
    
    print("\n" + "="*60)
    print("🎉 모든 테스트 통과!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
