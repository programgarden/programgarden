"""
예제 33: Supabase PostgreSQL 연결

PostgresNode를 사용하여 Supabase에 트레일링스탑 상태를 저장하는 예제.
메모리에서 최고가를 실시간 추적하고, 주기적으로 Supabase에 동기화합니다.

사전 준비:
1. Supabase 프로젝트 생성 (https://supabase.com)
2. 테이블 생성:
   CREATE TABLE trailing_stop_state (
       symbol VARCHAR(20) PRIMARY KEY,
       peak_price DECIMAL(20, 4),
       peak_pnl_rate DECIMAL(10, 4),
       entry_price DECIMAL(20, 4),
       updated_at TIMESTAMP DEFAULT NOW()
   );
3. .env 파일에 Supabase 연결 정보 설정 (examples/.env)
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수에서 Supabase 연결 정보 읽기
SUPABASE_HOST = os.getenv("SUPABASE_HOST", "")
SUPABASE_PORT = os.getenv("SUPABASE_PORT", "5432")
SUPABASE_DATABASE = os.getenv("SUPABASE_DATABASE", "postgres")
SUPABASE_USERNAME = os.getenv("SUPABASE_USERNAME", "postgres")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")

SUPABASE_POSTGRES = {
    "id": "33-supabase-postgres",
    "version": "1.0.0",
    "name": "Supabase PostgreSQL 연결 예제",
    "description": "PostgresNode로 Supabase에 트레일링스탑 상태 저장",
    "nodes": [
        {
            "id": "start",
            "type": "StartNode",
            "category": "infra",
            "position": {"x": 0, "y": 200},
        },
        {
            "id": "broker",
            "type": "BrokerNode",
            "category": "infra",
            "company": "ls",
            "product": "overseas_stock",
            "paper_trading": True,
            "position": {"x": 200, "y": 200},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "NVDA", "TSLA"],
            "position": {"x": 400, "y": 100},
        },
        {
            "id": "realMarket",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume", "bid", "ask"],
            "position": {"x": 600, "y": 100},
        },
        {
            "id": "account",
            "type": "RealAccountNode",
            "category": "realtime",
            "fields": ["positions", "balance"],
            "position": {"x": 600, "y": 300},
        },
        # Supabase PostgreSQL 저장 노드 (트레일링스탑 상태)
        {
            "id": "supabase",
            "type": "PostgresNode",
            "category": "data",
            "connection": {
                "host": SUPABASE_HOST,
                "port": SUPABASE_PORT,
                "database": SUPABASE_DATABASE,
                "username": SUPABASE_USERNAME,
                "password": SUPABASE_PASSWORD,
            },
            "table": "trailing_stop_state",
            "schema_name": "public",
            "key_fields": ["symbol"],
            "save_fields": ["symbol", "peak_price", "peak_pnl_rate", "entry_price", "updated_at"],
            # 핵심: 최고가는 max 집계 → 메모리 캐시에서 실시간 추적, DB는 max만 저장
            "aggregations": {
                "peak_price": "max",
                "peak_pnl_rate": "max",
            },
            # 동기화 설정: 1초마다 또는 10번 변경 시 DB 동기화
            "sync_interval_ms": 1000,
            "sync_on_change_count": 10,
            # Supabase는 SSL 필수
            "ssl_enabled": True,
            "connection_timeout": 30,
            "position": {"x": 800, "y": 200},
        },
        # 트레일링스탑 조건 체크
        {
            "id": "trailingStop",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "TrailingStop",
            "fields": {
                "trail_percent": 5.0,  # 최고점 대비 5% 하락 시 매도
            },
            "position": {"x": 1000, "y": 100},
        },
        # 트레일링스탑 발동 시 시장가 매도
        {
            "id": "sellOrder",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "MarketOrder",
            "fields": {
                "side": "sell",
                "quantity_type": "all",  # 전량 매도
            },
            "position": {"x": 1200, "y": 100},
        },
        # 알림
        {
            "id": "alert",
            "type": "AlertNode",
            "category": "event",
            "channel": "telegram",
            "template": "🔔 트레일링스탑 발동: {{ symbol }} - 최고가: {{ peak_price }}, 현재가: {{ current_price }}",
            "position": {"x": 1200, "y": 300},
        },
        # 결과 표시
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "peak_price", "current_price", "pnl_rate", "status"],
            "position": {"x": 1400, "y": 200},
        },
    ],
    "edges": [
        # 기본 흐름
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "watchlist"},
        {"from": "broker.connection", "to": "account.broker"},
        {"from": "watchlist.symbols", "to": "realMarket.symbols"},
        
        # 실시간 데이터 → Supabase 저장
        {"from": "realMarket.price", "to": "supabase.data"},
        {"from": "account.positions", "to": "supabase.data"},
        
        # Supabase에서 복원된 peak_price → 트레일링스탑 조건
        {"from": "supabase.loaded", "to": "trailingStop.state"},
        {"from": "realMarket.price", "to": "trailingStop.price_data"},
        
        # 조건 통과 → 매도 주문
        {"from": "trailingStop.passed_symbols", "to": "sellOrder.trigger"},
        {"from": "trailingStop.passed_symbols", "to": "alert.trigger"},
        
        # 결과 표시
        {"from": "sellOrder.success", "to": "display.data"},
        {"from": "supabase.saved", "to": "display.data"},
    ],
}


# .env 파일 예시 (examples/.env에 생성)
ENV_EXAMPLE = """
# Supabase PostgreSQL 연결 정보
SUPABASE_HOST=db.xxxxxxxxxxxx.supabase.co
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USERNAME=postgres
SUPABASE_PASSWORD=your-supabase-password
"""


def test_supabase_connection():
    """Supabase 연결 테스트 및 데이터 저장/조회"""
    import psycopg2
    from datetime import datetime
    
    print("\n=== Supabase 연결 테스트 ===")
    
    try:
        # 연결
        conn = psycopg2.connect(
            host=SUPABASE_HOST,
            port=SUPABASE_PORT,
            database=SUPABASE_DATABASE,
            user=SUPABASE_USERNAME,
            password=SUPABASE_PASSWORD,
            sslmode="require",
        )
        print("✅ 연결 성공!")
        
        cursor = conn.cursor()
        
        # 테이블 존재 확인 및 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trailing_stop_state (
                symbol VARCHAR(20) PRIMARY KEY,
                peak_price DECIMAL(20, 4),
                peak_pnl_rate DECIMAL(10, 4),
                entry_price DECIMAL(20, 4),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        print("✅ 테이블 준비 완료!")
        
        # 테스트 데이터 삽입 (UPSERT)
        test_data = [
            ("AAPL", 195.50, 5.25, 185.70),
            ("NVDA", 875.30, 12.50, 778.04),
            ("TSLA", 248.90, -2.30, 254.76),
        ]
        
        for symbol, peak_price, peak_pnl_rate, entry_price in test_data:
            cursor.execute("""
                INSERT INTO trailing_stop_state (symbol, peak_price, peak_pnl_rate, entry_price, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (symbol) 
                DO UPDATE SET 
                    peak_price = GREATEST(trailing_stop_state.peak_price, EXCLUDED.peak_price),
                    peak_pnl_rate = GREATEST(trailing_stop_state.peak_pnl_rate, EXCLUDED.peak_pnl_rate),
                    entry_price = EXCLUDED.entry_price,
                    updated_at = EXCLUDED.updated_at
            """, (symbol, peak_price, peak_pnl_rate, entry_price, datetime.now()))
        
        conn.commit()
        print("✅ 테스트 데이터 저장 완료!")
        
        # 데이터 조회
        cursor.execute("SELECT * FROM trailing_stop_state ORDER BY symbol")
        rows = cursor.fetchall()
        
        print("\n=== 저장된 데이터 ===")
        print(f"{'Symbol':<10} {'Peak Price':>12} {'Peak PnL %':>12} {'Entry Price':>12} {'Updated At'}")
        print("-" * 70)
        for row in rows:
            symbol, peak_price, peak_pnl_rate, entry_price, updated_at = row
            print(f"{symbol:<10} {float(peak_price):>12.2f} {float(peak_pnl_rate):>12.2f}% {float(entry_price):>12.2f} {updated_at}")
        
        cursor.close()
        conn.close()
        print("\n✅ Supabase 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden import ProgramGarden

    # 환경변수 확인
    if not SUPABASE_HOST or not SUPABASE_PASSWORD:
        print("⚠️  Supabase 연결 정보가 설정되지 않았습니다.")
        print("   examples/.env 파일을 생성하고 연결 정보를 입력하세요.")
        print(ENV_EXAMPLE)
        sys.exit(1)

    pg = ProgramGarden()

    # DSL 검증
    result = pg.validate(SUPABASE_POSTGRES)
    print(f"Valid: {result.is_valid}")
    if result.errors:
        print(f"Errors: {result.errors}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")

    # 노드 정보 출력
    print("\n=== 노드 구성 ===")
    for node in SUPABASE_POSTGRES["nodes"]:
        print(f"  - {node['id']}: {node['type']} ({node['category']})")

    # Supabase 연결 정보 확인 (마스킹)
    supabase_node = next(n for n in SUPABASE_POSTGRES["nodes"] if n["id"] == "supabase")
    print("\n=== Supabase 연결 설정 ===")
    print(f"  Host: {SUPABASE_HOST}")
    print(f"  Database: {SUPABASE_DATABASE}")
    print(f"  Table: {supabase_node['table']}")
    print(f"  Key Fields: {supabase_node['key_fields']}")
    print(f"  Aggregations: {supabase_node['aggregations']}")
    print(f"  SSL: {supabase_node['ssl_enabled']}")
    
    # 실제 Supabase 연결 테스트
    test_supabase_connection()

    # 실제 실행 (secrets 설정 필요)
    # if result.is_valid:
    #     job = pg.run(SUPABASE_POSTGRES)
    #     print(f"Job: {job}")
