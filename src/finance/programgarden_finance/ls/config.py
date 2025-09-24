"""
LS증권에 필요한 설정 데이터들을 모아두었습니다.

이 파일은 LS증권 API와의 통신을 위한 URL 및 기타 설정들을 포함합니다.
또한, URLS 클래스는 LS증권 API의 엔드포인트를 정의합니다.
"""

from dataclasses import dataclass


@dataclass
class URLS:
    LS_URL = 'https://openapi.ls-sec.co.kr:8080'

    OAUTH_URL = f"{LS_URL}/oauth2/token"
    ACCNO_URL = f"{LS_URL}/overseas-stock/accno"
    CHART_URL = f"{LS_URL}/overseas-stock/chart"
    MARKET_URL = f"{LS_URL}/overseas-stock/market-data"
    ORDER_URL = f"{LS_URL}/overseas-stock/order"

    FO_MARKET_URL = f"{LS_URL}/overseas-futureoption/market-data"
    FO_ACCNO_URL = f"{LS_URL}/overseas-futureoption/accno"
    FO_CHART_URL = f"{LS_URL}/overseas-futureoption/chart"
    FO_ORDER_URL = f"{LS_URL}/overseas-futureoption/order"

    WSS_URL = "wss://openapi.ls-sec.co.kr:9443/websocket"
