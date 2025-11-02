"""LS Securities configuration endpoints for ProgramGarden.

EN:
    Collect base URLs and websocket endpoints required for interacting with the
    LS Securities OpenAPI. The ``URLS`` dataclass exposes helpers for both live
    and paper trading environments.

KO:
    LS증권 OpenAPI 연동에 필요한 기본 URL과 웹소켓 엔드포인트를 모았습니다.
    ``URLS`` 데이터클래스는 실거래 및 모의투자 환경 모두에서 사용할 수 있는
    헬퍼를 제공합니다.
"""

from dataclasses import dataclass


@dataclass
class URLS:
    """Collection of API endpoints for LS Securities OpenAPI.

    EN:
        Centralize HTTP and WebSocket URLs so other modules can reference a
        single source of truth. Adjust ``LS_URL`` if the OpenAPI gateway
        changes.

    KO:
        HTTP 및 웹소켓 URL을 집중 관리하여 다른 모듈이 일관된 값을 참조하도록
        지원합니다. OpenAPI 게이트웨이가 변경되면 ``LS_URL`` 만 수정하면 됩니다.
    """
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
    WSS_URL_FAKE = "wss://openapi.ls-sec.co.kr:29443/websocket"

    @classmethod
    def get_wss_url(cls, paper_trading: bool = False) -> str:
        """Return the WebSocket endpoint for the desired trading mode.

        EN:
            Select the paper trading websocket when ``paper_trading`` is ``True``;
            otherwise use the production endpoint.

        KO:
            ``paper_trading`` 이 ``True`` 이면 모의투자용 웹소켓을, 아니면 실거래용
            웹소켓을 반환합니다.

        Parameters:
            paper_trading (bool): Flag indicating whether to target paper trading.

        Returns:
            str: WebSocket endpoint URL.
        """
        return cls.WSS_URL_FAKE if paper_trading else cls.WSS_URL
