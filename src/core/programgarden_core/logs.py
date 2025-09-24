import logging

# ANSI 색상 코드
LOG_COLORS = {
    "INFO": "\033[92m",  # 초록색
    "WARNING": "\033[93m",  # 노란색
    "ERROR": "\033[91m",  # 빨간색
    "CRITICAL": "\033[41m",  # 배경 빨간색
    "RESET": "\033[0m",  # 색상 초기화
}

pg_logger = logging.getLogger("pg")


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

    handler = logging.StreamHandler()
    pg_logger.setLevel(level)
    formatter = _ColoredFormatter(
        "%(name)s | %(asctime)s | %(levelname)s | %(filename)s:%(colored_lineno)s\n %(message)s"  # noqa: E501
    )
    handler.setFormatter(formatter)
    pg_logger.addHandler(handler)

    # 루트 로거에 영향을 주지 않도록 설정
    pg_logger.propagate = False  # 루트 로거로 전파 방지


def pg_log_disable():
    """로그를 완전히 비활성화합니다."""
    pg_logger.handlers.clear()
    pg_logger.setLevel(logging.CRITICAL + 1)  # 모든 로그 차단


def pg_log_reset():
    """로그 설정을 초기화합니다."""
    pg_logger.handlers.clear()
    pg_logger.setLevel(logging.NOTSET)


# 테스트 코드
if __name__ == "__main__":
    # 자동 실행 제거 - 명시적으로 호출해야 함
    # pg_log(level=logging.DEBUG)  # 이 줄 제거
    pg_log()
    pg_logger.debug("디버그 메시지")
    pg_logger.info("정보 메시지")
    pg_logger.warning("경고 메시지")
    pg_logger.error("에러 메시지")
    pg_logger.critical("치명적인 메시지")
