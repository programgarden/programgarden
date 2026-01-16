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
            "SGX": ExchangeInfo(
                code="SGX",
                name="SGX",
                full_name="Singapore Exchange",
                country="SG",
                currency="USD"
            ),
            "EUREX": ExchangeInfo(
                code="EUREX",
                name="EUREX",
                full_name="Eurex Exchange",
                country="DE",
                currency="EUR"
            ),
            "HKEX": ExchangeInfo(
                code="HKEX",
                name="HKEX",
                full_name="Hong Kong Exchanges",
                country="HK",
                currency="HKD"
            ),
            "OSE": ExchangeInfo(
                code="OSE",
                name="OSE",
                full_name="Osaka Exchange",
                country="JP",
                currency="JPY"
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
    
    def to_dict(self) -> dict:
        """dict 형태로 변환 (JSON 직렬화용)"""
        return {"exchange": self.exchange, "symbol": self.symbol}
    
    @classmethod
    def from_any(cls, value: any) -> "SymbolEntry":
        """
        다양한 형식에서 SymbolEntry로 변환
        
        Args:
            value: 다음 형식 중 하나
                - SymbolEntry 인스턴스
                - {"exchange": "NASDAQ", "symbol": "AAPL"}
                - "AAPL" (문자열 - 기본 거래소 추정)
                
        Returns:
            SymbolEntry 인스턴스
        """
        if isinstance(value, SymbolEntry):
            return value
        
        if isinstance(value, dict):
            exchange = value.get("exchange")
            symbol = value.get("symbol")
            
            if not symbol:
                raise ValueError(f"Symbol is required: {value}")
            
            if not exchange:
                # 거래소 없으면 추정 시도
                exchange = _guess_exchange(symbol)
            
            return cls(exchange=exchange, symbol=symbol)
        
        if isinstance(value, str):
            # 문자열인 경우 거래소 추정
            exchange = _guess_exchange(value)
            return cls(exchange=exchange, symbol=value)
        
        raise ValueError(f"Cannot convert to SymbolEntry: {type(value).__name__} = {value}")


def _guess_exchange(symbol: str) -> str:
    """
    종목코드로 거래소 추정 (fallback용)
    
    주의: 정확하지 않을 수 있으므로 명시적 거래소 지정 권장
    """
    # 해외선물 패턴 (예: NQH25, ESZ24, GCG25)
    import re
    if re.match(r"^[A-Z]{2,4}[FGHJKMNQUVXZ]\d{2}$", symbol.upper()):
        # 선물 심볼 패턴: 2-4글자 + 월코드(1글자) + 연도(2자리)
        prefix = symbol[:2].upper()
        # 주요 선물 거래소 추정
        if prefix in ("NQ", "ES", "MNQ", "MES", "RTY"):
            return "CME"
        elif prefix in ("GC", "SI", "HG"):
            return "COMEX"
        elif prefix in ("CL", "NG"):
            return "NYMEX"
        return "CME"  # 기본값
    
    # 해외주식은 기본 NASDAQ (미국 주식 다수)
    return "NASDAQ"


def normalize_symbol(value: any) -> SymbolEntry:
    """
    다양한 형식을 SymbolEntry로 정규화
    
    Args:
        value: SymbolEntry, dict, 또는 str
        
    Returns:
        SymbolEntry 인스턴스
    """
    return SymbolEntry.from_any(value)


def normalize_symbols(values: list) -> list:
    """
    종목 리스트를 SymbolEntry 리스트로 정규화
    
    Args:
        values: 다양한 형식의 종목 리스트
        
    Returns:
        SymbolEntry 인스턴스 리스트
    """
    if not values:
        return []
    
    result = []
    for v in values:
        try:
            entry = normalize_symbol(v)
            result.append(entry)
        except ValueError as e:
            # 변환 실패한 항목은 경고 후 스킵
            import logging
            logging.warning(f"Failed to normalize symbol: {v} - {e}")
    
    return result


def symbols_to_dict_list(symbols: list) -> list:
    """
    SymbolEntry 리스트를 dict 리스트로 변환 (JSON 직렬화용)
    
    Args:
        symbols: SymbolEntry 또는 dict 리스트
        
    Returns:
        [{"exchange": "NASDAQ", "symbol": "AAPL"}, ...] 형태
    """
    result = []
    for s in symbols:
        if isinstance(s, SymbolEntry):
            result.append(s.to_dict())
        elif isinstance(s, dict):
            # 이미 dict면 exchange 포함 여부 확인
            if "exchange" in s and "symbol" in s:
                result.append({"exchange": s["exchange"], "symbol": s["symbol"]})
            elif "symbol" in s:
                # exchange 없으면 추정
                sym = s["symbol"]
                exchange = _guess_exchange(sym)
                result.append({"exchange": exchange, "symbol": sym})
        elif isinstance(s, str):
            # 문자열이면 거래소 추정
            exchange = _guess_exchange(s)
            result.append({"exchange": exchange, "symbol": s})
    
    return result


def extract_symbol_codes(symbols: list) -> list:
    """
    종목 리스트에서 종목코드만 추출 (하위호환용)
    
    Args:
        symbols: SymbolEntry, dict, 또는 str 리스트
        
    Returns:
        ["AAPL", "TSLA", ...] 형태의 문자열 리스트
    """
    result = []
    for s in symbols:
        if isinstance(s, SymbolEntry):
            result.append(s.symbol)
        elif isinstance(s, dict):
            result.append(s.get("symbol", str(s)))
        elif isinstance(s, str):
            result.append(s)
    return result
