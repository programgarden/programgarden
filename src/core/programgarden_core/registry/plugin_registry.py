"""
ProgramGarden Core - PluginRegistry

플러그인 스키마 레지스트리
커뮤니티 전략 플러그인(RSI, MACD, MarketOrder 등) 관리
"""

from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

if TYPE_CHECKING:
    from programgarden_core.models.plugin_resource import PluginResourceHints, TrustLevel


class PluginCategory(str, Enum):
    """플러그인 카테고리"""

    STRATEGY_CONDITION = "strategy_condition"  # 조건 전략 (RSI, MACD 등)
    NEW_ORDER = "new_order"  # 신규 주문 (MarketOrder, LimitOrder 등)
    MODIFY_ORDER = "modify_order"  # 정정 주문 (TrackingPrice 등)
    CANCEL_ORDER = "cancel_order"  # 취소 주문 (TimeStop 등)


class ProductType(str, Enum):
    """상품 유형"""

    OVERSEAS_STOCK = "overseas_stock"
    OVERSEAS_FUTURES = "overseas_futures"


class PluginSchema(BaseModel):
    """플러그인 스키마 (AI 에이전트용)"""

    id: str = Field(..., description="플러그인 ID")
    name: Optional[str] = Field(default=None, description="플러그인 이름")
    category: PluginCategory = Field(..., description="플러그인 카테고리")
    version: str = Field(default="1.0.0", description="플러그인 버전")
    description: Optional[str] = Field(default=None, description="플러그인 설명")

    # 지원 상품
    products: List[ProductType] = Field(
        default_factory=lambda: [ProductType.OVERSEAS_STOCK, ProductType.OVERSEAS_FUTURES],
        description="지원 상품 유형",
    )

    # 필드 스키마 (params_schema에서 변경)
    fields_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="필드 스키마 (타입, 기본값, 바인딩 가능 여부 등)",
    )

    # 필요 데이터
    required_data: List[str] = Field(
        default_factory=list,
        description="필요한 데이터 (price_data, volume_data, position_data 등)",
    )

    # 메타데이터
    author: Optional[str] = Field(default=None, description="작성자")
    tags: List[str] = Field(default_factory=list, description="태그")
    
    # i18n 지원 (신규)
    locales: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="다국어 번역 (locale: {name, description, fields.xxx})",
    )
    
    # 리소스 관리 (신규)
    resource_hints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="플러그인 리소스 사용 힌트 (PluginResourceHints)",
    )
    trust_level: str = Field(
        default="community",
        description="플러그인 신뢰 레벨 (core, verified, community)",
    )
    
    def get_localized_name(self, locale: str = "en") -> str:
        """Get localized name, fallback to default name"""
        if locale in self.locales and "name" in self.locales[locale]:
            return self.locales[locale]["name"]
        return self.name or self.id
    
    def get_localized_description(self, locale: str = "en") -> str:
        """Get localized description, fallback to default description"""
        if locale in self.locales and "description" in self.locales[locale]:
            return self.locales[locale]["description"]
        return self.description or ""
    
    def get_localized_field_description(self, field_name: str, locale: str = "en") -> str:
        """Get localized field description"""
        key = f"fields.{field_name}"
        if locale in self.locales and key in self.locales[locale]:
            return self.locales[locale][key]
        # Fallback to fields_schema description
        if field_name in self.fields_schema:
            return self.fields_schema[field_name].get("description", "")
        return ""
    
    def to_localized_dict(self, locale: str = "en") -> Dict[str, Any]:
        """Convert to dict with localized strings"""
        result = self.model_dump()
        result["display_name"] = self.get_localized_name(locale)
        result["display_description"] = self.get_localized_description(locale)
        
        # Translate field descriptions
        if self.fields_schema:
            for field_name in self.fields_schema:
                if "description" in result["fields_schema"][field_name]:
                    localized_desc = self.get_localized_field_description(field_name, locale)
                    if localized_desc:
                        result["fields_schema"][field_name]["description"] = localized_desc
        
        return result

    model_config = ConfigDict(use_enum_values=True)


