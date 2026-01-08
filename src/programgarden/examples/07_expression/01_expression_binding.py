"""
예제 30: 표현식 바인딩 (Expression Binding)

Jinja2 스타일 {{ }} 표현식을 사용하여 노드 간 동적 값 전달

특징:
- {{ marketData.price }} - 다른 노드 출력 참조
- {{ marketData.price * 0.99 }} - 산술 연산
- {{ min(sizing.quantity, 100) }} - 내장 함수 사용
"""

EXPRESSION_BINDING = {
    "id": "30-expression-binding",
    "version": "1.0.0",
    "name": "표현식 바인딩 예제",
    "description": "동적 가격/수량 계산을 위한 표현식 사용",
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
            "provider": "ls-sec.co.kr",
            "product": "overseas_stock",
            "position": {"x": 200, "y": 200},
        },
        {
            "id": "watchlist",
            "type": "WatchlistNode",
            "category": "symbol",
            "symbols": ["AAPL", "NVDA"],
            "position": {"x": 400, "y": 200},
        },
        {
            "id": "marketData",
            "type": "RealMarketDataNode",
            "category": "realtime",
            "fields": ["price", "volume"],
            "position": {"x": 600, "y": 200},
        },
        {
            "id": "rsiCondition",
            "type": "ConditionNode",
            "category": "condition",
            "plugin": "RSI",
            "fields": {
                "period": 14,
                "threshold": 30,
                "direction": "below",
                # 표현식으로 가격 데이터 참조
                "price_data": "{{ marketData }}",
            },
            "position": {"x": 800, "y": 200},
        },
        {
            "id": "limitBuy",
            "type": "NewOrderNode",
            "category": "order",
            "plugin": "LimitOrder",
            "fields": {
                "side": "buy",
                # 표현식: 현재가의 99% (1% 할인)
                "price": "{{ marketData.price * 0.99 }}",
                # 표현식: 최대 100주로 제한
                "quantity": "{{ min(sizing.quantity, 100) }}",
            },
            "position": {"x": 1000, "y": 200},
        },
        {
            "id": "display",
            "type": "DisplayNode",
            "category": "display",
            "format": "table",
            "fields": ["symbol", "price", "quantity", "status"],
            "position": {"x": 1200, "y": 200},
        },
    ],
    "edges": [
        {"from": "start.start", "to": "broker"},
        {"from": "broker.connection", "to": "watchlist"},
        {"from": "watchlist.symbols", "to": "marketData.symbols"},
        {"from": "marketData.price", "to": "rsiCondition.price_data"},
        {"from": "rsiCondition.passed_symbols", "to": "limitBuy.symbols"},
        {"from": "limitBuy.result", "to": "display.data"},
    ],
}


if __name__ == "__main__":
    import asyncio
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

    from programgarden_core.expression import ExpressionEvaluator, ExpressionContext
    
    # 표현식 평가 테스트
    print("=== 표현식 평가 테스트 ===\n")
    
    # 컨텍스트 설정 (이전 노드 출력 시뮬레이션)
    ctx = ExpressionContext()
    ctx.set_node_output("marketData", "price", 185.50)
    ctx.set_node_output("sizing", "quantity", 150)
    
    evaluator = ExpressionEvaluator(ctx)
    
    # 테스트 케이스
    test_cases = [
        ("{{ marketData }}", "단순 참조"),
        ("{{ marketData * 0.99 }}", "가격 1% 할인"),
        ("{{ min(sizing, 100) }}", "최대 100주 제한"),
        ("{{ round(marketData * 0.99, 2) }}", "소수점 2자리"),
        ("buy", "고정값 (표현식 아님)"),
        (14, "숫자 고정값"),
    ]
    
    for expr, desc in test_cases:
        result = evaluator.evaluate(expr)
        print(f"{desc}:")
        print(f"  입력: {repr(expr)}")
        print(f"  결과: {result}")
        print()
    
    # 전체 fields 평가 테스트
    print("=== 전체 fields 평가 ===\n")
    
    fields = {
        "side": "buy",
        "price": "{{ marketData * 0.99 }}",
        "quantity": "{{ min(sizing, 100) }}",
        "limit_price": "{{ round(marketData * 0.985, 2) }}",
    }
    
    evaluated = evaluator.evaluate_fields(fields)
    print(f"입력 fields: {fields}")
    print(f"평가된 fields: {evaluated}")
