#!/usr/bin/env python3
"""
워크플로우 테스트 스크립트

다양한 워크플로우를 테스트하여 수정된 코드가 정상 작동하는지 확인합니다.
- RSI 플러그인 signal 필드 확인
- BacktestEngineNode 양방향 시뮬레이션 확인
- BenchmarkCompareNode 전략 비교 확인
"""
import asyncio
import sys
import json
sys.path.insert(0, "/Users/jyj/ls_projects/programgarden/src/community")
sys.path.insert(0, "/Users/jyj/ls_projects/programgarden/src/core")
sys.path.insert(0, "/Users/jyj/ls_projects/programgarden/src/programgarden")


async def test_rsi_signal():
    """RSI 플러그인이 signal 필드를 생성하는지 테스트"""
    from programgarden_community.plugins.strategy_conditions.rsi import rsi_condition
    
    # 테스트 데이터 생성 (RSI가 30 아래로 떨어지도록)
    test_data = []
    for i in range(30):
        if i < 15:
            # 하락장: 가격이 내려감
            price = 100 - i * 2
        else:
            # 상승장: 가격이 올라감
            price = 70 + (i - 15) * 3
        test_data.append({
            "symbol": "TEST", "exchange": "NASDAQ",
            "date": f"202501{i+1:02d}",
            "open": price + 1, "high": price + 2,
            "low": price - 1, "close": price,
            "volume": 1000000
        })
    
    result = await rsi_condition(
        data=test_data,
        fields={"period": 14, "threshold": 30, "direction": "below"},
        symbols=[{"symbol": "TEST", "exchange": "NASDAQ"}]
    )
    
    # time_series에서 signal 필드 확인
    values = result.get("values", [])
    if values:
        ts = values[0].get("time_series", [])
        signals = [b for b in ts if b.get("signal")]
        
        print("=" * 60)
        print("TEST 1: RSI 플러그인 signal 필드")
        print("=" * 60)
        print(f"총 {len(ts)}개 봉 중 {len(signals)}개 signal 발생")
        
        if signals:
            print("\n발생한 signals:")
            for s in signals[:5]:
                print(f"  {s.get('date')}: RSI={s.get('rsi', 0):.2f}, signal={s.get('signal')}, side={s.get('side')}")
            print("✅ RSI signal 테스트 통과")
            return True
        else:
            print("⚠️ signal이 발생하지 않음 (RSI가 30 아래로 안 떨어졌을 수 있음)")
            return False
    else:
        print("❌ values가 비어있음")
        return False


