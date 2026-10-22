"""Broker-agnostic LS Securities features.

EN:
    Hosts WebSocket TRs that do not depend on a specific broker credential
    type (overseas_stock / overseas_futureoption / korea_stock). Currently
    exposes the JIF (Market Status) real-time stream.

KO:
    특정 broker credential 타입에 종속되지 않는 LS증권 공용 기능을
    모아둔 네임스페이스입니다. 현재는 JIF(장운영정보) 실시간 스트림을
    제공합니다.
"""

from typing import Dict

from programgarden_core.korea_alias import require_korean_alias
from programgarden_finance.ls.token_manager import TokenManager

from .real import Real


class Common:
    """Broker-agnostic entry point exposing common real-time TRs.

    EN:
        Mirrors the OverseasStock/OverseasFutureoption/KoreaStock shape:
        instances are keyed by ``token_manager`` identity so multiple
        broker flows share a single WebSocket session.

    KO:
        OverseasStock/OverseasFutureoption/KoreaStock 와 동일한 구조로,
        ``token_manager`` 식별자별로 Real 인스턴스를 공유합니다.
        여러 broker 경로가 단일 WebSocket 세션을 재사용할 수 있도록
        _real_instances 캐시를 유지합니다.
    """

    _real_instances: Dict[int, "Real"] = {}

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def real(
        self,
        reconnect: bool = True,
        recv_timeout: float = 5.0,
        ping_interval: float = 30.0,
        ping_timeout: float = 5.0,
        max_backoff: float = 60.0,
    ) -> "Real":
        key = id(self.token_manager)
        cached = Common._real_instances.get(key)
        if cached is not None:
            return cached
        instance = Real(
            token_manager=self.token_manager,
            reconnect=reconnect,
            recv_timeout=recv_timeout,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            max_backoff=max_backoff,
        )
        Common._real_instances[key] = instance
        return instance

    실시간 = real
    실시간.__doc__ = "공용 실시간 데이터(JIF 장운영정보 등)를 조회합니다."

    @classmethod
    def _clear_real_instance(cls, token_manager_id: int) -> None:
        cls._real_instances.pop(token_manager_id, None)


__all__ = [
    "Common",
    "Real",
]
