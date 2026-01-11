"""
포트폴리오 백테스트 예제 실행 스크립트.

Usage:
    cd src/programgarden
    poetry run python examples/workflow_editor/03_portfolio_backtest/run.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parents[3]))

from programgarden import ProgramGarden


def run_portfolio_backtest():
    """계층적 포트폴리오 백테스트 실행."""
    from workflow import get_portfolio_workflow
    
    print("=" * 60)
    print("🏛️  계층적 포트폴리오 백테스트")
    print("=" * 60)
    
    # 워크플로우 로드
    try:
        workflow = get_portfolio_workflow()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\n👉 .env 파일에 APPKEY와 APPSECRET을 설정하세요:")
        print("   APPKEY=your_app_key")
        print("   APPSECRET=your_app_secret")
        return
    
    print(f"\n📋 워크플로우: {workflow['name']}")
    print(f"   - ID: {workflow['id']}")
    print(f"   - 노드 수: {len(workflow['nodes'])}")
    print(f"   - 엣지 수: {len(workflow['edges'])}")
    
    # 노드 카테고리별 요약
    categories = {}
    for node in workflow['nodes']:
        cat = node.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📊 노드 구성:")
    for cat, count in sorted(categories.items()):
        print(f"   - {cat}: {count}개")
    
    # 포트폴리오 계층 구조 출력
    print("\n🏗️  포트폴리오 계층 구조:")
    print("""
    ┌───────────────────────────────────────────────────────────────┐
    │                      Master Portfolio                         │
    │                    total: $100,000                            │
    │                  allocation: custom (60:40)                   │
    │                  rebalance: drift (5%)                        │
    ├───────────────────────────┬───────────────────────────────────┤
    │      Tech Portfolio (60%) │      Value Portfolio (40%)        │
    │       momentum alloc      │         equal alloc               │
    │       drift 10%           │         monthly rebal             │
    ├─────────────┬─────────────┼─────────────┬─────────────────────┤
    │  RSI Strat  │  MA Strat   │ Value Strat │ Momentum Strat      │
    │  NVDA,AAPL  │ MSFT,GOOGL  │   JNJ,PG    │       AMZN          │
    │  kelly 25%  │ equal wgt   │ fixed 10%   │     kelly 50%       │
    │  SL:5%/TP:15│ SL:3%/TS:5% │ SL:5%/TP:10%│     SL:7%/TS:10%    │
    └─────────────┴─────────────┴─────────────┴─────────────────────┘
    """)
    
    # ProgramGarden 인스턴스 생성
    pg = ProgramGarden()
    
    # 콜백 설정 (리스너 형태로 사용 가능)
    # ProgramGarden client는 run() 메서드로 실행
    
    # 워크플로우 검증
    print("\n" + "=" * 60)
    print("🔍 워크플로우 구조 검증")
    print("=" * 60)
    
    try:
        validation_result = pg.validate(workflow)
        
        print("\n" + "-" * 40)
        if validation_result.is_valid:
            print("✅ 워크플로우 구조 검증 성공!")
            print(f"\n📈 검증된 노드: {len(workflow['nodes'])}개")
            print(f"🔗 검증된 엣지: {len(workflow['edges'])}개")
        else:
            print(f"❌ 검증 실패:")
            for error in validation_result.errors:
                print(f"   - {error}")
            
    except Exception as e:
        print(f"\n❌ 검증 오류: {e}")
        import traceback
        traceback.print_exc()
    
    # dry_run 모드로 실행 (실제 API 호출 없이)
    print("\n" + "=" * 60)
    print("🚀 DRY RUN 모드로 워크플로우 실행")
    print("=" * 60)
    
    try:
        result = pg.run(
            workflow,
            context={
                "total_capital": 100000,
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "dry_run": True,
            },
            timeout=30.0,
        )
        
        print("\n" + "-" * 40)
        status = result.get("status", "unknown")
        if status == "completed":
            print("✅ 워크플로우 실행 성공!")
        elif status == "failed":
            print(f"❌ 실행 실패: {result.get('error', 'Unknown error')}")
        else:
            print(f"⏳ 상태: {status}")
            
    except Exception as e:
        print(f"\n❌ 실행 오류: {e}")
        import traceback
        traceback.print_exc()
    
    # 워크플로우 시각화 정보 출력
    print("\n" + "=" * 60)
    print("📐 워크플로우 시각화 데이터")
    print("=" * 60)
    
    # 레이어별 노드 그룹화
    layers = {
        "infra": [],
        "symbol": [],
        "data": [],
        "condition": [],
        "backtest": [],
        "risk": [],  # PortfolioNode
        "display": [],
    }
    
    for node in workflow['nodes']:
        cat = node.get('category', 'unknown')
        if cat in layers:
            layers[cat].append(node['id'])
    
    print("\n🗂️  레이어별 노드:")
    for layer, nodes in layers.items():
        if nodes:
            print(f"   {layer.upper()}: {', '.join(nodes)}")
    
    # 엣지 통계
    edge_types = {
        "infra→symbol": 0,
        "symbol→data": 0,
        "data→condition": 0,
        "condition→backtest": 0,
        "data→backtest": 0,
        "backtest→portfolio": 0,
        "portfolio→portfolio": 0,
        "portfolio→display": 0,
    }
    
    node_categories = {n['id']: n.get('category', '') for n in workflow['nodes']}
    
    for edge in workflow['edges']:
        from_node = edge['from'].split('.')[0]
        to_node = edge['to'].split('.')[0] if '.' in edge['to'] else edge['to']
        from_cat = node_categories.get(from_node, '')
        to_cat = node_categories.get(to_node, '')
        
        key = f"{from_cat}→{to_cat}"
        if key in edge_types:
            edge_types[key] += 1
    
    print("\n🔗 엣지 연결 통계:")
    for edge_type, count in edge_types.items():
        if count > 0:
            print(f"   {edge_type}: {count}개")
    
    print("\n" + "=" * 60)
    print("✨ 예제 완료")
    print("=" * 60)


def main():
    """메인 진입점."""
    run_portfolio_backtest()


if __name__ == "__main__":
    main()
