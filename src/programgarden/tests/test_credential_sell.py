#!/usr/bin/env python3
"""
Credential 구조 변경 테스트 - 보유종목 조회 후 매도

테스트 시나리오:
1. 해외주식 실거래 - 보유종목 조회 후 1주 매도
2. 해외선물 모의투자 - 보유종목 조회 후 1계약 청산
"""

import asyncio
import os
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 로드
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
    logger.info(f"Loaded .env from {env_path}")


async def test_overseas_stock_account():
    """해외주식 실거래 - 보유종목 조회"""
    logger.info("=" * 60)
    logger.info("해외주식 실거래 - 보유종목 조회")
    logger.info("=" * 60)

    workflow = {
        "id": "test-stock-account",
        "name": "해외주식 보유종목 조회",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode"
            },
            {
                "id": "broker",
                "type": "OverseasStockBrokerNode",
                "credential_id": "stock-cred"
            },
            {
                "id": "account",
                "type": "OverseasStockAccountNode"
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"}
        ],
        "credentials": [
            {
                "id": "stock-cred",
                "type": "broker_ls_stock",
                "data": [
                    {"key": "appkey", "value": os.environ.get("APPKEY", "")},
                    {"key": "appsecret", "value": os.environ.get("APPSECRET", "")}
                ]
            }
        ]
    }

    from programgarden import WorkflowExecutor

    executor = WorkflowExecutor()
    job = await executor.execute(workflow)

    await asyncio.sleep(3)
    await job.stop()

    # 결과 출력
    positions = job.context.get_all_outputs("account")
    logger.info(f"보유종목 조회 결과:")

    if positions:
        held = positions.get("held_symbols", [])
        balance = positions.get("balance", {})
        pos_list = positions.get("positions", [])

        logger.info(f"  보유종목 수: {len(held)}")
        logger.info(f"  예수금: {balance}")

        for p in pos_list:
            logger.info(f"  - {p.get('symbol')} @ {p.get('exchange')}: "
                       f"{p.get('quantity')}주, 평단가 ${p.get('avg_price')}, "
                       f"현재가 ${p.get('current_price')}, 손익 ${p.get('pnl')}")

        return pos_list
    else:
        logger.warning("보유종목 조회 실패")
        return []


async def test_overseas_stock_sell(position):
    """해외주식 실거래 - 1주 매도"""
    if not position:
        logger.info("매도할 종목 없음")
        return

    symbol = position.get("symbol")
    exchange = position.get("exchange")
    current_price = position.get("current_price", 0)

    logger.info("=" * 60)
    logger.info(f"해외주식 실거래 - {symbol} 1주 매도 (시장가)")
    logger.info("=" * 60)

    workflow = {
        "id": "test-stock-sell",
        "name": "해외주식 매도",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode"
            },
            {
                "id": "broker",
                "type": "OverseasStockBrokerNode",
                "credential_id": "stock-cred"
            },
            {
                "id": "order",
                "type": "OverseasStockNewOrderNode",
                "side": "sell",
                "order_type": "market",
                "order": {
                    "symbol": symbol,
                    "exchange": exchange,
                    "quantity": 1,
                    "price": current_price
                }
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "order"}
        ],
        "credentials": [
            {
                "id": "stock-cred",
                "type": "broker_ls_stock",
                "data": [
                    {"key": "appkey", "value": os.environ.get("APPKEY", "")},
                    {"key": "appsecret", "value": os.environ.get("APPSECRET", "")}
                ]
            }
        ]
    }

    from programgarden import WorkflowExecutor

    executor = WorkflowExecutor()
    job = await executor.execute(workflow)

    await asyncio.sleep(5)
    await job.stop()

    result = job.context.get_all_outputs("order")
    logger.info(f"매도 결과: {result}")
    return result


