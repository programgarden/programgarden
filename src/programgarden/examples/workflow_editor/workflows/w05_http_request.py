"""
HTTPRequestNode 테스트 워크플로우

외부 REST API를 호출하고 응답을 처리하는 예제:
- Public API 호출
- POST 요청

Headers는 UI에서 + 버튼으로 추가합니다 (JSON에는 노출되지 않음).
"""


def get_workflow():
    """Build HTTP request test workflow."""
    return {
        "id": "http-request-test",
        "version": "1.0.0",
        "name": "HTTPRequestNode 테스트",
        "description": "외부 REST API 호출 및 응답 처리 테스트",
        "tags": ["http", "api", "external"],
        
        "nodes": [
            # =====================================================================
            # INFRA Layer
            # =====================================================================
            {
                "id": "start",
                "type": "StartNode",
                "category": "infra",
                "position": {"x": 50, "y": 200},
            },
            
            # =====================================================================
            # DATA Layer - Public API (GET)
            # =====================================================================
            {
                "id": "public_api",
                "type": "HTTPRequestNode",
                "category": "data",
                "position": {"x": 250, "y": 100},
                
                "method": "GET",
                "url": "https://api.coingecko.com/api/v3/simple/price",
                "query_params": {
                    "ids": "bitcoin,ethereum",
                    "vs_currencies": "usd"
                },
            },
            
            # =====================================================================
            # DATA Layer - API Key를 Query로 전달
            # =====================================================================
            {
                "id": "stock_api",
                "type": "HTTPRequestNode",
                "category": "data",
                "position": {"x": 250, "y": 300},
                
                "method": "GET",
                "url": "https://www.alphavantage.co/query",
                "query_params": {
                    "function": "GLOBAL_QUOTE",
                    "symbol": "AAPL",
                    "apikey": "{{ env.ALPHA_VANTAGE_KEY }}"
                },
            },
            
            # =====================================================================
            # DATA Layer - POST 요청
            # =====================================================================
            {
                "id": "post_api",
                "type": "HTTPRequestNode",
                "category": "data",
                "position": {"x": 500, "y": 200},
                
                "method": "POST",
                "url": "https://webhook.example.com/notify",
                "body": {
                    "event": "price_alert",
                    "price": "{{ nodes.public_api.response.bitcoin.usd }}",
                    "message": "Bitcoin price updated"
                },
                # Headers는 UI에서 추가:
                # - Content-Type: application/json
                # - Authorization: Bearer xxx
            },
            
            # =====================================================================
            # DISPLAY Layer - 결과 표시
            # =====================================================================
            {
                "id": "display_result",
                "type": "DisplayNode",
                "category": "display",
                "position": {"x": 750, "y": 200},
                
                "chart_type": "table",
                "title": "API 응답 결과",
                "data": "{{ nodes.public_api.response }}",
            },
        ],
        
        "edges": [
            {"from": "start", "to": "public_api"},
            {"from": "start", "to": "stock_api"},
            {"from": "public_api", "to": "post_api"},
            {"from": "post_api", "to": "display_result"},
        ],
    }
