"""Utilities for enforcing Korean aliases on callables and classes.

EN:
    Provide a decorator and metaclass that guarantee the presence of Korean
    aliases for methods so that both English and Korean APIs stay synchronized.
    Apply ``@require_korean_alias`` to methods and ``EnforceKoreanAliasMeta`` as
    a metaclass to ensure each decorated method has at least one Korean alias.

KO:
    메서드가 한글 별칭을 반드시 갖도록 보장하는 데코레이터와 메타클래스를
    제공합니다. ``@require_korean_alias`` 데코레이터와
    ``EnforceKoreanAliasMeta`` 메타클래스를 적용하면 영어/한글 API를 동시에
    유지할 수 있습니다.

Example / 예시:
    >>> from programgarden_core.korea_alias import require_korean_alias,
    ...     EnforceKoreanAliasMeta
    >>> class OverseasStock(metaclass=EnforceKoreanAliasMeta):
    ...     @require_korean_alias
    ...     def accno(self):
    ...         return "account"
    ...     계좌 = accno
    ...     계좌.__doc__ = "계좌 정보를 조회합니다."
"""

from functools import wraps
import inspect


def require_korean_alias(func):
    """Mark functions that must expose a Korean alias.

    EN:
        Attach metadata to ``func`` so ``EnforceKoreanAliasMeta`` can verify a
        corresponding Korean alias is defined on the owning class.

    KO:
        ``func`` 에 메타데이터를 부여하여 ``EnforceKoreanAliasMeta`` 가 한글
        별칭이 정의되어 있는지 검사할 수 있도록 합니다.

    Parameters:
        func (Callable): A method that requires a Korean alias binding.

    Returns:
        Callable: The wrapped function carrying alias requirements.

    Raises:
        None: The decorator never raises and simply augments the function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._requires_korean_alias = True
    return wrapper


class EnforceKoreanAliasMeta(type):
    """Metaclass that enforces Korean aliases for decorated methods.

    EN:
        Ensures every method decorated with ``@require_korean_alias`` has at
        least one Korean-named alias defined on the class.

    KO:
        ``@require_korean_alias`` 가 적용된 모든 메서드에 대해 한글 이름의 별칭이
        클래스에 정의되어 있는지 확인하는 메타클래스입니다.
    """

    def __new__(cls, name, bases, attrs):
        """Create a class and validate the presence of Korean aliases.

        EN:
            Walk through namespace ``attrs`` and confirm that decorated
            functions receive at least one Korean alias. A ``ValueError`` is
            raised when the requirement is not satisfied.

        KO:
            네임스페이스 ``attrs`` 를 순회하며 데코레이터가 적용된 함수에 한글
            별칭이 존재하는지 검증합니다. 조건을 만족하지 못하면
            ``ValueError`` 를 발생시킵니다.

        Parameters:
            name (str): The class name being constructed.
            bases (Tuple[type, ...]): Inherited base classes.
            attrs (Dict[str, Any]): Namespace containing class attributes.

        Returns:
            type: The finalized class object after validation.

        Raises:
            ValueError: Missing Korean aliases for decorated functions.
        """
        korean_aliases = set()
        # 한글 별칭 수집
        for key, value in attrs.items():
            if key.startswith('__') or not key.encode().isalnum() or key.isascii():
                continue
            korean_aliases.add(value.__name__ if callable(value) else key)

        # @require_korean_alias가 붙은 메서드만 검사
        for key, value in attrs.items():
            if not inspect.isfunction(value) or key.startswith('__'):
                continue

            # 데코레이터가 붙은 경우에만 한글 별칭 검사
            if getattr(value, '_requires_korean_alias', False):

                has_korean_alias = False
                for alias_key, alias_value in attrs.items():
                    if (
                        not alias_key.startswith('__')
                        and not alias_key.isascii()
                        and callable(alias_value)
                        and alias_value.__name__ == value.__name__
                    ):
                        has_korean_alias = True
                        break

                if not has_korean_alias:
                    raise ValueError(
                        f"메서드 '{key}'는 @require_korean_alias 데코레이터가 적용되었으나 "
                        "한글 별칭이 정의되지 않았습니다."
                    )

        return super().__new__(cls, name, bases, attrs)