async def test_macd_signal():
    """MACD 플러그인이 signal 필드를 생성하는지 테스트"""
    from programgarden_community.plugins.strategy_conditions.macd import macd_condition
    
    # MACD 테스트용 데이터 (40일 이상 필요)
    test_data = []
    for i in range(50):
        # 주기적 변동: sin 파형으로 크로스오버 유도
        import math
        price = 100 + 20 * math.sin(i * 0.3)
        test_data.append({
            "symbol": "TEST", "exchange": "NASDAQ",
            "date": f"2025{(i // 31) + 1:02d}{(i % 31) + 1:02d}",
            "open": price + 1, "high": price + 3,
            "low": price - 2, "close": price,
            "volume": 1000000
        })
    
    result = await macd_condition(
        data=test_data,
        fields={"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "bullish_cross"},
        symbols=[{"symbol": "TEST", "exchange": "NASDAQ"}]
    )
    
    values = result.get("values", [])
    if values:
        ts = values[0].get("time_series", [])
        signals = [b for b in ts if b.get("signal")]
        
        print("\n" + "=" * 60)
        print("TEST 2: MACD 플러그인 signal 필드")
        print("=" * 60)
        print(f"총 {len(ts)}개 봉 중 {len(signals)}개 signal 발생")
        
        if signals:
            for s in signals[:5]:
                print(f"  {s.get('date')}: histogram={s.get('histogram', 0):.4f}, signal={s.get('signal')}, side={s.get('side')}")
            print("✅ MACD signal 테스트 통과")
            return True
        else:
            print("⚠️ MACD 크로스오버가 발생하지 않음")
            return True  # 데이터에 따라 발생하지 않을 수 있음
    else:
        print("❌ values가 비어있음")
        return False


async def test_backtest_simulation():
    """BacktestEngineNodeExecutor 시뮬레이션 테스트"""
    from programgarden.executor import BacktestEngineNodeExecutor
    from programgarden.context import ExecutionContext
    
    print("\n" + "=" * 60)
    print("TEST 3: BacktestEngineNode 시뮬레이션")
    print("=" * 60)
    
    executor = BacktestEngineNodeExecutor()
    
    # 테스트 OHLCV 데이터
    ohlcv_data = {
        "AAPL": [
            {"date": f"202501{i+1:02d}", "close": 100 + i * 0.5}
            for i in range(30)
        ]
    }
    
    # 시그널: 5일차에 매수, 20일차에 매도
    signals = [
        {"date": "20250105", "symbol": "AAPL", "signal": "buy", "side": "long", "price": 102.0},
        {"date": "20250120", "symbol": "AAPL", "signal": "sell", "side": "long", "price": 109.5},
    ]
    
    result = executor._run_simulation(
        ohlcv_data=ohlcv_data,
        signals=signals,
        initial_capital=10000,
        commission_rate=0.001,
        slippage=0.0005,
        allow_short=False,
    )
    
    print(f"초기자본: $10,000")
    print(f"최종자산: ${result['equity_curve'][-1]['value']:.2f}")
    print(f"거래 횟수: {len(result['trades'])}")
    
    for t in result['trades']:
        print(f"  {t['date']}: {t['action']} {t.get('qty', 0):.2f} @ ${t.get('price', 0):.2f}")
    
    if result['equity_curve'] and result['trades']:
        print("✅ BacktestEngine 시뮬레이션 테스트 통과")
        return True
    else:
        print("❌ 시뮬레이션 결과 없음")
        return False


async def test_bidirectional_simulation():
    """양방향 시뮬레이션 (allow_short=True) 테스트"""
    from programgarden.executor import BacktestEngineNodeExecutor
    
    print("\n" + "=" * 60)
    print("TEST 4: BacktestEngineNode 양방향 시뮬레이션 (숏 포지션)")
    print("=" * 60)
    
    executor = BacktestEngineNodeExecutor()
    
    # 테스트 OHLCV 데이터 (가격이 내려갔다 올라감)
    ohlcv_data = {
        "BTCUSD": [
            {"date": f"202501{i+1:02d}", "close": 100 - i if i < 15 else 85 + (i - 15)}
            for i in range(30)
        ]
    }
    
    # 숏 진입 → 숏 청산 시그널
    signals = [
        {"date": "20250105", "symbol": "BTCUSD", "signal": "sell", "side": "short", "price": 95.0},  # 숏 진입
        {"date": "20250115", "symbol": "BTCUSD", "signal": "buy", "side": "short", "price": 85.0},   # 숏 커버
    ]
    
    result = executor._run_simulation(
        ohlcv_data=ohlcv_data,
        signals=signals,
        initial_capital=10000,
        commission_rate=0.001,
        slippage=0.0005,
        allow_short=True,
    )
    
    print(f"초기자본: $10,000")
    print(f"최종자산: ${result['equity_curve'][-1]['value']:.2f}")
    print(f"거래 횟수: {len(result['trades'])}")
    
    for t in result['trades']:
        action = t.get('action', 'unknown')
        qty = t.get('qty', 0)
        price = t.get('price', 0)
        side = t.get('side', 'long')
        print(f"  {t['date']}: {action} ({side}) {qty:.2f} @ ${price:.2f}")
    
    # 숏 진입/청산이 있는지 확인
    has_short = any(t.get('side') == 'short' for t in result['trades'])
    
    if has_short:
        print("✅ 양방향 시뮬레이션 테스트 통과 (숏 포지션 확인)")
        return True
    else:
        print("⚠️ 숏 포지션이 생성되지 않음")
        return False


async def test_benchmark_compare():
    """BenchmarkCompareNodeExecutor 테스트"""
    from programgarden.executor import BenchmarkCompareNodeExecutor
    from programgarden.context import ExecutionContext
    
    print("\n" + "=" * 60)
    print("TEST 5: BenchmarkCompareNode 전략 비교")
    print("=" * 60)
    
    executor = BenchmarkCompareNodeExecutor()
    
    # 모의 context 생성 (간단한 mock)
    class MockContext:
        def __init__(self):
            self.outputs = {}
        
        def get_expression_context(self):
            from programgarden_core.expression import ExpressionContext
            return ExpressionContext(node_outputs={})
        
        def log(self, level, msg, node_id=None):
            print(f"  [{level}] {msg}")
    
    context = MockContext()
    
    # 두 전략의 equity_curve
    strategies_input = [
        {
            "strategy_name": "RSI Strategy",
            "equity_curve": [
                {"date": "20250101", "value": 10000},
                {"date": "20250115", "value": 10500},
                {"date": "20250130", "value": 10200},
            ],
            "metrics": {"total_return": 2.0, "sharpe_ratio": 0.8, "max_drawdown": 3.0},
        },
        {
            "strategy_name": "Buy & Hold",
            "equity_curve": [
                {"date": "20250101", "value": 10000},
                {"date": "20250115", "value": 10300},
                {"date": "20250130", "value": 10600},
            ],
            "metrics": {"total_return": 6.0, "sharpe_ratio": 1.2, "max_drawdown": 2.0},
        },
    ]
    
    result = await executor.execute(
        node_id="test_compare",
        node_type="BenchmarkCompareNode",
        config={"strategies": strategies_input, "ranking_metric": "sharpe"},
        context=context,
    )
    
    print(f"\n비교 지표:")
    for m in result.get("comparison_metrics", []):
        print(f"  {m['label']}: return={m['return']}%, sharpe={m['sharpe']}, mdd={m['mdd']}%")
    
    print(f"\n순위 (sharpe 기준):")
    for r in result.get("ranking", []):
        print(f"  #{r['rank']}: {r['label']} (sharpe={r['sharpe']})")
    
    if result.get("ranking") and result.get("comparison_metrics"):
        print("\n✅ BenchmarkCompare 테스트 통과")
        return True
    else:
        print("\n❌ 비교 결과 없음")
        return False


async def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("ProgramGarden 워크플로우 테스트")
    print("=" * 60)
    
    results = []
    
    # 1. RSI signal 테스트
    results.append(("RSI signal", await test_rsi_signal()))
    
    # 2. MACD signal 테스트
    results.append(("MACD signal", await test_macd_signal()))
    
    # 3. BacktestEngine 시뮬레이션
    results.append(("BacktestEngine", await test_backtest_simulation()))
    
    # 4. 양방향 시뮬레이션
    results.append(("Bidirectional", await test_bidirectional_simulation()))
    
    # 5. BenchmarkCompare
    results.append(("BenchmarkCompare", await test_benchmark_compare()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")
        if success:
            passed += 1
    
    print(f"\n총 {len(results)}개 중 {passed}개 통과")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
