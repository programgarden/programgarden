"""programgarden.system_keys

EN:
    Validation helpers that ensure user-supplied system configuration
    dictionaries include the mandatory sections required for Programgarden to
    operate (settings, securities, strategies, credentials, etc.). By invoking
    :func:`exist_system_keys_error`, library integrators receive immediate and
    explicit feedback about missing fields before runtime execution begins.

KR:
    Programgarden이 동작하는 데 필요한 필수 섹션(설정, 증권, 전략, 인증 정보 등)이
    사용자 제공 시스템 구성 딕셔너리에 포함되어 있는지 검증하는 도우미입니다.
    :func:`exist_system_keys_error`를 호출하면 실행 전에 누락 필드를 명확하게
    확인할 수 있습니다.
"""

from programgarden_core import (
    SystemType,
    exceptions,
    system_logger,
)


def exist_system_keys_error(system: SystemType) -> None:
    """Validate presence and structure of required system configuration keys.

    EN:
        Checks that the incoming ``system`` dictionary includes mandatory
        sections and sub-keys (settings, securities, strategies) and raises
        domain-specific exceptions when validations fail. Logging statements
        provide immediate operator feedback.

    KR:
        전달된 ``system`` 딕셔너리가 필수 섹션 및 하위 키(설정, 증권, 전략 등)를
        포함하는지 검사하고, 유효성 검증 실패 시 도메인 예외를 발생시킵니다.
        로깅을 통해 운영자가 즉시 문제를 파악할 수 있습니다.

    Args:
        system (SystemType):
            EN: User-provided system configuration, typically loaded from
            external YAML/JSON.
            KR: 외부 YAML/JSON에서 로드된 사용자 제공 시스템 구성입니다.

    Returns:
        None:
            EN: Function performs validation side effects and raises on failure.
            KR: 검증 부수 효과만 수행하며, 실패 시 예외를 발생시킬 뿐 값을 반환하지
            않습니다.

    Raises:
        exceptions.NotExistSystemException:
            EN: Raised when the root object is not a dictionary.
            KR: 루트 객체가 딕셔너리가 아닐 경우 발생합니다.
        exceptions.NotExistSystemKeyException:
            EN: Raised when required subsections or keys are missing or of the
            wrong type.
            KR: 필수 하위 섹션이나 키가 없거나 타입이 잘못된 경우 발생합니다.
    """

    if not isinstance(system, dict):
        system_logger.error("Invalid system configuration: must be a dictionary.")
        raise exceptions.NotExistSystemException(
            message="Invalid system configuration: must be a dictionary.",
        )

    # --- settings ---
    settings = system.get("settings", {})
    if not settings:
        system_logger.error("System settings information ('settings') is required.")
        raise exceptions.NotExistSystemKeyException(
            message="System settings information ('settings') is required.",
        )

    if not isinstance(settings, dict):
        system_logger.error("System settings information ('settings') must be a dictionary.")
        raise exceptions.NotExistSystemKeyException(
            message="System settings information ('settings') must be a dictionary.",
        )

    if not settings.get("system_id", None):
        system_logger.error("System settings must include a unique 'system_id'.")
        raise exceptions.NotExistSystemKeyException(
            message="System settings must include a unique 'system_id'.",
        )

    # --- securities ---
    securities = system.get("securities")
    if securities is None:
        system_logger.error("System securities information ('securities') is required.")
        raise exceptions.NotExistSystemKeyException(
            message="System securities information ('securities') is required.",
        )

    if not isinstance(securities, dict):
        system_logger.error("System securities information ('securities') must be a dictionary.")
        raise exceptions.NotExistSystemKeyException(
            message="System securities information ('securities') must be a dictionary.",
        )

    # EN: Minimal credential fields required to authenticate and select LS products.
    # KR: LS 인증 및 상품 선택에 필수적인 최소 자격 필드입니다.
    required_sec_keys = ["company", "product", "appkey", "appsecretkey"]
    for key in required_sec_keys:
        if key not in securities:
            system_logger.error(f"Missing '{key}' key in system securities.")
            raise exceptions.NotExistSystemKeyException(
                message=f"Missing '{key}' key in system securities."
            )

    # --- strategies ---
    strategies = system.get("strategies", [])
    if strategies is None:
        strategies = []

    if not isinstance(strategies, list):
        system_logger.error("System strategies ('strategies') must be a list.")
        raise exceptions.NotExistSystemKeyException(
            message="'strategies' must be a list."
        )

    # EN: Strategy metadata keys necessary to drive condition evaluation pipelines.
    # KR: 조건 평가 파이프라인을 수행하는 데 필요한 전략 메타데이터 키입니다.
    required_strategy_keys = [
        "id",
    ]

    for idx, strategy in enumerate(strategies):
        if not isinstance(strategy, dict):
            raise exceptions.NotExistSystemKeyException(
                message=f"strategies[{idx}] must be a dictionary."
            )

        strategy_id = strategy.get("id")
        if not strategy_id:
            raise exceptions.NotExistSystemKeyException(
                message=f"strategies[{idx}] requires a unique 'id'."
            )

        for key in required_strategy_keys:
            if key not in strategy:
                raise exceptions.NotExistSystemKeyException(
                    message=f"Strategy '{strategy_id}' is missing '{key}' key."
                )

        buy_or_sell = strategy.get("buy_or_sell", None)
        if buy_or_sell not in ("buy_new", "sell_new", None):
            raise exceptions.NotExistSystemKeyException(
                message=f"Strategy '{strategy_id}' has invalid 'buy_or_sell' value: {buy_or_sell}"
            )