class PluginRegistry:
    """
    플러그인 레지스트리

    커뮤니티 전략 플러그인을 등록하고 조회하는 레지스트리.
    AI 에이전트가 사용 가능한 플러그인 목록을 조회할 때 사용.
    """

    _instance: Optional["PluginRegistry"] = None
    _plugins: Dict[str, Dict[str, Any]] = {}  # {plugin_id: {version: callable}}
    _schemas: Dict[str, PluginSchema] = {}

    def __new__(cls) -> "PluginRegistry":
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
            cls._instance._schemas = {}
        return cls._instance

    def register(
        self,
        plugin_id: str,
        plugin_callable: Callable,
        schema: PluginSchema,
    ) -> None:
        """
        플러그인 등록

        Args:
            plugin_id: 플러그인 ID
            plugin_callable: 플러그인 실행 함수/클래스
            schema: 플러그인 스키마
        """
        version = schema.version

        if plugin_id not in self._plugins:
            self._plugins[plugin_id] = {}

        self._plugins[plugin_id][version] = plugin_callable
        self._schemas[f"{plugin_id}@{version}"] = schema

        # 최신 버전은 버전 없이도 접근 가능
        self._schemas[plugin_id] = schema

    def get(
        self,
        plugin_id: str,
        version: Optional[str] = None,
    ) -> Optional[Callable]:
        """
        플러그인 조회

        Args:
            plugin_id: 플러그인 ID (예: RSI, RSI@1.2.0)
            version: 버전 (생략 시 최신 버전)
        """
        # plugin_id에 @버전이 포함된 경우
        if "@" in plugin_id:
            plugin_id, version = plugin_id.split("@", 1)

        if plugin_id not in self._plugins:
            return None

        versions = self._plugins[plugin_id]

        if version:
            return versions.get(version)

        # 최신 버전 반환 (semantic versioning 정렬)
        if versions:
            latest = sorted(versions.keys(), reverse=True)[0]
            return versions[latest]

        return None

    def get_schema(
        self,
        plugin_id: str,
        version: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> Optional[PluginSchema]:
        """플러그인 스키마 조회
        
        Args:
            plugin_id: 플러그인 ID
            version: 버전 (생략 시 최신)
            locale: 번역 locale (ko, en 등)
        """
        if version:
            schema = self._schemas.get(f"{plugin_id}@{version}")
        else:
            schema = self._schemas.get(plugin_id)
        return schema

    def get_schema_localized(
        self,
        plugin_id: str,
        locale: str = "en",
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """플러그인 스키마를 번역된 dict로 조회"""
        schema = self.get_schema(plugin_id, version)
        if schema:
            return schema.to_localized_dict(locale)
        return None

    def list_plugins(
        self,
        category: Optional[PluginCategory] = None,
        product: Optional[ProductType] = None,
        locale: Optional[str] = None,
    ) -> List[Any]:
        """
        플러그인 목록 조회 (AI 에이전트용)

        Args:
            category: 카테고리 필터
            product: 상품 유형 필터 (BrokerNode.product로 자동 필터링)
            locale: 번역 locale (제공 시 dict 반환, 아니면 PluginSchema 반환)
        """
        result = []
        seen = set()  # 중복 제거 (버전별로 등록되므로)

        for key, schema in self._schemas.items():
            # @버전이 포함된 키는 건너뛰기 (중복 방지)
            if "@" in key:
                continue

            # 카테고리 필터
            if category and schema.category != category:
                continue

            # 상품 유형 필터
            if product and product not in schema.products:
                continue

            if schema.id not in seen:
                if locale:
                    result.append(schema.to_localized_dict(locale))
                else:
                    result.append(schema)
                seen.add(schema.id)

        return result

    def list_by_category(self) -> Dict[str, List[PluginSchema]]:
        """카테고리별 플러그인 목록"""
        result: Dict[str, List[PluginSchema]] = {}

        for category in PluginCategory:
            plugins = self.list_plugins(category=category)
            if plugins:
                result[category.value] = plugins

        return result

    def search(
        self,
        query: str,
        category: Optional[PluginCategory] = None,
    ) -> List[PluginSchema]:
        """
        플러그인 검색

        Args:
            query: 검색어 (ID, 이름, 설명, 태그에서 검색)
            category: 카테고리 필터
        """
        query_lower = query.lower()
        result = []

        for schema in self.list_plugins(category=category):
            # ID, 이름, 설명, 태그에서 검색
            searchable = " ".join([
                schema.id.lower(),
                (schema.name or "").lower(),
                (schema.description or "").lower(),
                " ".join(schema.tags).lower(),
            ])

            if query_lower in searchable:
                result.append(schema)

        return result
