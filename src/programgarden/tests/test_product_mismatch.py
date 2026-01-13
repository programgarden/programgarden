"""
Product mismatch test for RealMarketDataNodeExecutor

BrokerNode(overseas_futures) + WatchlistNode(overseas_stock) → Error
"""
import asyncio
import pytest
from programgarden.context import ExecutionContext
from programgarden.executor import RealMarketDataNodeExecutor
from programgarden_core.exceptions import ValidationError


class TestProductMismatch:
    """BrokerNode ↔ WatchlistNode product 불일치 검증 테스트"""

    def _create_context(self, broker_product: str, watchlist_product: str) -> ExecutionContext:
        """테스트용 context 생성"""
        edges = [
            {"from": "broker", "to": "realMarket"},
            {"from": "watchlist", "to": "realMarket"},
        ]
        nodes = {
            "broker": {"type": "BrokerNode"},
            "watchlist": {"type": "WatchlistNode"},
            "realMarket": {"type": "RealMarketDataNode"},
        }
        
        ctx = ExecutionContext(
            job_id="test-job",
            workflow_id="test-workflow",
            workflow_edges=edges,
            workflow_nodes=nodes,
        )
        
        # BrokerNode 출력 설정
        ctx.set_output("broker", "product", broker_product)
        ctx.set_output("broker", "connection", {"provider": "ls-sec.co.kr", "product": broker_product})
        
        # WatchlistNode 출력 설정
        ctx.set_output("watchlist", "product", watchlist_product)
        ctx.set_output("watchlist", "symbols", [{"exchange": "NASDAQ", "symbol": "AAPL"}])
        
        # RealMarketDataNode 입력으로 connection, symbols 설정 (실행 시 WorkflowExecutor가 엣지를 통해 주입함)
        ctx.set_output("_input_realMarket", "connection", {"provider": "ls-sec.co.kr", "product": broker_product})
        ctx.set_output("_input_realMarket", "symbols", [{"exchange": "NASDAQ", "symbol": "AAPL"}])
        ctx.set_output("_input_realMarket", "product", watchlist_product)  # watchlist의 product
        
        return ctx

    @pytest.mark.asyncio
    async def test_product_mismatch_raises_error(self):
        """overseas_futures vs overseas_stock 불일치 시 에러 발생"""
        ctx = self._create_context("overseas_futures", "overseas_stock")
        executor = RealMarketDataNodeExecutor()
        
        with pytest.raises(ValidationError) as exc_info:
            await executor.execute("realMarket", "RealMarketDataNode", {}, ctx)
        
        assert "Product mismatch" in str(exc_info.value)
        assert "overseas_futures" in str(exc_info.value)
        assert "overseas_stock" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_same_product_no_error(self):
        """같은 product면 에러 없이 정상 동작"""
        ctx = self._create_context("overseas_stock", "overseas_stock")
        executor = RealMarketDataNodeExecutor()
        
        # 에러 없이 실행되어야 함
        result = await executor.execute("realMarket", "RealMarketDataNode", {}, ctx)
        
        assert "price" in result
        assert "AAPL" in result["price"]

    @pytest.mark.asyncio
    async def test_futures_product_match(self):
        """overseas_futures 동일하면 정상 동작"""
        ctx = self._create_context("overseas_futures", "overseas_futures")
        executor = RealMarketDataNodeExecutor()
        
        result = await executor.execute("realMarket", "RealMarketDataNode", {}, ctx)
        
        assert "price" in result


if __name__ == "__main__":
    # 직접 실행 테스트
    async def main():
        test = TestProductMismatch()
        
        print("Test 1: Product mismatch should raise error...")
        ctx = test._create_context("overseas_futures", "overseas_stock")
        executor = RealMarketDataNodeExecutor()
        
        try:
            await executor.execute("realMarket", "RealMarketDataNode", {}, ctx)
            print("❌ FAIL: Should have raised an error")
        except ValidationError as e:
            print(f"✅ PASS: {e}")
        
        print("\nTest 2: Same product should work...")
        ctx = test._create_context("overseas_stock", "overseas_stock")
        try:
            result = await executor.execute("realMarket", "RealMarketDataNode", {}, ctx)
            print(f"✅ PASS: {result.get('price', {})}")
        except Exception as e:
            print(f"❌ FAIL: {e}")
    
    asyncio.run(main())
