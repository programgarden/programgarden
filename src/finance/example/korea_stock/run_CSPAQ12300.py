"""Read position cost evidence; the entire CSPAQ12300 summary is unavailable."""
import logging
import os

from dotenv import load_dotenv
from programgarden_finance import LS, CSPAQ12300

logger = logging.getLogger(__name__)
load_dotenv()

POSITION_FIELDS = (
    "IsuNo", "BalQty", "BnsBaseBalQty", "AvrUprc", "PchsAmt",
    "NowPrc", "BalEvalAmt", "EvalPnl", "PnlRat",
)


def position_evidence(item):
    """Preserve missing values and the broker's raw ratio scale."""
    return {
        key: getattr(item, key) if key in item.model_fields_set else None
        for key in POSITION_FIELDS
    }


def test_req_CSPAQ12300():
    """Query the owner-supplied official average-price request once."""
    logging.basicConfig(level=logging.INFO)
    ls = LS()
    if not ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    ):
        logger.error("Broker login failed")
        return

    body = CSPAQ12300.CSPAQ12300InBlock1(
        RecCnt=1, BalCreTp="0", CmsnAppTpCode="0",
        D2balBaseQryTp="0", UprcTpCode="0",
    )
    response = ls.korea_stock().accno().cspaq12300(body).req()
    if response.error_msg:
        logger.error("Request failed: %s", response.error_msg)
        return

    logger.info("Broker response code: %s", response.rsp_cd)
    logger.info("Account summary: %s (all OutBlock2 fields)", response.block2_status)
    logger.info("Price basis: average; valuation commission: excluded")
    if response.header and response.header.tr_cont == "Y":
        logger.info("More pages are available; this is not a complete account view")
    # Do not log private holdings or account values in a runnable example.
    rows = [position_evidence(item) for item in response.block3]
    logger.info("Position rows returned: %s", len(rows))
    return rows


if __name__ == "__main__":
    test_req_CSPAQ12300()
