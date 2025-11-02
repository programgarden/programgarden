"""Logging helpers for ProgramGarden namespaces.

EN:
    Provide convenience functions and colored formatters tailored to the
    ``pg`` logger hierarchy so that SDK users can obtain structured output.

KO:
    SDK 사용자가 ``pg`` 로거 계층을 통해 구조화된 출력을 쉽게 얻도록 컬러
    포매터와 편의 함수를 제공합니다.
"""

import logging
from typing import Dict

# EN: ANSI escape codes used to colorize log output by level.
# KO: 로그 레벨별 색상을 적용하기 위한 ANSI 이스케이프 코드 매핑입니다.
LOG_COLORS = {
    "INFO": "\033[92m",  # 초록색
    "WARNING": "\033[93m",  # 노란색
    "ERROR": "\033[91m",  # 빨간색
    "CRITICAL": "\033[41m",  # 배경 빨간색
    "RESET": "\033[0m",  # 색상 초기화
}

# EN: Base namespace for all ProgramGarden loggers.
# KO: ProgramGarden 로거 이름의 루트 네임스페이스입니다.
_BASE_LOGGER_NAME = "pg"

# EN: Canonical logger names grouped by functional categories.
# KO: 기능 영역별로 정리된 표준 로거 이름 매핑입니다.
_LOGGER_NAMES = {
    "system": f"{_BASE_LOGGER_NAME}.system",
    "strategy": f"{_BASE_LOGGER_NAME}.strategy",
    "condition": f"{_BASE_LOGGER_NAME}.condition",
    "trade": f"{_BASE_LOGGER_NAME}.trade",
    "order": f"{_BASE_LOGGER_NAME}.order",
    "plugin": f"{_BASE_LOGGER_NAME}.plugin",
    "symbol": f"{_BASE_LOGGER_NAME}.symbol",
    "finance": f"{_BASE_LOGGER_NAME}.finance",
}

# EN: Pre-resolved loggers exposed for external use.
# KO: 외부에서 바로 사용할 수 있도록 준비된 로거 인스턴스입니다.
pg_logger = logging.getLogger(_BASE_LOGGER_NAME)
system_logger = logging.getLogger(_LOGGER_NAMES["system"])
strategy_logger = logging.getLogger(_LOGGER_NAMES["strategy"])
condition_logger = logging.getLogger(_LOGGER_NAMES["condition"])
trade_logger = logging.getLogger(_LOGGER_NAMES["trade"])
order_logger = logging.getLogger(_LOGGER_NAMES["order"])
plugin_logger = logging.getLogger(_LOGGER_NAMES["plugin"])
symbol_logger = logging.getLogger(_LOGGER_NAMES["symbol"])
finance_logger = logging.getLogger(_LOGGER_NAMES["finance"])

_KNOWN_LOGGERS: Dict[str, logging.Logger] = {
    "pg": pg_logger,
    "system": system_logger,
    "strategy": strategy_logger,
    "condition": condition_logger,
    "trade": trade_logger,
    "order": order_logger,
    "plugin": plugin_logger,
    "symbol": symbol_logger,
    "finance": finance_logger,
}


class _ColoredFormatter(logging.Formatter):
    """Formatter that applies level-specific ANSI colors.

    EN:
        Colors timestamps, level names, and logger names while keeping the
        message body untouched for readability.

    KO:
        메시지 본문을 제외한 시간, 레벨, 로거 이름에 ANSI 색상을 입혀 가독성을
        높입니다.
    """

    def format_time(self, record, datefmt=None):
        """Format timestamp with level-based coloring.

        Parameters:
            record (logging.LogRecord): Log record produced by the handler.
            datefmt (Optional[str]): Optional datetime format string.

        Returns:
            str: Colorized timestamp string.
        """
        # 원본 levelname을 사용 (format()에서 _orig_levelname에 저장)
        orig_level = getattr(record, "_orig_levelname", record.levelname)
        log_color = LOG_COLORS.get(orig_level, LOG_COLORS["RESET"])
        t = super().formatTime(record, datefmt or "%Y-%m-%d %H:%M:%S")
        return f"{log_color}{t}{LOG_COLORS['RESET']}"

    def format(self, record):
        """Apply ANSI color codes to select record attributes.

        Parameters:
            record (logging.LogRecord): Log record to format.

        Returns:
            str: Fully formatted log message string.
        """
        # record의 원본 levelname을 저장 (나중에 formatTime에서 사용)
        orig_levelname = record.levelname
        record._orig_levelname = orig_levelname

        # 원본 levelname을 바탕으로 색상 결정
        color = LOG_COLORS.get(orig_levelname, LOG_COLORS["RESET"])
        record.levelname = f"{color}{orig_levelname}{LOG_COLORS['RESET']}"
        record.name = f"{color}{record.name}{LOG_COLORS['RESET']}"
        record.filename = f"{color}{record.pathname}{LOG_COLORS['RESET']}"

        # 숫자형 필드를 변경하지 않고, 새 필드에 색상 적용
        record.colored_lineno = f"{color}{record.lineno}{LOG_COLORS['RESET']}"

        return super().format(record)


