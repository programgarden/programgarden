"""Finance 패키지용 믹스인 클래스들

EN:
    Mixin classes for finance package (singleton pattern, etc.)

KO:
    Finance 패키지용 믹스인 클래스들 (싱글톤 패턴 등)
"""

from __future__ import annotations

import threading
from typing import Any, ClassVar, Dict, Optional, Tuple, Type, TypeVar

T = TypeVar("T", bound="SingletonClientMixin")


class SingletonClientMixin:
    """브로커 클라이언트를 위한 스레드 안전 싱글톤 헬퍼

    EN:
        Thread-safe singleton helper for broker clients.

    KO:
        브로커 클라이언트의 스레드 안전 싱글톤 패턴을 지원하는 믹스인입니다.
    """

    _singleton_instance: ClassVar[Optional[T]] = None
    _singleton_lock: ClassVar[threading.RLock] = threading.RLock()
    _singleton_args: ClassVar[Tuple[Any, ...]] = ()
    _singleton_kwargs: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """프로세스 전체에서 유일한 싱글톤 인스턴스 반환

        EN:
            Return a process-wide singleton instance of the subclass.
            Additional positional/keyword arguments are applied only when the
            singleton is first created. Subsequent calls ignore arguments unless
            they match the stored configuration.

        KO:
            서브클래스의 프로세스 전체 싱글톤 인스턴스를 반환합니다.
            추가 인자는 싱글톤이 처음 생성될 때만 적용됩니다.
            이후 호출은 저장된 설정과 일치하지 않으면 인자를 무시합니다.

        Parameters:
            *args: 생성자에 전달할 위치 인자
            **kwargs: 생성자에 전달할 키워드 인자

        Returns:
            T: 싱글톤 인스턴스

        Raises:
            ValueError: 이미 다른 인자로 초기화된 경우
        """
        with cls._singleton_lock:
            if cls._singleton_instance is None:
                cls._singleton_args = args
                cls._singleton_kwargs = kwargs
                cls._singleton_instance = cls(*args, **kwargs)  # type: ignore[call-arg]
            else:
                if args or kwargs:
                    if args != cls._singleton_args or kwargs != cls._singleton_kwargs:
                        raise ValueError(
                            "Singleton already initialized with different arguments. "
                            "Call reset_instance() before reconfiguring."
                        )
            return cls._singleton_instance  # type: ignore[return-value]

    @classmethod
    def reset_instance(cls) -> None:
        """캐시된 싱글톤 인스턴스 리셋 (주로 테스트용)

        EN:
            Reset the cached singleton (mainly for testing).

        KO:
            캐시된 싱글톤 인스턴스를 리셋합니다 (주로 테스트 용도).
        """
        with cls._singleton_lock:
            cls._singleton_instance = None
            cls._singleton_args = ()
            cls._singleton_kwargs = {}
