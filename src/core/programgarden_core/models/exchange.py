"""
ProgramGarden Core - 거래소 코드 매핑

증권사별 거래소 코드와 사용자 친화적 이름 매핑을 정의합니다.
- 해외주식: NYSE, NASDAQ, AMEX 등
- 해외선물: CME, COMEX, NYMEX 등
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ProductType(str, Enum):
    """상품 타입"""
    OVERSEAS_STOCK = "overseas_stock"
    OVERSEAS_FUTURES = "overseas_futures"


class ExchangeInfo(BaseModel):
    """거래소 정보"""
    code: str = Field(..., description="API용 거래소 코드 (예: 81, 82, CME)")
    name: str = Field(..., description="사용자 친화적 이름 (예: NYSE, NASDAQ)")
    full_name: str = Field(default="", description="거래소 전체 이름")
    country: str = Field(default="US", description="국가 코드")
    currency: str = Field(default="USD", description="기본 통화")
    
    
class ExchangeRegistry:
    """
    증권사별 거래소 코드 레지스트리
    
    동적으로 거래소 목록을 로드/갱신할 수 있습니다.
    """
    
    def __init__(self):
        self._exchanges: Dict[str, Dict[str, ExchangeInfo]] = {}
        self._name_to_code: Dict[str, Dict[str, str]] = {}
        self._code_to_name: Dict[str, Dict[str, str]] = {}
        
        # 기본 LS증권 거래소 로드
        self._load_ls_exchanges()
    
    def _load_ls_exchanges(self):
        """LS증권 기본 거래소 매핑 로드"""
        
        # 해외주식 거래소
        ls_overseas_stock = {
            "NYSE": ExchangeInfo(
                code="81",
                name="NYSE",
                full_name="New York Stock Exchange",
                country="US",
                currency="USD"
            ),
            "AMEX": ExchangeInfo(
                code="81",  # NYSE와 동일 코드
                name="AMEX",
                full_name="American Stock Exchange",
                country="US",
                currency="USD"
            ),
            "NASDAQ": ExchangeInfo(
                code="82",
                name="NASDAQ",
                full_name="NASDAQ Stock Market",
                country="US",
                currency="USD"
            ),
        }
        
        # 해외선물 거래소 (문자열 코드 그대로 사용)
        ls_overseas_futures = {
            "CME": ExchangeInfo(
                code="CME",
                name="CME",
                full_name="Chicago Mercantile Exchange",
                country="US",
                currency="USD"
            ),
            "COMEX": ExchangeInfo(
                code="COMEX",
                name="COMEX",
                full_name="Commodity Exchange",
                country="US",
                currency="USD"
            ),
            "NYMEX": ExchangeInfo(
                code="NYMEX",
                name="NYMEX",
                full_name="New York Mercantile Exchange",
                country="US",
                currency="USD"
            ),
            "CBOT": ExchangeInfo(
                code="CBOT",
                name="CBOT",
                full_name="Chicago Board of Trade",
                country="US",
                currency="USD"
            ),
            "ICE": ExchangeInfo(
                code="ICE",
                name="ICE",
                full_name="Intercontinental Exchange",
                country="US",
                currency="USD"
            ),
        }
        
        self.register_exchanges("ls", ProductType.OVERSEAS_STOCK, ls_overseas_stock)
        self.register_exchanges("ls", ProductType.OVERSEAS_FUTURES, ls_overseas_futures)
    
    def register_exchanges(
        self, 
        broker: str, 
        product: ProductType, 
        exchanges: Dict[str, ExchangeInfo]
    ):
        """거래소 목록 등록"""
        key = f"{broker}:{product.value}"
        self._exchanges[key] = exchanges
        
        # 이름 <-> 코드 매핑 빌드
        self._name_to_code[key] = {name: info.code for name, info in exchanges.items()}
        self._code_to_name[key] = {info.code: name for name, info in exchanges.items()}
    
    def get_exchanges(
        self, 
        broker: str, 
        product: ProductType
    ) -> Dict[str, ExchangeInfo]:
        """거래소 목록 조회"""
        key = f"{broker}:{product.value}"
        return self._exchanges.get(key, {})
    
    def get_exchange_list(
        self, 
        broker: str, 
        product: ProductType
    ) -> List[str]:
        """거래소 이름 목록 조회"""
        return list(self.get_exchanges(broker, product).keys())
    
    def name_to_code(
        self, 
        broker: str, 
        product: ProductType, 
        name: str
    ) -> Optional[str]:
        """거래소 이름 → API 코드 변환"""
        key = f"{broker}:{product.value}"
        mapping = self._name_to_code.get(key, {})
        return mapping.get(name.upper())
    
    def code_to_name(
        self, 
        broker: str, 
        product: ProductType, 
        code: str
    ) -> Optional[str]:
        """API 코드 → 거래소 이름 변환"""
        key = f"{broker}:{product.value}"
        mapping = self._code_to_name.get(key, {})
        return mapping.get(code)
    
    def get_default_exchange(
        self, 
        broker: str, 
        product: ProductType
    ) -> Optional[str]:
        """상품 타입별 기본 거래소"""
        exchanges = self.get_exchange_list(broker, product)
        if not exchanges:
            return None
        
        # 해외주식: NASDAQ 기본
        if product == ProductType.OVERSEAS_STOCK:
            return "NASDAQ" if "NASDAQ" in exchanges else exchanges[0]
        
        # 해외선물: CME 기본
        if product == ProductType.OVERSEAS_FUTURES:
            return "CME" if "CME" in exchanges else exchanges[0]
        
        return exchanges[0]


# 글로벌 레지스트리 인스턴스
exchange_registry = ExchangeRegistry()


class SymbolEntry(BaseModel):
    """
    종목 엔트리 (거래소 + 종목코드)
    
    사용자는 거래소 이름(NYSE, NASDAQ)으로 입력하고,
    실행 시점에 API 코드(81, 82)로 변환됩니다.
    """
    exchange: str = Field(..., description="거래소 이름 (NYSE, NASDAQ, CME 등)")
    symbol: str = Field(..., description="종목코드 (AAPL, NVDA, NQH25 등)")
    
    def to_api_symbol(self, broker: str, product: ProductType) -> str:
        """API용 종목코드 생성 (예: 82AAPL)"""
        code = exchange_registry.name_to_code(broker, product, self.exchange)
        if code is None:
            raise ValueError(f"Unknown exchange: {self.exchange}")
        
        # 해외주식: 코드+심볼 (예: 82AAPL)
        if product == ProductType.OVERSEAS_STOCK:
            return f"{code}{self.symbol}"
        
        # 해외선물: 심볼만 (거래소는 별도 필드)
        return self.symbol
    
    def get_exchange_code(self, broker: str, product: ProductType) -> str:
        """API용 거래소 코드 반환"""
        code = exchange_registry.name_to_code(broker, product, self.exchange)
        if code is None:
            raise ValueError(f"Unknown exchange: {self.exchange}")
        return code
