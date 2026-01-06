"""
ProgramGarden - WorkflowExecutor

Workflow execution engine
- validate() → compile() → execute() lifecycle
- Stateful long-running execution support
- Graceful Restart support
"""

from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime
import asyncio
import uuid

from programgarden.resolver import WorkflowResolver, ResolvedWorkflow, ValidationResult
from programgarden.context import ExecutionContext
from programgarden_core.expression import ExpressionEvaluator, ExpressionContext


class NodeExecutorBase:
    """Node executor base class"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """
        Execute node

        Returns:
            Dictionary of output port values
        """
        raise NotImplementedError


class StartNodeExecutor(NodeExecutorBase):
    """StartNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        context.log("info", "Workflow started", node_id)
        return {"start": True}


class ScheduleNodeExecutor(NodeExecutorBase):
    """ScheduleNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        # Schedule trigger (uses cron scheduler in actual implementation)
        cron = config.get("cron", "*/5 * * * *")
        context.log("info", f"Schedule triggered: {cron}", node_id)
        return {"trigger": True}


class WatchlistNodeExecutor(NodeExecutorBase):
    """WatchlistNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        symbols = config.get("symbols", [])
        context.log("info", f"Watchlist symbols: {symbols}", node_id)
        return {"symbols": symbols}


