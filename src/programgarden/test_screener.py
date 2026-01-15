#!/usr/bin/env python
"""ScreenerNode 직접 테스트"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv("/Users/jyj/ls_projects/programgarden/.env")

async def test_screener():
    # 1. yfinance로 S&P500 종목 가져오기 테스트
    print("=== 1. yfinance S&P500 조회 테스트 ===")
    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        print(f"S&P500 info keys: {list(sp500.info.keys())[:10]}")
    except Exception as e:
        print(f"yfinance 기본 테스트 실패: {e}")
    
    # 2. 개별 종목 정보 조회 테스트
    print("\n=== 2. 개별 종목 정보 조회 테스트 (AAPL) ===")
    try:
        aapl = yf.Ticker("AAPL")
        info = aapl.info
        print(f"  marketCap: {info.get('marketCap', 'N/A')}")
        print(f"  averageVolume: {info.get('averageVolume', 'N/A')}")
        print(f"  sector: {info.get('sector', 'N/A')}")
        print(f"  exchange: {info.get('exchange', 'N/A')}")
    except Exception as e:
        print(f"AAPL 조회 실패: {e}")
    
    # 3. MarketUniverseNode의 SP500 리스트 확인
    print("\n=== 3. MarketUniverseNode SP500 리스트 테스트 ===")
    from programgarden.executor import MarketUniverseNodeExecutor
    from programgarden.context import ExecutionContext
    
    context = ExecutionContext(
        job_id="test-job",
        workflow_id="test-workflow",
    )
    universe_executor = MarketUniverseNodeExecutor()
    
    result = await universe_executor.execute(
        node_id="test_universe",
        node_type="MarketUniverseNode",
        config={"universe": "SP500"},
        context=context,
    )
    print(f"  SP500 종목 수: {result.get('count', 0)}")
    print(f"  처음 5개: {result.get('symbols', [])[:5]}")
    
    # 4. ScreenerNode 직접 테스트
    print("\n=== 4. ScreenerNode 직접 테스트 ===")
    from programgarden.executor import ScreenerNodeExecutor
    
    screener_executor = ScreenerNodeExecutor()
    screener_result = await screener_executor.execute(
        node_id="test_screener",
        node_type="ScreenerNode",
        config={
            "market_cap_min": 10000000000,  # 100억 달러
            "volume_min": 1000000,
            "sector": "Technology",
            "exchange": "NASDAQ",
            "max_results": 20,
        },
        context=context,
    )
    print(f"  결과 종목 수: {screener_result.get('count', 0)}")
    print(f"  에러: {screener_result.get('error', 'None')}")
    print(f"  종목: {screener_result.get('symbols', [])[:5]}")

if __name__ == "__main__":
    asyncio.run(test_screener())
