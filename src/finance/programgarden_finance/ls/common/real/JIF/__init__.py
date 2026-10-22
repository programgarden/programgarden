"""JIF (Market Status) real-time WebSocket subscription.

Supports 12 markets: KOSPI, KOSDAQ, KRX_FUTURES, NXT, KRX_NIGHT, US,
CN_AM, CN_PM, HK_AM, HK_PM, JP_AM, JP_PM.

Overseas futures markets (CME, HKEx Futures, SGX, etc.) are NOT
covered by JIF and cannot be queried through this client.

Usable regardless of broker credential type (overseas_stock /
overseas_futureoption / korea_stock) — only an access token is required.
"""

from .client import RealJIF

__all__ = ["RealJIF"]
