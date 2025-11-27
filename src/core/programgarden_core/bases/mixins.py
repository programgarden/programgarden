from __future__ import annotations

import threading
from typing import Any, ClassVar, Dict, Optional, Tuple, Type, TypeVar

T = TypeVar("T", bound="SingletonClientMixin")


class SingletonClientMixin:
    """Thread-safe singleton helper for broker clients."""

    _singleton_instance: ClassVar[Optional[T]] = None
    _singleton_lock: ClassVar[threading.RLock] = threading.RLock()
    _singleton_args: ClassVar[Tuple[Any, ...]] = ()
    _singleton_kwargs: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """Return a process-wide singleton instance of the subclass.

        Additional positional/keyword arguments are applied only when the
        singleton is first created. Subsequent calls ignore arguments unless
        they match the stored configuration.
        """
        with cls._singleton_lock:
            if cls._singleton_instance is None:
                cls._singleton_args = args
                cls._singleton_kwargs = kwargs
                cls._singleton_instance = cls(*args, **kwargs)
            else:
                if args or kwargs:
                    if args != cls._singleton_args or kwargs != cls._singleton_kwargs:
                        raise ValueError(
                            "Singleton already initialized with different arguments. "
                            "Call reset_instance() before reconfiguring."
                        )
            return cls._singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the cached singleton (mainly for testing)."""
        with cls._singleton_lock:
            cls._singleton_instance = None
            cls._singleton_args = ()
            cls._singleton_kwargs = {}