async def test_overseas_futures_account():
    """해외선물 모의투자 - 보유종목 조회"""
    logger.info("=" * 60)
    logger.info("해외선물 모의투자 - 보유종목 조회")
    logger.info("=" * 60)

    workflow = {
        "id": "test-futures-account",
        "name": "해외선물 보유종목 조회",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode"
            },
            {
                "id": "broker",
                "type": "OverseasFuturesBrokerNode",
                "credential_id": "futures-cred"
            },
            {
                "id": "account",
                "type": "OverseasFuturesAccountNode"
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"}
        ],
        "credentials": [
            {
                "id": "futures-cred",
                "type": "broker_ls_futures",
                "data": [
                    {"key": "appkey", "value": os.environ.get("APPKEY_FUTURE_FAKE", "")},
                    {"key": "appsecret", "value": os.environ.get("APPSECRET_FUTURE_FAKE", "")},
                    {"key": "paper_trading", "value": True}
                ]
            }
        ]
    }

    from programgarden import WorkflowExecutor

    executor = WorkflowExecutor()
    job = await executor.execute(workflow)

    await asyncio.sleep(3)
    await job.stop()

    # 결과 출력
    positions = job.context.get_all_outputs("account")
    logger.info(f"보유종목 조회 결과:")

    if positions:
        held = positions.get("held_symbols", [])
        balance = positions.get("balance", {})
        pos_list = positions.get("positions", [])

        logger.info(f"  보유종목 수: {len(held)}")
        logger.info(f"  예수금: {balance}")

        for p in pos_list:
            logger.info(f"  - {p.get('symbol')}: "
                       f"{p.get('quantity')}계약, 평단가 {p.get('avg_price')}, "
                       f"현재가 {p.get('current_price')}, 손익 {p.get('pnl')}")

        return pos_list
    else:
        logger.warning("보유종목 조회 실패")
        return []


async def test_overseas_futures_close(position):
    """해외선물 모의투자 - 1계약 청산"""
    if not position:
        logger.info("청산할 종목 없음")
        return

    symbol = position.get("symbol")
    quantity = position.get("quantity", 0)
    side = position.get("side", "buy")
    current_price = position.get("current_price", 0)

    # 청산은 반대 포지션
    close_side = "sell" if side == "buy" else "buy"

    logger.info("=" * 60)
    logger.info(f"해외선물 모의투자 - {symbol} 1계약 청산 ({close_side})")
    logger.info("=" * 60)

    workflow = {
        "id": "test-futures-close",
        "name": "해외선물 청산",
        "nodes": [
            {
                "id": "start",
                "type": "StartNode"
            },
            {
                "id": "broker",
                "type": "OverseasFuturesBrokerNode",
                "credential_id": "futures-cred"
            },
            {
                "id": "order",
                "type": "OverseasFuturesNewOrderNode",
                "side": close_side,
                "order_type": "market",
                "order": {
                    "symbol": symbol,
                    "quantity": 1,
                    "price": current_price
                }
            }
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "order"}
        ],
        "credentials": [
            {
                "id": "futures-cred",
                "type": "broker_ls_futures",
                "data": [
                    {"key": "appkey", "value": os.environ.get("APPKEY_FUTURE_FAKE", "")},
                    {"key": "appsecret", "value": os.environ.get("APPSECRET_FUTURE_FAKE", "")},
                    {"key": "paper_trading", "value": True}
                ]
            }
        ]
    }

    from programgarden import WorkflowExecutor

    executor = WorkflowExecutor()
    job = await executor.execute(workflow)

    await asyncio.sleep(5)
    await job.stop()

    result = job.context.get_all_outputs("order")
    logger.info(f"청산 결과: {result}")
    return result


async def main():
    logger.info("=" * 60)
    logger.info("Credential 구조 변경 테스트 시작")
    logger.info("=" * 60)

    # 1. 해외주식 실거래 - 보유종목 조회
    stock_positions = await test_overseas_stock_account()

    # 2. 해외주식 보유종목이 있으면 1주 매도
    if stock_positions:
        # 첫 번째 보유종목 매도
        await test_overseas_stock_sell(stock_positions[0])

    logger.info("\n")

    # 3. 해외선물 모의투자 - 보유종목 조회
    futures_positions = await test_overseas_futures_account()

    # 4. 해외선물 보유종목이 있으면 1계약 청산
    if futures_positions:
        await test_overseas_futures_close(futures_positions[0])

    logger.info("=" * 60)
    logger.info("테스트 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
