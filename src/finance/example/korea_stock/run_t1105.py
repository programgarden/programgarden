import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1105

logger = logging.getLogger(__name__)

load_dotenv()


# LS publishes only the field labels (피봇 / 1차·2차 저항·지지 / 기준가격 /
# D저항·D지지) for t1105 — the underlying pivot / Demark mathematical
# formulas are vendor-specific and NOT declared in available LS source.
# Decimal scale, currency unit of price fields, the reference base of
# ``stdprc``, and whether values vary by exchange (exchgubun=N/U) are
# likewise undeclared — values are printed as returned by LS without
# derivation or unit annotations.


def _print_response(label: str, response) -> None:
    """Helper — print the single OutBlock with all 9 levels side-by-side."""
    logger.info(f"=== {label} ===")
    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        return

    if response.block is None:
        logger.info("[피봇/디마크] OutBlock 없음")
        return

    b = response.block
    logger.info(f"[종목] {b.shcode}")
    logger.info(
        f"[Pivot ladder] supp2={b.supp2:,} | supp1={b.supp1:,} | "
        f"pbot={b.pbot:,} | offer1={b.offer1:,} | offer2={b.offer2:,}"
    )
    logger.info(f"[Demark]      suppd={b.suppd:,} | offerd={b.offerd:,}")
    logger.info(f"[Reference]   stdprc={b.stdprc:,}")


def _login() -> "LS":
    ls = LS()
    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )
    if login_result is False:
        logger.error("로그인 실패")
        raise RuntimeError("login failed")
    return ls


def test_req_t1105_krx():
    """t1105 주식피봇/디마크조회 — KRX (exchgubun='K', default)."""
    logging.basicConfig(level=logging.INFO)

    ls = _login()
    # 흥국화재(001200) — LS 공식 example 종목.
    m = ls.국내주식().시세().주식피봇디마크조회(
        t1105.T1105InBlock(
            shcode="001200",
            exchgubun="K",
        )
    )
    response = m.req()
    _print_response("t1105 KRX (exchgubun=K)", response)


def test_req_t1105_nxt():
    """t1105 주식피봇/디마크조회 — NXT (exchgubun='N')."""
    logging.basicConfig(level=logging.INFO)

    ls = _login()
    m = ls.국내주식().시세().주식피봇디마크조회(
        t1105.T1105InBlock(
            shcode="005930",
            exchgubun="N",
        )
    )
    response = m.req()
    _print_response("t1105 NXT (exchgubun=N)", response)


def test_req_t1105_unified():
    """t1105 주식피봇/디마크조회 — 통합 (exchgubun='U')."""
    logging.basicConfig(level=logging.INFO)

    ls = _login()
    m = ls.국내주식().시세().주식피봇디마크조회(
        t1105.T1105InBlock(
            shcode="005930",
            exchgubun="U",
        )
    )
    response = m.req()
    _print_response("t1105 통합 (exchgubun=U)", response)


if __name__ == "__main__":
    test_req_t1105_krx()
    test_req_t1105_nxt()
    test_req_t1105_unified()
