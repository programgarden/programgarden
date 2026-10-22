import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1449

logger = logging.getLogger(__name__)

load_dotenv()


# LS-declared enum mapping for ``T1449OutBlock.sign`` / ``T1449OutBlock1.sign``
# (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). Other field semantics
# (currency unit of price fields, sign convention of ``change``, row
# ordering of OutBlock1, exact denominators for ``diff`` (비중) /
# ``msdiff`` (매수비율) / reference base of ``tickdiff``) are NOT
# declared in the LS source available to this codebase — values are
# printed as returned by LS without unit annotations.
_SIGN_GLYPH = {"1": "▲", "2": "△", "3": "-", "4": "▼", "5": "▽"}


def _print_response(label: str, response) -> None:
    """Helper — print summary OutBlock + per-price-level OutBlock1 rows."""
    logger.info(f"=== {label} ===")
    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        return

    # OutBlock — current-price summary.
    if response.out_block is not None:
        s = response.out_block
        glyph = _SIGN_GLYPH.get(s.sign, s.sign)
        logger.info(
            f"[요약] 현재가={s.price:,} {glyph} 전일대비={s.change:+,} "
            f"등락률={s.diff:+.2f}% 거래량={s.volume:,} "
            f"매수체결량={s.msvolume:,} 매도체결량={s.mdvolume:,}"
        )
    else:
        logger.info("[요약] OutBlock 없음")

    # OutBlock1 — per-price-level rows.
    logger.info(f"[가격대별] 행 수: {len(response.block)}")
    if response.block:
        logger.info("-" * 110)
        logger.info(
            f"{'체결가':>10} {'sign':>4} {'전일대비':>9} {'등락률':>8} "
            f"{'체결수량':>11} {'비중':>8} {'매도체결량':>11} {'매수체결량':>11} {'매수비율':>8}"
        )
        logger.info("-" * 110)
        for item in response.block:
            glyph = _SIGN_GLYPH.get(item.sign, item.sign)
            logger.info(
                f"{item.price:>10,} {glyph:>4} {item.change:>+9,} "
                f"{item.tickdiff:>+7.2f}% {item.cvolume:>11,} "
                f"{item.diff:>7.2f}% {item.mdvolume:>11,} "
                f"{item.msvolume:>11,} {item.msdiff:>7.2f}%"
            )


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


def test_req_t1449_today():
    """t1449 가격대별매매비중조회 — 당일(dategb=1)."""
    logging.basicConfig(level=logging.INFO)

    ls = _login()
    # 흥국화재(001200) — LS 공식 example 종목 사용. dategb=1 (당일).
    m = ls.국내주식().시세().가격대별매매비중조회(
        t1449.T1449InBlock(
            shcode="001200",
            dategb="1",
        )
    )
    response = m.req()
    _print_response("t1449 당일 (dategb=1)", response)


def test_req_t1449_yesterday():
    """t1449 가격대별매매비중조회 — 전일(dategb=2)."""
    logging.basicConfig(level=logging.INFO)

    ls = _login()
    # 흥국화재(001200) 전일 분포.
    m = ls.국내주식().시세().가격대별매매비중조회(
        t1449.T1449InBlock(
            shcode="001200",
            dategb="2",
        )
    )
    response = m.req()
    _print_response("t1449 전일 (dategb=2)", response)


def test_req_t1449_combined():
    """t1449 가격대별매매비중조회 — 당일+전일(dategb=3)."""
    logging.basicConfig(level=logging.INFO)

    ls = _login()
    # 흥국화재(001200) 당일+전일 결합.
    m = ls.국내주식().시세().가격대별매매비중조회(
        t1449.T1449InBlock(
            shcode="001200",
            dategb="3",
        )
    )
    response = m.req()
    _print_response("t1449 당일+전일 (dategb=3)", response)


if __name__ == "__main__":
    test_req_t1449_today()
    test_req_t1449_yesterday()
    test_req_t1449_combined()
