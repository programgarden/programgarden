"""
LS Securities symbol provider integration.

This module implements a small adapter around the LS (LS증권) finance
client to fetch available symbols for a given product. The adapter exposes
a single async provider class that external developers can call to retrieve
a list of `SymbolInfo` records.
"""

from typing import List, Optional

from programgarden_core import SymbolInfo, OrderType, pg_logger, SecuritiesAccountType
from programgarden_finance import LS, g3190, COSOQ00201, g3104, COSAQ00102
from datetime import date, datetime
import pytz


class SymbolProvider:
    async def get_symbols(
        self,
        order_type: Optional[OrderType],
        securities: SecuritiesAccountType
    ) -> List[SymbolInfo]:
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

        symbols: List[SymbolInfo] = []
        if product == "overseas_stock":
            if order_type == "new_buy" or order_type is None:
                symbols.extend(await self.get_market_symbols(ls))
            elif order_type == "new_sell":
                symbols.extend(await self.get_account_symbols(ls))

            elif order_type in ["modify_buy", "modify_sell", "cancel_buy", "cancel_sell"]:
                symbols.extend(await self.get_non_trade_symbols(ls))

        else:
            pg_logger.warning(f"Unsupported product: {product}")

        return symbols

    async def get_account_symbols(self, ls: LS) -> List[SymbolInfo]:
        """Retrieve account symbols for overseas stocks."""
        tmp: List[SymbolInfo] = []
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
                SymbolInfo(
                    symbol=block.ShtnIsuNo.strip(),
                    exchcd=block.FcurrMktCode,
                    mcap=result.block.shareprc
                )
            )

        return tmp

    async def get_market_symbols(self, ls: LS) -> List[SymbolInfo]:
        """Retrieve buy symbols for overseas stocks."""
        overseas_stock = ls.overseas_stock()
        tmp: List[SymbolInfo] = []

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
                                                SymbolInfo(
                                                    symbol=block.symbol.strip(),
                                                    exchcd=block.exchcd,
                                                    mcap=block.share*block.clos,
                                                )
                                                for block in response.block1
                                ) if response and hasattr(response, "block1") and response.block1 else None
                )

        return tmp

    async def get_non_trade_symbols(self, ls: LS) -> List[SymbolInfo]:
        """Retrieve non-trade symbols for overseas stocks."""
        tmp: List[SymbolInfo] = []

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
                    SymbolInfo(
                        symbol=block.ShtnIsuNo.strip(),
                        exchcd=block.OrdMktCode,
                        mcap=result.block.shareprc,
                        OrdNo=block.OrdNo
                    )
                )

        return tmp
