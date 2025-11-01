"""Programgarden public interface exports.

EN:
    Aggregates the primary entry points consumed by external developers when
    integrating Programgarden with LS Securities, re-exporting clients,
    executors, listeners, and financial TR objects for convenient imports.

KR:
    Programgarden을 LS 증권과 연동하는 외부 개발자가 쉽게 가져다 쓸 수 있도록
    클라이언트, 실행기, 리스너, 금융 TR 객체 등을 재노출하는 공개 인터페이스를
    제공합니다.
"""

from programgarden.system_executor import SystemExecutor
from programgarden_core import exceptions
from .client import Programgarden
from .pg_listener import (
    PGListener,
)
from programgarden_finance import (
    ls,
    LS,
    oauth,
    overseas_stock,
    overseas_futureoption,

    COSAQ00102,
    COSAQ01400,
    COSOQ00201,
    COSOQ02701,
    g3103,
    g3202,
    g3203,
    g3204,
    g3101,
    g3102,
    g3104,
    g3106,
    g3190,

    o3101,
    o3104,
    o3105,
    o3106,
    o3107,
    o3116,
    o3121,
    o3123,
    o3125,
    o3126,
    o3127,
    o3128,
    o3136,
    o3137,

    COSAT00301,
    COSAT00311,
    COSMT00300,
    COSAT00400,

    CIDBQ01400,
    CIDBQ01500,
    CIDBQ01800,
    CIDBQ02400,
    CIDBQ03000,
    CIDBQ05300,
    CIDEQ00800,

    o3103,
    o3108,
    o3117,
    o3139,

    CIDBT00100,
    CIDBT00900,
    CIDBT01000
)

__all__ = [
    # EN: System orchestration executor coordinating strategy lifecycle.
    # KR: 전략 라이프사이클을 조율하는 시스템 오케스트레이션 실행기입니다.
    SystemExecutor,
    # EN: High-level client entry point for automating trading systems.
    # KR: 자동 매매 시스템을 실행하는 최상위 클라이언트 엔트리 포인트입니다.
    Programgarden,
    # EN: Convenience alias for top-level LS finance namespace.
    # KR: LS 금융 네임스페이스에 대한 편의 별칭입니다.
    ls,
    # EN: Concrete LS API client singleton accessor.
    # KR: LS API 클라이언트 싱글톤 접근자입니다.
    LS,
    # EN: OAuth helper utilities for LS authentication workflows.
    # KR: LS 인증 워크플로우용 OAuth 헬퍼 유틸리티입니다.
    oauth,
    # EN: Domain-specific exceptions shared with Programgarden core.
    # KR: Programgarden 코어와 공유하는 도메인 예외 모음입니다.
    exceptions,

    # EN: Listener helper exposing event subscription interfaces.
    # KR: 이벤트 구독 인터페이스를 제공하는 리스너 헬퍼입니다.
    PGListener,

    # EN: Trading resource namespaces for overseas stock and futures.
    # KR: 해외 주식 및 해외 선물 거래 리소스 네임스페이스입니다.
    overseas_stock,
    overseas_futureoption,

    # EN: Frequently used TR (transaction) objects for overseas stock.
    # KR: 해외 주식 거래에 자주 사용되는 TR(트랜잭션) 객체입니다.
    COSAQ00102,
    COSAQ01400,
    COSOQ00201,
    COSOQ02701,
    g3103,
    g3202,
    g3203,
    g3204,
    g3101,
    g3102,
    g3104,
    g3106,
    g3190,

    # EN: TR helpers assisting with overseas stock order orchestration.
    # KR: 해외 주식 주문 오케스트레이션을 지원하는 TR 헬퍼입니다.
    COSAT00301,
    COSAT00311,
    COSMT00300,
    COSAT00400,

    # EN: TR resources for overseas futures order and account handling.
    # KR: 해외 선물 주문 및 계좌 처리를 위한 TR 리소스입니다.
    o3101,
    o3104,
    o3105,
    o3106,
    o3107,
    o3116,
    o3121,
    o3123,
    o3125,
    o3126,
    o3127,
    o3128,
    o3136,
    o3137,

    # EN: Account and balance query TR groups for account monitoring.
    # KR: 계좌 모니터링을 위한 계좌/잔고 조회 TR 그룹입니다.
    CIDBQ01400,
    CIDBQ01500,
    CIDBQ01800,
    CIDBQ02400,
    CIDBQ03000,
    CIDBQ05300,
    CIDEQ00800,

    # EN: Supplementary derivatives TR entries for order lifecycle.
    # KR: 주문 라이프사이클을 위한 파생상품 TR 보조 항목입니다.
    o3103,
    o3108,
    o3117,
    o3139,

    # EN: Derivatives trade record TR identifiers for settlement flows.
    # KR: 결제 흐름을 위한 파생상품 거래 기록 TR 식별자입니다.
    CIDBT00100,
    CIDBT00900,
    CIDBT01000
]