def get_logger(category: str) -> logging.Logger:
    """Return a logger scoped to the ``pg`` namespace.

    EN:
        Provide consistent logger retrieval for custom categories, caching
        instances to avoid redundant creation.

    KO:
        커스텀 카테고리에 맞는 로거를 재사용할 수 있도록 생성 및 캐싱합니다.

    Parameters:
        category (str): Category or sub-namespace to retrieve.

    Returns:
        logging.Logger: Requested logger instance.
    """
    if not category:
        return pg_logger

    if category in _KNOWN_LOGGERS:
        return _KNOWN_LOGGERS[category]

    if category.startswith(f"{_BASE_LOGGER_NAME}."):
        logger_name = category
        registry_key = category.split(".", 1)[1]
    else:
        logger_name = f"{_BASE_LOGGER_NAME}.{category}"
        registry_key = category

    logger = logging.getLogger(logger_name)
    _KNOWN_LOGGERS[registry_key] = logger
    return logger


def pg_log(level=logging.DEBUG):
    """Configure base ``pg`` logger with colored console output.

    EN:
        Attach the custom colored formatter to the root ProgramGarden logger and
        propagate level settings to known child loggers.

    KO:
        ProgramGarden 루트 로거에 컬러 포매터를 부착하고 자식 로거에도 동일한
        레벨을 적용합니다.

    Parameters:
        level (int): Logging level constant (e.g., ``logging.INFO``).

    Returns:
        None: The function configures loggers in place.
    """

    formatter = _ColoredFormatter(
        "%(name)s | %(asctime)s | %(levelname)s | %(message)s"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    pg_logger.handlers.clear()
    pg_logger.addHandler(handler)
    pg_logger.setLevel(level)
    pg_logger.propagate = False  # 루트 로거로 전파 방지

    for name, logger in _KNOWN_LOGGERS.items():
        if logger is pg_logger:
            continue
        logger.setLevel(level)
        logger.propagate = True
        logger.handlers.clear()


def pg_log_disable():
    """Disable all loggers managed by ProgramGarden.

    EN:
        Clear handlers and set levels beyond ``CRITICAL`` to suppress output.

    KO:
        모든 핸들러를 제거하고 ``CRITICAL`` 보다 높은 레벨로 설정하여 로그를
        완전히 차단합니다.

    Returns:
        None: The function mutates global logging state.
    """
    for logger in _KNOWN_LOGGERS.values():
        logger.handlers.clear()
        logger.setLevel(logging.CRITICAL + 1)
        logger.propagate = False


def pg_log_reset():
    """Reset logger configuration to defaults.

    EN:
        Remove custom handlers and restore propagation for each known logger.

    KO:
        커스텀 핸들러를 제거하고 전파 설정을 복원하여 기본 상태로 되돌립니다.

    Returns:
        None: The function mutates global logging state.
    """
    for logger in _KNOWN_LOGGERS.values():
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True


# 테스트 코드
if __name__ == "__main__":
    # 자동 실행 제거 - 명시적으로 호출해야 함
    # pg_log(level=logging.DEBUG)  # 이 줄 제거
    pg_log()
    pg_logger.debug("디버그 메시지")
    system_logger.info("정보 메시지")
    pg_logger.warning("경고 메시지")
    pg_logger.error("에러 메시지")
    pg_logger.critical("치명적인 메시지")
