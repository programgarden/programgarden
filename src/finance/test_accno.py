#!/usr/bin/env python3
"""간단한 계좌 조회 테스트"""
from dotenv import load_dotenv
import os
from pathlib import Path

# .env 로드
load_dotenv(Path(__file__).parents[2] / ".env")

appkey = os.getenv("APPKEY")
appsecret = os.getenv("APPSECRET")
print(f"APPKEY: {appkey[:8]}..." if appkey else "APPKEY: None")

from programgarden_finance import LS

ls = LS.get_instance()
login_result = ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=False)
print(f"Login result: {login_result}")
print(f"Is logged in: {ls.is_logged_in()}")

# 계좌 잔고 조회
accno = ls.overseas_stock().accno()
result = accno.get_summary()
print(f"\n=== Holdings ===")
if result and hasattr(result, "positions"):
    for pos in result.positions:
        print(f"  {pos.symbol}: {pos.quantity} @ {pos.buy_price}")
else:
    print(f"  Raw result: {result}")
