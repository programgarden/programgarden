"""
ProgramGarden - Binding Type Validator

바인딩된 값의 타입을 검증합니다.
타입 불일치 시 에러 메시지를 반환하여 UI에서 빨간색 글씨로 표시할 수 있습니다.
"""

from typing import Any, Optional, Tuple, Callable, Dict
from dataclasses import dataclass


@dataclass
class BindingValidationResult:
    """바인딩 검증 결과"""
    
    field_name: str
    is_valid: bool
    error_message: Optional[str] = None
    actual_type: Optional[str] = None
    expected_type: Optional[str] = None


class BindingTypeValidator:
    """
    바인딩된 값의 타입 검증
    
    FieldSchema의 expected_type과 실제 값을 비교하여 타입 일치 여부를 확인합니다.
    UI에서 타입 불일치 시 바인딩 표현식을 빨간색 글씨로 표시하는데 사용됩니다.
    
    Example:
        is_valid, error = BindingTypeValidator.validate(
            value={"AAPL": 150.0},
            expected_type="dict[str, float]",
            field_name="price_data"
        )
        # is_valid=True, error=None
        
        is_valid, error = BindingTypeValidator.validate(
            value="not a dict",
            expected_type="dict[str, float]",
            field_name="price_data"
        )
        # is_valid=False, error="'price_data' 타입 불일치: 예상 dict[str, float], 실제 str"
    """
    
    # 타입 문자열 → 검증 함수 매핑
    TYPE_VALIDATORS: Dict[str, Callable[[Any], bool]] = {
        # 기본 타입
        "dict": lambda v: isinstance(v, dict),
        "list": lambda v: isinstance(v, list),
        "float": lambda v: isinstance(v, (int, float)),
        "int": lambda v: isinstance(v, int),
        "str": lambda v: isinstance(v, str),
        "bool": lambda v: isinstance(v, bool),
        "any": lambda v: True,
        
        # 복합 타입
        "dict[str, float]": lambda v: (
            isinstance(v, dict) and 
            all(isinstance(k, str) and isinstance(val, (int, float)) for k, val in v.items())
        ),
        "dict[str, any]": lambda v: (
            isinstance(v, dict) and 
            all(isinstance(k, str) for k in v.keys())
        ),
        "list[str]": lambda v: (
            isinstance(v, list) and 
            all(isinstance(i, str) for i in v)
        ),
        "list[dict]": lambda v: (
            isinstance(v, list) and 
            all(isinstance(i, dict) for i in v)
        ),
        "list[float]": lambda v: (
            isinstance(v, list) and 
            all(isinstance(i, (int, float)) for i in v)
        ),
        
        # 특수 타입 (노드 출력 형태)
        "symbol_list": lambda v: (
            isinstance(v, list) and 
            all(isinstance(i, (str, dict)) for i in v)
        ),
        "market_data": lambda v: isinstance(v, dict),
        "position_data": lambda v: (
            isinstance(v, list) and
            all(isinstance(i, dict) for i in v)
        ),
        "balance_data": lambda v: isinstance(v, dict),
        "order_list": lambda v: isinstance(v, list),
    }
    
    @classmethod
    def validate(
        cls,
        value: Any,
        expected_type: Optional[str],
        field_name: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        값의 타입 검증
        
        Args:
            value: 검증할 값
            expected_type: 기대하는 타입 문자열
            field_name: 필드 이름 (에러 메시지용)
            
        Returns:
            (is_valid, error_message)
        """
        # expected_type이 없으면 검증 패스
        if expected_type is None:
            return True, None
        
        # None 값은 통과 (선택적 필드일 수 있음)
        if value is None:
            return True, None
        
        validator = cls.TYPE_VALIDATORS.get(expected_type)
        if validator is None:
            # 알 수 없는 타입은 통과 (확장 가능성)
            return True, None
        
        if validator(value):
            return True, None
        
        actual_type = type(value).__name__
        
        # 더 자세한 타입 정보 제공
        if isinstance(value, list) and len(value) > 0:
            item_type = type(value[0]).__name__
            actual_type = f"list[{item_type}]"
        elif isinstance(value, dict) and len(value) > 0:
            key_type = type(next(iter(value.keys()))).__name__
            val_type = type(next(iter(value.values()))).__name__
            actual_type = f"dict[{key_type}, {val_type}]"
        
        return False, (
            f"'{field_name}' 타입 불일치: "
            f"예상 {expected_type}, 실제 {actual_type}"
        )
    
    @classmethod
    def validate_config(
        cls,
        config: Dict[str, Any],
        field_schemas: Dict[str, Any],
    ) -> list[BindingValidationResult]:
        """
        config 전체의 타입 검증
        
        Args:
            config: 노드 config
            field_schemas: 필드 스키마 딕셔너리 (get_field_schema() 결과)
            
        Returns:
            검증 결과 리스트 (에러가 있는 필드만)
        """
        results = []
        
        for field_name, schema in field_schemas.items():
            if field_name not in config:
                continue
            
            expected_type = getattr(schema, 'expected_type', None)
            if expected_type is None:
                continue
            
            value = config[field_name]
            is_valid, error_msg = cls.validate(value, expected_type, field_name)
            
            if not is_valid:
                results.append(BindingValidationResult(
                    field_name=field_name,
                    is_valid=False,
                    error_message=error_msg,
                    actual_type=type(value).__name__,
                    expected_type=expected_type,
                ))
        
        return results