class BrokerNodeExecutor(NodeExecutorBase):
    """BrokerNode executor"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        provider = config.get("provider", "ls-sec.co.kr")
        product = config.get("product", "overseas_stock")
        context.log("info", f"Broker connected: {provider} ({product})", node_id)
        return {"connection": {"provider": provider, "product": product}}


class RealAccountNodeExecutor(NodeExecutorBase):
    """RealAccountNode executor - 실시간 계좌 정보 (브로커별 분기 처리)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        # BrokerNode에서 설정된 provider/product 정보 가져오기
        broker_connection = context.get_output("broker", "connection") or {}
        provider = broker_connection.get("provider", "ls-sec.co.kr")
        product = broker_connection.get("product", "overseas_stock")
        
        context.log("info", f"RealAccount: provider={provider}, product={product}", node_id)
        
        # ========================================
        # 브로커별 분기 처리
        # - 새 브로커 추가 시 여기에 elif 분기 추가
        # - 예: elif provider == "kiwoom": return await self._execute_kiwoom(...)
        # ========================================
        if provider == "ls-sec.co.kr":
            return await self._execute_ls(node_id, product, config, context)
        else:
            context.log("error", f"Unsupported provider: {provider}", node_id)
            return self._empty_result(f"Unsupported provider: {provider}")

    async def _execute_ls(
        self,
        node_id: str,
        product: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """LS증권 계좌 조회"""
        from datetime import datetime
        
        # secrets에서 인증 정보 가져오기
        credential = context.get_credential()
        if not credential:
            context.log("error", "Credential not found in secrets", node_id)
            return self._empty_result("Missing credentials")
        
        appkey = credential.get("appkey")
        appsecret = credential.get("appsecret")
        paper_trading = credential.get("paper_trading", False)
        
        if not appkey or not appsecret:
            context.log("error", "appkey/appsecret not found in credential", node_id)
            return self._empty_result("Missing appkey/appsecret")
        
        try:
            from programgarden_finance import LS
            from programgarden_finance.ls.models import SetupOptions
            
            ls = LS.get_instance()
            
            if not ls.is_logged_in():
                login_result = ls.login(
                    appkey=appkey,
                    appsecretkey=appsecret,
                    paper_trading=paper_trading,
                )
                if not login_result:
                    context.log("error", "LS login failed", node_id)
                    return self._empty_result("Login failed")
                context.log("info", f"LS logged in (paper_trading={paper_trading})", node_id)
            
            # ========================================
            # LS 상품별 분기 처리
            # - 새 상품 추가 시 여기에 elif 분기 추가
            # ========================================
            if product == "overseas_stock":
                return await self._ls_overseas_stock(ls, node_id, context)
            elif product == "domestic_stock":
                return await self._ls_domestic_stock(ls, node_id, context)
            elif product == "overseas_futureoption":
                return await self._ls_overseas_futureoption(ls, node_id, context)
            else:
                context.log("warning", f"Unsupported LS product: {product}, using overseas_stock", node_id)
                return await self._ls_overseas_stock(ls, node_id, context)
                
        except ImportError as e:
            context.log("error", f"finance package not available: {e}", node_id)
            return self._empty_result(f"finance package error: {e}")
        except Exception as e:
            context.log("error", f"Unexpected error: {e}", node_id)
            return self._empty_result(str(e))

    async def _ls_overseas_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """LS증권 해외주식 잔고 조회 (COSOQ00201)"""
        from datetime import datetime
        from programgarden_finance import COSOQ00201
        from programgarden_finance.ls.models import SetupOptions
        
        today = datetime.now().strftime("%Y%m%d")
        cosoq00201 = ls.overseas_stock().accno().cosoq00201(
            COSOQ00201.COSOQ00201InBlock1(
                RecCnt=1,
                BaseDt=today,
                CrcyCode="ALL",
                AstkBalTpCode="00",
            ),
            options=SetupOptions(on_rate_limit="wait"),
        )
        
        response = await cosoq00201.req_async()
        
        if response.error_msg:
            context.log("error", f"API error: {response.error_msg}", node_id)
            return self._empty_result(response.error_msg)
        
        # block4 = 종목별 잔고 상세
        positions = {}
        for item in response.block4 or []:
            symbol = item.ShtnIsuNo.strip()
            if not symbol:
                continue
            
            positions[symbol] = {
                "symbol": symbol,
                "name": item.JpnMktHanglIsuNm.strip() if item.JpnMktHanglIsuNm else symbol,
                "qty": item.AstkBalQty,
                "avg_price": item.FcstckUprc,
                "current_price": item.OvrsScrtsCurpri,
                "pnl_rate": item.PnlRat,
                "pnl_amount": item.FcurrEvalPnlAmt,
                "currency": item.CrcyCode,
                "market": item.MktTpNm.strip() if item.MktTpNm else "",
                "eval_amount": item.FcurrEvalAmt,
                "purchase_amount": item.FcurrBuyAmt,
            }
        
        held_symbols = list(positions.keys())
        
        # block2 = 전체 평가 요약
        balance_info = {"cash": 0.0, "total_value": 0.0}
        if response.block2:
            balance_info = {
                "total_pnl_rate": response.block2.ErnRat,
                "cash_krw": response.block2.WonDpsBalAmt,
                "stock_eval_krw": response.block2.StkConvEvalAmt,
                "total_eval_krw": response.block2.WonEvalSumAmt,
                "total_pnl_krw": response.block2.ConvEvalPnlAmt,
            }
        
        context.log("info", f"LS overseas_stock: {len(held_symbols)} positions", node_id)
        return {
            "held_symbols": held_symbols,
            "positions": positions,
            "balance": balance_info,
        }

    async def _ls_domestic_stock(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """LS증권 국내주식 잔고 조회 (TODO: 구현 필요)"""
        context.log("warning", "LS domestic_stock not yet implemented, returning empty", node_id)
        return self._empty_result("domestic_stock not implemented")

    async def _ls_overseas_futureoption(self, ls, node_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """LS증권 해외선물옵션 잔고 조회 (TODO: 구현 필요)"""
        context.log("warning", "LS overseas_futureoption not yet implemented, returning empty", node_id)
        return self._empty_result("overseas_futureoption not implemented")

    def _empty_result(self, error: str = "") -> Dict[str, Any]:
        """빈 결과 반환"""
        result = {
            "held_symbols": [],
            "positions": {},
            "balance": {"cash": 0.0, "total_value": 0.0},
        }
        if error:
            result["error"] = error
        return result


class RealMarketDataNodeExecutor(NodeExecutorBase):
    """RealMarketDataNode executor - 실시간 시세"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        import random
        
        # 입력에서 symbols 가져오기
        symbols = context.get_output("_input_" + node_id, "symbols") or []
        if not symbols:
            symbols = context.get_output("account", "held_symbols") or []
        
        # TODO: 실제 구현에서는 WebSocket 시세 수신
        # 현재는 약간의 변동을 주는 목업 데이터
        prices = {}
        base_prices = {"NVDA": 875.30, "AAPL": 192.30, "TSLA": 248.90}
        
        for symbol in symbols:
            base = base_prices.get(symbol, 100.0)
            # ±0.5% 랜덤 변동
            variation = base * random.uniform(-0.005, 0.005)
            prices[symbol] = round(base + variation, 2)
        
        context.log("info", f"Market data received: {symbols}", node_id)
        return {"price": prices, "volume": {}, "bid": {}, "ask": {}}


class CustomPnLNodeExecutor(NodeExecutorBase):
    """CustomPnLNode executor - 커스텀 수익률 계산 (고급 사용자용)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        # 입력 데이터 가져오기
        positions = context.get_output("account", "positions") or {}
        current_prices = context.get_output("realMarket", "price") or {}
        
        # 커스텀 설정
        custom_commission = config.get("commission_rate", 0.0025)  # 기본 0.25%
        include_commission = config.get("include_commission", True)
        
        position_pnl = {}
        total_pnl_amount = 0.0
        
        for symbol, pos in positions.items():
            current_price = current_prices.get(symbol, pos.get("current_price", 0))
            avg_price = pos.get("avg_price", 0)
            qty = pos.get("qty", 0)
            
            if avg_price > 0:
                pnl_rate = ((current_price - avg_price) / avg_price) * 100
                pnl_amount = (current_price - avg_price) * qty
                
                # 커스텀 수수료 적용
                if include_commission:
                    commission = (avg_price * qty + current_price * qty) * custom_commission
                    pnl_amount -= commission
            else:
                pnl_rate = 0.0
                pnl_amount = 0.0
            
            position_pnl[symbol] = {
                "symbol": symbol,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "pnl_rate": round(pnl_rate, 2),
                "pnl_amount": round(pnl_amount, 2),
            }
            total_pnl_amount += pnl_amount
        
        context.log("info", f"Custom PnL calculated: {len(position_pnl)} positions", node_id)
        return {
            "position_pnl": position_pnl,
            "daily_pnl": round(total_pnl_amount, 2),
            "summary": {"total_positions": len(position_pnl), "total_pnl": total_pnl_amount},
        }


class DisplayNodeExecutor(NodeExecutorBase):
    """DisplayNode executor - 테이블/차트 표시"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        from datetime import datetime
        
        # 입력 데이터 가져오기 (account.positions 또는 customPnl.position_pnl)
        data = context.get_output("account", "positions") or {}
        if not data:
            data = context.get_output("customPnl", "position_pnl") or {}
        
        # balance 정보도 가져오기
        balance = context.get_output("account", "balance") or {}
        
        chart_type = config.get("chart_type", "table")
        title = config.get("title", "")
        options = config.get("options", {})
        
        if chart_type == "table" and data:
            # 테이블 출력
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{title} [{now}]")
            print("=" * 100)
            print(f"{'Symbol':<10} {'Name':<15} {'Qty':>10} {'Avg Price':>12} {'Cur Price':>12} {'PnL Rate':>10} {'PnL Amount':>14}")
            print("-" * 100)
            
            # 정렬
            sort_by = options.get("sort_by", "symbol")
            sort_order = options.get("sort_order", "asc")
            sorted_data = sorted(
                data.values(),
                key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by, 0), (int, float)) else str(x.get(sort_by, "")),
                reverse=(sort_order == "desc"),
            )
            
            for row in sorted_data:
                pnl_rate = row.get("pnl_rate", 0)
                pnl_amount = row.get("pnl_amount", 0)
                pnl_sign = "+" if pnl_rate >= 0 else ""
                pnl_color = "\033[92m" if pnl_rate >= 0 else "\033[91m"  # Green/Red
                reset = "\033[0m"
                
                currency = row.get("currency", "USD")
                currency_symbol = "$" if currency == "USD" else currency + " "
                
                # qty가 float인 경우 (소수점 주식)
                qty = row.get("qty", 0)
                qty_str = f"{qty:>10.4f}" if isinstance(qty, float) and qty != int(qty) else f"{int(qty):>10}"
                
                # name 축약 (15자 이내)
                name = row.get("name", row.get("symbol", ""))[:15]
                
                print(
                    f"{row.get('symbol', ''):<10} "
                    f"{name:<15} "
                    f"{qty_str} "
                    f"{currency_symbol}{row.get('avg_price', 0):>10.4f} "
                    f"{currency_symbol}{row.get('current_price', 0):>10.4f} "
                    f"{pnl_color}{pnl_sign}{pnl_rate:>8.2f}%{reset} "
                    f"{pnl_color}{pnl_sign}{currency_symbol}{pnl_amount:>12.2f}{reset}"
                )
            
            print("-" * 100)
            total_pnl = sum(r.get("pnl_amount", 0) for r in data.values())
            total_sign = "+" if total_pnl >= 0 else ""
            total_color = "\033[92m" if total_pnl >= 0 else "\033[91m"
            print(f"{'Total':<10} {'':<15} {'':<10} {'':<12} {'':<12} {'':<10} {total_color}{total_sign}${total_pnl:>12.2f}\033[0m")
            
            # balance 정보 표시
            if balance:
                print("-" * 100)
                if "total_pnl_rate" in balance:
                    total_rate = balance.get("total_pnl_rate", 0)
                    rate_color = "\033[92m" if total_rate >= 0 else "\033[91m"
                    rate_sign = "+" if total_rate >= 0 else ""
                    print(f"총 수익률: {rate_color}{rate_sign}{total_rate:.2f}%\033[0m")
                if "total_eval_krw" in balance:
                    print(f"총 평가금액(원화): ₩{balance.get('total_eval_krw', 0):,.0f}")
                if "total_pnl_krw" in balance:
                    pnl_krw = balance.get("total_pnl_krw", 0)
                    krw_color = "\033[92m" if pnl_krw >= 0 else "\033[91m"
                    krw_sign = "+" if pnl_krw >= 0 else ""
                    print(f"총 평가손익(원화): {krw_color}{krw_sign}₩{pnl_krw:,.0f}\033[0m")
            
            print("=" * 100)
        
        context.log("info", f"Display rendered: {chart_type}", node_id)
        return {"rendered": True}


class ConditionNodeExecutor(NodeExecutorBase):
    """ConditionNode executor (plugin-based)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Collect input data
        symbols = context.get_input(node_id, "symbols") or []
        price_data = context.get_input(node_id, "price_data") or {}

        # Evaluate expressions
        evaluated_fields = fields or {}
        if fields:
            expr_context = context.get_expression_context()
            evaluator = ExpressionEvaluator(expr_context)
            evaluated_fields = evaluator.evaluate_fields(fields)

        # Execute plugin (if present)
        passed_symbols = []
        values = {}

        if plugin:
            # Plugin execution logic
            for symbol in symbols:
                # TODO: Implement actual plugin execution
                passed_symbols.append(symbol)
                values[symbol] = {"result": True}
        else:
            # Pass all symbols if no plugin
            passed_symbols = symbols

        context.log(
            "info",
            f"Condition evaluated: {len(passed_symbols)}/{len(symbols)} passed",
            node_id,
        )

        return {
            "result": len(passed_symbols) > 0,
            "passed_symbols": passed_symbols,
            "failed_symbols": [s for s in symbols if s not in passed_symbols],
            "values": values,
        }


class WorkflowExecutor:
    """
    Workflow execution engine

    Stateful long-running execution:
    - 24-hour continuous execution support
    - Position/balance state persistence
    - Graceful Restart support
    """

    def __init__(self):
        self.resolver = WorkflowResolver()
        self._jobs: Dict[str, "WorkflowJob"] = {}
        self._executors: Dict[str, NodeExecutorBase] = self._init_executors()

    def _init_executors(self) -> Dict[str, NodeExecutorBase]:
        """Initialize per-node-type executors"""
        return {
            "StartNode": StartNodeExecutor(),
            "ScheduleNode": ScheduleNodeExecutor(),
            "WatchlistNode": WatchlistNodeExecutor(),
            "BrokerNode": BrokerNodeExecutor(),
            "RealAccountNode": RealAccountNodeExecutor(),
            "RealMarketDataNode": RealMarketDataNodeExecutor(),
            "CustomPnLNode": CustomPnLNodeExecutor(),
            "DisplayNode": DisplayNodeExecutor(),
            "ConditionNode": ConditionNodeExecutor(),
            # TODO: Implement remaining node executors
        }

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        Validate workflow

        Args:
            definition: Workflow definition (JSON dict)
        """
        return self.resolver.validate(definition)

    def compile(
        self,
        definition: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
    ) -> tuple[Optional[ResolvedWorkflow], ValidationResult]:
        """
        Compile workflow (convert to execution objects)

        Args:
            definition: Workflow definition
            context_params: Execution context parameters
        """
        return self.resolver.resolve(definition, context_params)

    async def execute(
        self,
        definition: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> "WorkflowJob":
        """
        Execute workflow

        Args:
            definition: Workflow definition
            context_params: Runtime parameters (symbols, dry_run, etc.)
            secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
            job_id: Job ID (auto-generated if not provided)
        """
        # Compile
        resolved, validation = self.compile(definition, context_params)
        if not validation.is_valid:
            raise ValueError(f"Workflow validation failed: {validation.errors}")

        # Create Job
        job_id = job_id or f"job-{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(
            job_id=job_id,
            workflow_id=resolved.workflow_id,
            context_params=context_params or {},
            secrets=secrets,
        )

        job = WorkflowJob(
            job_id=job_id,
            workflow=resolved,
            context=context,
            executor=self,
        )

        self._jobs[job_id] = job

        # Start execution
        await job.start()

        return job

    async def execute_node(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute single node"""
        executor = self._executors.get(node_type)

        if not executor:
            context.log("warning", f"No executor for node type: {node_type}", node_id)
            return {}

        # Add plugin fields for ConditionNode
        if node_type == "ConditionNode":
            return await executor.execute(
                node_id=node_id,
                node_type=node_type,
                config=config,
                context=context,
                plugin=plugin,
                fields=fields,
            )

        return await executor.execute(
            node_id=node_id,
            node_type=node_type,
            config=config,
            context=context,
        )

    def get_job(self, job_id: str) -> Optional["WorkflowJob"]:
        """Get Job"""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List["WorkflowJob"]:
        """List all Jobs"""
        return list(self._jobs.values())


class WorkflowJob:
    """
    Workflow execution instance

    Stateful: Persists position/balance state
    """

    def __init__(
        self,
        job_id: str,
        workflow: ResolvedWorkflow,
        context: ExecutionContext,
        executor: WorkflowExecutor,
    ):
        self.job_id = job_id
        self.workflow = workflow
        self.context = context
        self.executor = executor

        # State
        self.status = "pending"
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # Statistics
        self.stats = {
            "conditions_evaluated": 0,
            "orders_placed": 0,
            "orders_filled": 0,
            "errors_count": 0,
        }

        # Execution task
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start execution"""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.context.start()

        # Async execution
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        """Workflow execution loop"""
        try:
            # Execute nodes in topological order
            for node_id in self.workflow.execution_order:
                if not self.context.is_running:
                    break

                # Wait if paused
                while self.context.is_paused:
                    await asyncio.sleep(0.1)

                node = self.workflow.nodes.get(node_id)
                if not node:
                    continue

                # Connect inputs (get values from edges)
                for edge in self.workflow.edges:
                    if edge.to_node_id == node_id:
                        value = self.context.get_output(
                            edge.from_node_id,
                            edge.from_port,
                        )
                        if value is not None:
                            # Connect input value to node
                            input_port = edge.to_port or "input"
                            self.context.set_output(
                                f"_input_{node_id}",
                                input_port,
                                value,
                            )

                # Execute node
                outputs = await self.executor.execute_node(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=node.config,
                    context=self.context,
                    plugin=node.plugin,
                    fields=node.fields,
                )

                # Store outputs
                for port_name, value in outputs.items():
                    self.context.set_output(node_id, port_name, value)

            self.status = "completed"
            self.completed_at = datetime.utcnow()

        except Exception as e:
            self.status = "failed"
            self.stats["errors_count"] += 1
            self.context.log("error", str(e))

    async def pause(self) -> None:
        """Pause execution"""
        self.status = "paused"
        self.context.pause()

    async def resume(self) -> None:
        """Resume execution"""
        self.status = "running"
        self.context.resume()

    async def cancel(self) -> None:
        """Cancel execution"""
        self.status = "cancelled"
        self.context.stop()
        if self._task:
            self._task.cancel()

    def get_state(self) -> Dict[str, Any]:
        """Get state snapshot"""
        return {
            "job_id": self.job_id,
            "workflow_id": self.workflow.workflow_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stats": self.stats,
            "logs": self.context.get_logs(limit=50),
        }
