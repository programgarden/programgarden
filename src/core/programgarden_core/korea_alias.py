"""
한글 별칭을 강제하기 위한 데코레이터와 메타클래스

이 모듈은 함수에 한글 별칭이 필요한 경우 이를 강제하기 위한
데코레이터와 메타클래스를 제공합니다.
이 기능은 함수가 한글 별칭을 갖도록 보장하며, 이를 통해
프로그램의 일관성을 유지합니다.

사용방법은
1. 함수에 `@require_korean_alias` 데코레이터를 적용합니다.
2. 클래스에 `EnforceKoreanAliasMeta` 메타클래스를 적용합니다.
이렇게 하면 해당 클래스의 모든 메서드가 한글 별칭을 갖도록 강제됩니다.

예시:
```python
from programgarden_core.korean_alias import require_korean_alias, EnforceKoreanAliasMeta

class OverseasStock(metaclass=EnforceKoreanAliasMeta):

    @require_korean_alias
    def accno(self) -> Accno:
        return Accno()

    계좌 = accno
    계좌.__doc__ = "계좌 정보를 조회합니다."

    ```

이렇게 하면 `accno`는 한글 별칭을 반드시 가져야 합니다.
만약 한글 별칭이 정의되지 않으면 `ValueError`가 발생합니다.
"""

from functools import wraps
import inspect


def require_korean_alias(func):
    """한글 별칭이 필요한 함수임을 표시하는 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._requires_korean_alias = True
    return wrapper


class EnforceKoreanAliasMeta(type):
    """한글 별칭 강제를 위한 메타클래스"""
    def __new__(cls, name, bases, attrs):
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
