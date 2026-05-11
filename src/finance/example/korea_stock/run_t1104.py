import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1104

logger = logging.getLogger(__name__)

load_dotenv()


# LS-declared enum mappings for t1104:
#   gubn — 1=시세 / 2=최고저가 / 3=Pivot / 4=이동평균선
#   dat1 — 1=시가 / 2=고가 / 3=저가 / 4=가중평균가
#   dat2 — 1=당일 / 2=전일
# Unit / decimal scale / format of OutBlock1.vals are NOT declared in
# available LS source; the example prints values as returned by LS without
# unit annotations. Interpretation of dat1 under gubn=3 (Pivot) or 4
# (이동평균선) is also undeclared.

_GUBN_LABEL = {
    "1": "시세 (quote)",
    "2": "최고저가 (period high/low)",
    "3": "Pivot (피봇)",
    "4": "이동평균선 (moving average)",
}
_DAT1_LABEL = {
    "1": "시가 (open)",
    "2": "고가 (high)",
    "3": "저가 (low)",
    "4": "가중평균가 (weighted average)",
}
_DAT2_LABEL = {
    "1": "당일 (today)",
    "2": "전일 (previous day)",
}


def test_req_t1104_quote():
    """t1104 주식현재가시세메모 — 시세(gubn=1) 디렉티브 4건 동시 조회.

    삼성전자(005930) 의 당일 시가/고가/저가/가중평균가를 한 번에 요청.
    """

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    directives = [
        t1104.T1104InBlock1(indx="0", gubn="1", dat1="1", dat2="1"),  # 당일 시가
        t1104.T1104InBlock1(indx="1", gubn="1", dat1="2", dat2="1"),  # 당일 고가
        t1104.T1104InBlock1(indx="2", gubn="1", dat1="3", dat2="1"),  # 당일 저가
        t1104.T1104InBlock1(indx="3", gubn="1", dat1="4", dat2="1"),  # 당일 가중평균가
    ]

    m_t1104 = ls.국내주식().시세().주식현재가시세메모(
        t1104InBlock_body=t1104.T1104InBlock(
            code="005930",
            nrec=str(len(directives)).zfill(2),
            exchgubun="K",  # K=KRX / N=NXT / U=통합
        ),
        t1104InBlock1_body=directives,
    )

    response = m_t1104.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.summary_block:
        logger.info(f"출력건수 nrec: {response.summary_block.nrec}")

    logger.info(f"조회 건수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(
        f"{'indx':>4} {'gubn':>4} {'category':>28} {'vals':>20}"
    )
    logger.info("-" * 100)

    # Re-correlate each output row to the request directive via ``indx``.
    by_indx = {d.indx: d for d in directives}
    for item in response.block:
        directive = by_indx.get(item.indx)
        sub_key = ""
        if directive:
            sub_key = (
                f" | dat1={_DAT1_LABEL.get(directive.dat1, directive.dat1)} "
                f"/ dat2={_DAT2_LABEL.get(directive.dat2, directive.dat2)}"
            )
        logger.info(
            f"{item.indx:>4} {item.gubn:>4} "
            f"{_GUBN_LABEL.get(item.gubn, item.gubn):>28} "
            f"{item.vals:>20}{sub_key}"
        )


def test_req_t1104_high_low():
    """t1104 — 최고저가(gubn=2) 디렉티브: 당일/전일 고가·저가 비교."""

    logging.basicConfig(level=logging.INFO)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    directives = [
        t1104.T1104InBlock1(indx="0", gubn="2", dat1="2", dat2="1"),  # 당일 고가
        t1104.T1104InBlock1(indx="1", gubn="2", dat1="3", dat2="1"),  # 당일 저가
        t1104.T1104InBlock1(indx="2", gubn="2", dat1="2", dat2="2"),  # 전일 고가
        t1104.T1104InBlock1(indx="3", gubn="2", dat1="3", dat2="2"),  # 전일 저가
    ]

    m_t1104 = ls.국내주식().시세().주식현재가시세메모(
        t1104InBlock_body=t1104.T1104InBlock(
            code="000660",  # SK하이닉스
            nrec=str(len(directives)).zfill(2),
            exchgubun="K",
        ),
        t1104InBlock1_body=directives,
    )

    response = m_t1104.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        return

    logger.info(f"최고저가 조회 건수: {len(response.block)}건")
    for item, directive in zip(response.block, directives):
        logger.info(
            f"indx={item.indx} gubn={item.gubn} "
            f"dat1={_DAT1_LABEL.get(directive.dat1, directive.dat1)} "
            f"dat2={_DAT2_LABEL.get(directive.dat2, directive.dat2)} "
            f"vals={item.vals}"
        )


def test_req_t1104_pivot_and_ma():
    """t1104 — Pivot(gubn=3) + 이동평균선(gubn=4) 디렉티브 혼합 조회.

    dat1 의 의미가 gubn=3/4 에서 LS 명세에 선언되어 있지 않음 (시가/고가/저가
    keyword 가 Pivot 의 P/S1/R1 등에 매핑되는지 등 cross-product 의미를
    소스에서 확인 불가). vals 값은 그대로 출력.
    """

    logging.basicConfig(level=logging.INFO)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA"),
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    directives = [
        t1104.T1104InBlock1(indx="0", gubn="3", dat1="1", dat2="1"),  # Pivot
        t1104.T1104InBlock1(indx="1", gubn="3", dat1="2", dat2="1"),
        t1104.T1104InBlock1(indx="2", gubn="4", dat1="1", dat2="1"),  # 이동평균선
        t1104.T1104InBlock1(indx="3", gubn="4", dat1="2", dat2="1"),
    ]

    m_t1104 = ls.국내주식().시세().주식현재가시세메모(
        t1104InBlock_body=t1104.T1104InBlock(
            code="035720",  # 카카오
            nrec=str(len(directives)).zfill(2),
            exchgubun="K",
        ),
        t1104InBlock1_body=directives,
    )

    response = m_t1104.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        return

    logger.info(f"Pivot+MA 조회 건수: {len(response.block)}건")
    for item in response.block:
        logger.info(
            f"indx={item.indx} "
            f"category={_GUBN_LABEL.get(item.gubn, item.gubn)} "
            f"vals={item.vals}"
        )


if __name__ == "__main__":
    test_req_t1104_quote()
