"""
바인딩 타입 검증 테스트

BindingTypeValidator의 타입 검증 로직을 테스트합니다.
"""

import pytest
from programgarden.binding_validator import BindingTypeValidator, BindingValidationResult


class TestBindingTypeValidator:
    """BindingTypeValidator 단위 테스트"""
    
    def test_dict_type_validation(self):
        """dict 타입 검증"""
        is_valid, error = BindingTypeValidator.validate(
            {"AAPL": 150.0, "TSLA": 250.0},
            "dict[str, float]",
            "price_data"
        )
        assert is_valid
        assert error is None
    
    def test_dict_type_mismatch(self):
        """dict 타입 불일치"""
        is_valid, error = BindingTypeValidator.validate(
            "not a dict",
            "dict[str, float]",
            "price_data"
        )
        assert not is_valid
        assert "타입 불일치" in error
        assert "price_data" in error
        assert "dict[str, float]" in error
    
    def test_list_str_validation(self):
        """list[str] 타입 검증"""
        is_valid, error = BindingTypeValidator.validate(
            ["AAPL", "TSLA", "NVDA"],
            "list[str]",
            "symbols"
        )
        assert is_valid
        assert error is None
    
    def test_list_str_type_mismatch(self):
        """list[str] 타입 불일치 (int 요소 포함)"""
        is_valid, error = BindingTypeValidator.validate(
            ["AAPL", 123, "NVDA"],
            "list[str]",
            "symbols"
        )
        assert not is_valid
        assert "타입 불일치" in error
    
    def test_list_dict_validation(self):
        """list[dict] 타입 검증"""
        is_valid, error = BindingTypeValidator.validate(
            [{"order_id": "ORD001"}, {"order_id": "ORD002"}],
            "list[dict]",
            "target_orders"
        )
        assert is_valid
        assert error is None
    
    def test_none_value_passes(self):
        """None 값은 통과"""
        is_valid, error = BindingTypeValidator.validate(
            None,
            "dict[str, float]",
            "price_data"
        )
        assert is_valid
        assert error is None
    
    def test_none_expected_type_passes(self):
        """expected_type이 None이면 통과"""
        is_valid, error = BindingTypeValidator.validate(
            "any value",
            None,
            "some_field"
        )
        assert is_valid
        assert error is None
    
    def test_unknown_type_passes(self):
        """알 수 없는 타입은 통과"""
        is_valid, error = BindingTypeValidator.validate(
            "value",
            "unknown_type_xyz",
            "field"
        )
        assert is_valid
        assert error is None
    
    def test_basic_dict_type(self):
        """기본 dict 타입 검증"""
        is_valid, error = BindingTypeValidator.validate(
            {"key": "value"},
            "dict",
            "config"
        )
        assert is_valid
    
    def test_basic_list_type(self):
        """기본 list 타입 검증"""
        is_valid, error = BindingTypeValidator.validate(
            [1, 2, 3],
            "list",
            "items"
        )
        assert is_valid
    
    def test_symbol_list_type(self):
        """symbol_list 특수 타입 (str 또는 dict 요소)"""
        # 문자열 리스트
        is_valid, error = BindingTypeValidator.validate(
            ["AAPL", "TSLA"],
            "symbol_list",
            "symbols"
        )
        assert is_valid
        
        # dict 리스트 (거래소 포함)
        is_valid, error = BindingTypeValidator.validate(
            [{"exchange": "NASDAQ", "symbol": "AAPL"}],
            "symbol_list",
            "symbols"
        )
        assert is_valid


class TestValidateConfig:
    """validate_config 메서드 테스트"""
    
    def test_validate_config_with_errors(self):
        """config 전체 검증 (에러 케이스)"""
        from unittest.mock import MagicMock
        
        # Mock FieldSchema
        schema1 = MagicMock()
        schema1.expected_type = "dict[str, float]"
        
        schema2 = MagicMock()
        schema2.expected_type = "list[str]"
        
        field_schemas = {
            "price_data": schema1,
            "symbols": schema2,
        }
        
        config = {
            "price_data": "not a dict",  # 에러
            "symbols": ["AAPL", "TSLA"],  # 정상
        }
        
        results = BindingTypeValidator.validate_config(config, field_schemas)
        
        assert len(results) == 1
        assert results[0].field_name == "price_data"
        assert not results[0].is_valid
    
    def test_validate_config_all_valid(self):
        """config 전체 검증 (정상 케이스)"""
        from unittest.mock import MagicMock
        
        schema1 = MagicMock()
        schema1.expected_type = "dict[str, float]"
        
        field_schemas = {
            "price_data": schema1,
        }
        
        config = {
            "price_data": {"AAPL": 150.0},
        }
        
        results = BindingTypeValidator.validate_config(config, field_schemas)
        assert len(results) == 0  # 에러 없음
