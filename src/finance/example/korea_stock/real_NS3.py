"""Receive NS3 quotes for the owner-supplied symbol; never submit an order."""
import asyncio
import logging
import os
from dotenv import load_dotenv
from programgarden_finance import LS
from programgarden_finance.ls.korea_stock.real.NS3.blocks import NS3RealResponse

logger = logging.getLogger(__name__)


async def run_example(duration: float = 45) -> dict:
    load_dotenv()
    ls = LS.get_instance()
    if not ls.login(appkey=os.getenv("APPKEY_KOREA"), appsecretkey=os.getenv("APPSECRET_KOREA")):
        raise RuntimeError("Domestic broker login failed")
    real = ls.korea_stock().real()
    summary = {"ticks": 0, "acknowledgements": [], "observed_fields": [], "parse_errors": 0}
    observed = set()

    async def on_message(response: NS3RealResponse):
        if response.error_msg:
            summary["parse_errors"] += 1
        if response.body is None:
            summary["acknowledgements"].append(response.rsp_cd)
            return
        summary["ticks"] += 1
        observed.update(response.body.model_fields_set)

    await real.connect()
    ns3 = real.NS3()
    try:
        ns3.on_ns3_message(on_message)
        # Exact source request: N + six digits + three spaces, tr_type="3".
        ns3.add_ns3_symbols(["N010950   "])
        await asyncio.sleep(duration)
    finally:
        ns3.remove_ns3_symbols(["N010950   "])
        await asyncio.sleep(0.25)
        ns3.on_remove_ns3_message(on_message)
        await real.close()
    summary["observed_fields"] = sorted(observed)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    print(asyncio.run(run_example()))
