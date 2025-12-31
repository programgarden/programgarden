"""
해외선물 종목 명세 관리자 (SymbolSpecManager)

o3121 API를 활용하여 종목별 Tick Size/Value를 동적으로 관리합니다.
- 첫 실행 시 로드
- 주기적 갱신 (기본 6시간)
"""

from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio


class SymbolSpec(BaseModel):
    """선물 종목 명세 (o3121 API 기반)"""
    
    symbol: str = Field(..., description="종목코드")
    """종목코드 (Symbol)"""
    
    symbol_name: str = Field(default="", description="종목명")
    """종목명 (SymbolNm)"""
    
    exchange_code: str = Field(default="", description="거래소코드")
    """거래소코드 (ExchCd)"""
    
    tick_size: Decimal = Field(..., description="호가단위가격 (Tick Size)")
    """호가단위가격 (UntPrc) = Tick Size"""
    
    tick_value: Decimal = Field(..., description="최소가격변동금액 (Tick Value)")
    """최소가격변동금액 (MnChgAmt) = Tick Value"""
    
    currency: str = Field(default="USD", description="기준통화코드")
    """기준통화코드 (CrncyCd)"""
    
    contract_amount: Decimal = Field(default=Decimal("0"), description="계약당금액")
    """계약당금액 (CtrtPrAmt)"""
    
    opening_margin: Decimal = Field(default=Decimal("0"), description="개시증거금")
    """개시증거금 (OpngMgn)"""
    
    maintenance_margin: Decimal = Field(default=Decimal("0"), description="유지증거금")
    """유지증거금 (MntncMgn)"""
    
    decimal_places: int = Field(default=2, description="유효소수점자리수")
    """유효소수점자리수 (DotGb)"""
    
    base_product_code: str = Field(default="", description="기초상품코드")
    """기초상품코드 (BscGdsCd)"""
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 갱신 시간")
    """마지막 갱신 시간"""


class SymbolSpecManager:
    """
    o3121 API를 활용한 해외선물 종목 명세 동적 관리
    
    - 첫 실행 시 로드
    - 주기적 갱신 (기본 6시간)
    """
    
    DEFAULT_REFRESH_HOURS = 6
    
    def __init__(self, market_client, refresh_hours: int = DEFAULT_REFRESH_HOURS):
        """
        Args:
            market_client: overseas_futureoption().market() 클라이언트
            refresh_hours: 갱신 주기 (시간, 기본 6시간)
        """
        self._market_client = market_client
        self._specs: Dict[str, SymbolSpec] = {}
        self._specs_by_base: Dict[str, List[str]] = {}  # 기초상품별 종목 그룹
        self._refresh_hours = refresh_hours
        self._last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """초기화 - 종목 명세 로드 및 주기적 갱신 시작"""
        await self._fetch_specs()
        self._refresh_task = asyncio.create_task(self._periodic_refresh())
        self._initialized = True
    
    async def _fetch_specs(self):
        """o3121 API로 종목 명세 조회"""
        async with self._lock:
            try:
                from ..market.o3121.blocks import O3121InBlock
                
                # 선물(F) 종목 조회
                tr = self._market_client.o3121(
                    body=O3121InBlock(MktGb="F", BscGdsCd="")
                )
                resp = await tr.req_async()
                
                if resp.rsp_cd == "00000" and resp.block:
                    self._specs.clear()
                    self._specs_by_base.clear()
                    
                    for item in resp.block:
                        spec = SymbolSpec(
                            symbol=item.Symbol,
                            symbol_name=item.SymbolNm,
                            exchange_code=item.ExchCd,
                            tick_size=Decimal(str(item.UntPrc)) if item.UntPrc else Decimal("0.01"),
                            tick_value=Decimal(str(item.MnChgAmt)) if item.MnChgAmt else Decimal("1"),
                            currency=item.CrncyCd or "USD",
                            contract_amount=Decimal(str(item.CtrtPrAmt)) if item.CtrtPrAmt else Decimal("0"),
                            opening_margin=Decimal(str(item.OpngMgn)) if item.OpngMgn else Decimal("0"),
                            maintenance_margin=Decimal(str(item.MntncMgn)) if item.MntncMgn else Decimal("0"),
                            decimal_places=item.DotGb or 2,
                            base_product_code=item.BscGdsCd or "",
                            last_updated=datetime.now()
                        )
                        self._specs[spec.symbol] = spec
                        
                        # 기초상품별 그룹화 (예: NQ -> [NQH25, NQM25, ...])
                        base_code = spec.base_product_code
                        if base_code:
                            if base_code not in self._specs_by_base:
                                self._specs_by_base[base_code] = []
                            self._specs_by_base[base_code].append(spec.symbol)
                    
                    self._last_refresh = datetime.now()
                    print(f"[SymbolSpecManager] {len(self._specs)}개 종목 로드 완료")
                else:
                    print(f"[SymbolSpecManager] o3121 조회 실패: {resp.rsp_msg}")
                    
            except Exception as e:
                print(f"[SymbolSpecManager] o3121 조회 예외: {e}")
    
    async def _periodic_refresh(self):
        """주기적 갱신"""
        while True:
            await asyncio.sleep(self._refresh_hours * 3600)
            await self._fetch_specs()
    
    def get_spec(self, symbol: str) -> Optional[SymbolSpec]:
        """
        종목 명세 조회
        
        Args:
            symbol: 종목코드
        
        Returns:
            SymbolSpec 또는 None
        """
        return self._specs.get(symbol)
    
    def get_spec_or_raise(self, symbol: str) -> SymbolSpec:
        """
        종목 명세 조회 (없으면 예외)
        
        Args:
            symbol: 종목코드
        
        Returns:
            SymbolSpec
        
        Raises:
            ValueError: 종목이 없는 경우
        """
        spec = self._specs.get(symbol)
        if not spec:
            available = list(self._specs.keys())[:10]
            raise ValueError(
                f"Symbol '{symbol}' not found. "
                f"Available (first 10): {available}... "
                f"Use manual_tick_size/manual_tick_value or call force_refresh()."
            )
        return spec
    
    def get_specs_by_base_product(self, base_code: str) -> List[str]:
        """
        기초상품 코드로 관련 종목들 조회
        
        Args:
            base_code: 기초상품코드 (예: "NQ")
        
        Returns:
            종목코드 목록 (예: ["NQH25", "NQM25"])
        """
        return self._specs_by_base.get(base_code, [])
    
    @property
    def available_symbols(self) -> List[str]:
        """사용 가능한 종목 목록"""
        return list(self._specs.keys())
    
    @property
    def available_base_products(self) -> List[str]:
        """사용 가능한 기초상품 코드 목록"""
        return list(self._specs_by_base.keys())
    
    @property
    def last_refresh_time(self) -> Optional[datetime]:
        """마지막 갱신 시간"""
        return self._last_refresh
    
    @property
    def spec_count(self) -> int:
        """로드된 종목 수"""
        return len(self._specs)
    
    @property
    def is_initialized(self) -> bool:
        """초기화 완료 여부"""
        return self._initialized
    
    async def force_refresh(self):
        """강제 갱신"""
        await self._fetch_specs()
    
    async def stop(self):
        """주기적 갱신 중지"""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
