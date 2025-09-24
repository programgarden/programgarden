"""
LS Securities symbol provider integration.

This module implements a small adapter around the LS (LS증권) finance
client to fetch available symbols for a given product. The adapter exposes
a single async provider class that external developers can call to retrieve
a list of `SymbolInfo` records.

High level behaviour
- Supports only company == "ls".
- Requires the underlying LS client to be logged in; this function will
        raise a ValueError if the client is not authenticated.
- Uses the LS client's async occurs-style API to receive result blocks and
        converts them into `SymbolInfo` instances.

Example
                provider = SymbolProvider()
                symbols = await provider.get_symbols(company="ls", product="overseas_stock")
                for s in symbols:
                                print(s.symbol, s.exchcd)

"""

from typing import List, Optional

from programgarden_core import SymbolInfo, pg_logger, SecuritiesAccountType
from programgarden_finance import LS, g3190, COSOQ00201, g3104
from datetime import date


class SymbolProvider:
    async def get_symbols(
        self,
        buy: Optional[bool],
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
            if buy is True or buy is None:
                symbols.extend(await self.get_market_symbols(ls))

            elif buy is False:
                symbols.extend(await self.get_account_symbols(ls))

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
