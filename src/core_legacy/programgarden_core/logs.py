"""Logging namespace for ProgramGarden.

EN:
    Provides a base logger under the ``programgarden`` namespace with NullHandler
    as default. All internal modules use ``programgarden.*`` namespace loggers
    (e.g., ``programgarden.client``, ``programgarden.ls.token_manager``).
    
    By default, no logs are output. Developers who need logging can 
    configure their own handlers.

    Example - Enable all ProgramGarden logs:
        import logging

        logging.getLogger('programgarden').setLevel(logging.DEBUG)
        logging.getLogger('programgarden').addHandler(logging.StreamHandler())

    Example - Enable only LS API logs:
        import logging

        logging.getLogger('programgarden.ls').setLevel(logging.DEBUG)
        logging.getLogger('programgarden.ls').addHandler(logging.StreamHandler())

KO:
    ``programgarden`` 네임스페이스 기본 로거를 NullHandler와 함께 제공합니다.
    모든 내부 모듈은 ``programgarden.*`` 네임스페이스 로거를 사용합니다
    (예: ``programgarden.client``, ``programgarden.ls.token_manager``).
    
    기본적으로 로그는 출력되지 않습니다. 로깅이 필요한 개발자는 
    직접 핸들러를 설정할 수 있습니다.

    예시 - 모든 ProgramGarden 로그 활성화:
        import logging

        logging.getLogger('programgarden').setLevel(logging.DEBUG)
        logging.getLogger('programgarden').addHandler(logging.StreamHandler())

    예시 - LS API 로그만 활성화:
        import logging

        logging.getLogger('programgarden.ls').setLevel(logging.DEBUG)
        logging.getLogger('programgarden.ls').addHandler(logging.StreamHandler())
"""

import logging

# Base logger with NullHandler (silent by default)
_pg_logger = logging.getLogger("programgarden")
_pg_logger.addHandler(logging.NullHandler())
_pg_logger.propagate = True
