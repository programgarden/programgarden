"""한글 별칭 강제 유틸리티

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
    >>> from programgarden_core.korea_alias import require_korean_alias, EnforceKoreanAliasMeta
    >>> class OverseasStock(metaclass=EnforceKoreanAliasMeta):
    ...     @require_korean_alias
    ...     def accno(self):
    ...         return "account"
    ...     계좌 = accno
    ...     계좌.__doc__ = "계좌 정보를 조회합니다."
"""

from functools import wraps
import inspect
from abc import ABCMeta


def require_korean_alias(func):
    """한글 별칭이 필요한 함수를 표시하는 데코레이터

    EN:
        Attach metadata to ``func`` so ``EnforceKoreanAliasMeta`` can verify a
        corresponding Korean alias is defined on the owning class.

    KO:
        ``func`` 에 메타데이터를 부여하여 ``EnforceKoreanAliasMeta`` 가 한글
        별칭이 정의되어 있는지 검사할 수 있도록 합니다.

    Parameters:
        func (Callable): 한글 별칭이 필요한 메서드

    Returns:
        Callable: 별칭 요구사항을 담은 래핑된 함수
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._requires_korean_alias = True
    return wrapper


class EnforceKoreanAliasMeta(type):
    """데코레이트된 메서드에 대해 한글 별칭을 강제하는 메타클래스

    EN:
        Ensures every method decorated with ``@require_korean_alias`` has at
        least one Korean-named alias defined on the class.

    KO:
        ``@require_korean_alias`` 가 적용된 모든 메서드에 대해 한글 이름의 별칭이
        클래스에 정의되어 있는지 확인하는 메타클래스입니다.
    """

    def __new__(cls, name, bases, attrs):
        """클래스를 생성하고 한글 별칭 존재 여부를 검증

        EN:
            Walk through namespace ``attrs`` and confirm that decorated
            functions receive at least one Korean alias. A ``ValueError`` is
            raised when the requirement is not satisfied.

        KO:
            네임스페이스 ``attrs`` 를 순회하며 데코레이터가 적용된 함수에 한글
            별칭이 존재하는지 검증합니다. 조건을 만족하지 못하면
            ``ValueError`` 를 발생시킵니다.

        Parameters:
            name (str): 생성될 클래스 이름
            bases (Tuple[type, ...]): 상속받은 베이스 클래스들
            attrs (Dict[str, Any]): 클래스 속성을 담은 네임스페이스

        Returns:
            type: 검증 후 생성된 클래스 객체

        Raises:
            ValueError: 데코레이트된 함수에 한글 별칭이 없는 경우
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


class EnforceKoreanAliasABCMeta(EnforceKoreanAliasMeta, ABCMeta):
    """ABCMeta 확장 버전: 추상 메서드와 한글 별칭을 동시에 검증합니다."""
    pass
