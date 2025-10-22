"""
LS Securities symbol provider integration.

This module implements a small adapter around the LS (LS증권) finance
client to fetch available symbols for a given product. The adapter exposes
a single async provider class that external developers can call to retrieve
a list of `SymbolInfo` records.
"""

from typing import List, Optional, Union

from programgarden_core import (
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType,
    pg_logger,
    SecuritiesAccountType,
)
from programgarden_finance import LS, g3190, COSOQ00201, g3104, COSAQ00102, o3101
from datetime import date, datetime
import pytz


class SymbolProvider:
    async def get_symbols(
        self,
        order_type: Optional[OrderType],
        securities: SecuritiesAccountType
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """
        Retrieve a list of symbols for the requested company and product.
        """

        company = securities.get("company", "ls")
        product = securities.get("product", "overseas_stock")

        if company != "ls":
            return []

        ls = LS.get_instance()
        if not ls.is_logged_in():
            return []

        symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        if product == "overseas_stock":
            if order_type == "new_buy" or order_type is None:
                symbols.extend(await self.get_market_symbols(ls))
            elif order_type == "new_sell":
                symbols.extend(await self.get_account_symbols(ls))

            elif order_type in ["modify_buy", "modify_sell", "cancel_buy", "cancel_sell"]:
                symbols.extend(await self.get_non_trade_symbols(ls))

        elif product == "overseas_futures":
            if order_type in ("new_buy", "new_sell", None):
                symbols.extend(await self.get_future_market_symbols(ls))
            elif order_type in ["modify_buy", "modify_sell", "cancel_buy", "cancel_sell"]:
                symbols.extend(await self.get_future_pending_orders(ls))

        else:
            pg_logger.warning(f"Unsupported product: {product}")

        return symbols

    async def get_account_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve account symbols for overseas stocks."""
        tmp: List[SymbolInfoOverseasStock] = []
        response = await ls.overseas_stock().accno().cosoq00201(
                    COSOQ00201.COSOQ00201InBlock1(
                        RecCnt=1,
                        BaseDt=date.today().strftime("%Y%m%d"),
                        CrcyCode="ALL",
                        AstkBalTpCode="00"
                    )
                ).req_async()

        for block in response.block4:

            result = await ls.overseas_stock().market().g3104(
                body=g3104.G3104InBlock(
                    keysymbol=block.FcurrMktCode+block.ShtnIsuNo.strip(),
                    exchcd=block.FcurrMktCode,
                    symbol=block.ShtnIsuNo.strip()
                )
            ).req_async()

            if not result:
                continue

            tmp.append(
                SymbolInfoOverseasStock(
                    symbol=block.ShtnIsuNo.strip(),
                    exchcd=block.FcurrMktCode,
                    mcap=result.block.shareprc,
                    product_type="overseas_stock",
                )
            )

        return tmp

    async def get_market_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve buy symbols for overseas stocks."""
        overseas_stock = ls.overseas_stock()
        tmp: List[SymbolInfoOverseasStock] = []

        await overseas_stock.market().g3190(
                                body=g3190.G3190InBlock(
                                                delaygb="R",
                                                natcode="US",
                                                exgubun="2",
                                                readcnt=500,
                                                cts_value="",
                                )
                ).occurs_req_async(
                                callback=lambda response, _: tmp.extend(
                                                SymbolInfoOverseasStock(
                                                    symbol=block.symbol.strip(),
                                                    exchcd=block.exchcd,
                                                    mcap=block.share*block.clos,
                                                    product_type="overseas_stock",
                                                )
                                                for block in response.block1
                                ) if response and hasattr(response, "block1") and response.block1 else None
                )

        return tmp

    async def get_non_trade_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve non-trade symbols for overseas stocks."""
        tmp: List[SymbolInfoOverseasStock] = []

        ny_tz = pytz.timezone("America/New_York")
        ny_time = datetime.now(ny_tz)

        for exchcd in ["81", "82"]:
            response = await ls.overseas_stock().accno().cosaq00102(
                        COSAQ00102.COSAQ00102InBlock1(
                            RecCnt=1,
                            QryTpCode="1",
                            BkseqTpCode="1",
                            OrdMktCode=exchcd,
                            BnsTpCode="0",
                            IsuNo="",
                            SrtOrdNo=999999999,
                            OrdDt=ny_time.strftime("%Y%m%d"),
                            ExecYn="2",
                            CrcyCode="USD",
                            ThdayBnsAppYn="0",
                            LoanBalHldYn="0"
                        )
                    ).req_async()

            for block in response.block3:
                result = await ls.overseas_stock().market().g3104(
                    body=g3104.G3104InBlock(
                        keysymbol=block.OrdMktCode+block.ShtnIsuNo.strip(),
                        exchcd=block.OrdMktCode,
                        symbol=block.ShtnIsuNo.strip()
                    )
                ).req_async()

                if not result:
                    continue

                tmp.append(
                    SymbolInfoOverseasStock(
                        symbol=block.ShtnIsuNo.strip(),
                        exchcd=block.OrdMktCode,
                        mcap=result.block.shareprc,
                        OrdNo=block.OrdNo,
                        product_type="overseas_stock",
                    )
                )

        return tmp

    async def get_future_market_symbols(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """Retrieve tradable overseas futures symbols."""

        tmp: List[SymbolInfoOverseasFutures] = []

        response = await ls.overseas_futureoption().market().o3101(
            body=o3101.O3101InBlock(
                gubun="1"
            )
        ).req_async()

        if not response or not getattr(response, "block", None):
            return tmp

        for block in response.block:
            try:
                symbol_code = block.Symbol.strip()
            except AttributeError:
                symbol_code = block.Symbol

            symbol_info: SymbolInfoOverseasFutures = SymbolInfoOverseasFutures(
                symbol=symbol_code,
                exchcd=(block.ExchCd or "").strip(),
                product_type="overseas_futures",
            )

            if getattr(block, "SymbolNm", None):
                symbol_info["symbol_name"] = block.SymbolNm.strip()

            year = (block.LstngYr or "").strip()
            month = (block.LstngM or "").strip()
            due = f"{year}{month}" if year or month else ""
            if due:
                symbol_info["due_yymm"] = due

            if getattr(block, "GdsCd", None):
                symbol_info["prdt_code"] = block.GdsCd.strip()

            if getattr(block, "CrncyCd", None):
                symbol_info["currency_code"] = block.CrncyCd.strip()

            try:
                contract_size = float(block.CtrtPrAmt)
                symbol_info["contract_size"] = contract_size
            except (TypeError, ValueError):
                pass

            symbol_info["additional"] = {
                "unit_price": getattr(block, "UntPrc", None),
                "min_change_amount": getattr(block, "MnChgAmt", None),
                "maintenance_margin": getattr(block, "MntncMgn", None),
                "opening_margin": getattr(block, "OpngMgn", None),
            }

            tmp.append(symbol_info)

        return tmp

    async def get_future_pending_orders(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """Placeholder for future pending order retrieval.

        현재는 미체결/정정 대상 종목을 별도로 조회하지 않고 빈 값을 반환합니다.
        커뮤니티 플러그인 또는 전략에서 필요한 경우 직접 조회를 수행해야 합니다.
        """

        return []
