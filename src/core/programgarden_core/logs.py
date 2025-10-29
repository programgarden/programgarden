import logging
from typing import Dict

# ANSI 색상 코드
LOG_COLORS = {
    "INFO": "\033[92m",  # 초록색
    "WARNING": "\033[93m",  # 노란색
    "ERROR": "\033[91m",  # 빨간색
    "CRITICAL": "\033[41m",  # 배경 빨간색
    "RESET": "\033[0m",  # 색상 초기화
}

_BASE_LOGGER_NAME = "pg"
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
    """메시지를 제외한 모든 항목에 로그 레벨별 색상을 입히는 포매터"""

    def format_time(self, record, datefmt=None):
        # 원본 levelname을 사용 (format()에서 _orig_levelname에 저장)
        orig_level = getattr(record, "_orig_levelname", record.levelname)
        log_color = LOG_COLORS.get(orig_level, LOG_COLORS["RESET"])
        t = super().formatTime(record, datefmt or "%Y-%m-%d %H:%M:%S")
        return f"{log_color}{t}{LOG_COLORS['RESET']}"

    def format(self, record):
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
    """Return a named logger under the pg namespace."""
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
    """
    로그 레벨을 설정합니다.
    설정된 레벨부터 표시됩니다.

    .. code-block:: python
        logger.debug("디버그 메시지")
        logger.info("정보 메시지")
        logger.warning("경고 메시지")
        logger.error("에러 메시지")
        logger.critical("치명적인 메시지")
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
    """로그를 완전히 비활성화합니다."""
    for logger in _KNOWN_LOGGERS.values():
        logger.handlers.clear()
        logger.setLevel(logging.CRITICAL + 1)
        logger.propagate = False


def pg_log_reset():
    """로그 설정을 초기화합니다."""
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
