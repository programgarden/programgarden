import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t8451

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t8451():

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # S-Oil(010950) 일봉 차트 조회 (최근 10건)
    m_t8451 = ls.국내주식().차트().주식차트(
        t8451.T8451InBlock(
            shcode="010950",
            gubun="2",       # 2:일
            qrycnt=10,
            edate="99999999",
            sujung="N",
            exchgubun="K"
        )
    )

    response = m_t8451.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block:
        b = response.block
        logger.info(f"종목: {b.shcode}")
        logger.info(f"전일 시가:{b.jisiga} 고가:{b.jihigh} 저가:{b.jilow} 종가:{b.jiclose} 거래량:{b.jivolume}")
        logger.info(f"당일 시가:{b.disiga} 고가:{b.dihigh} 저가:{b.dilow} 종가:{b.diclose}")
        logger.info(f"상한가:{b.highend} 하한가:{b.lowend}")
        logger.info(f"연속일자: '{b.cts_date}' (비어있으면 연속조회 없음)")

    if response.block1:
        logger.info(f"--- 차트 데이터 ({len(response.block1)}건) ---")
        for item in response.block1:
            sign_str = {
                "1": "상한", "2": "상승", "3": "보합", "4": "하한", "5": "하락"
            }.get(item.sign, item.sign)
            logger.info(
                f"  {item.date} | 시:{item.open:>8,} 고:{item.high:>8,} "
                f"저:{item.low:>8,} 종:{item.close:>8,} | "
                f"거래량:{item.jdiff_vol:>10,} | {sign_str}"
            )


def test_occurs_req_t8451():
    """연속조회 예제 - 대량 일봉 데이터 조회"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    from programgarden_finance.ls.status import RequestStatus

    def on_status(response, status: RequestStatus):
        if status == RequestStatus.LOADING:
            logger.info("연속 조회 중...")
        elif status == RequestStatus.DONE:
            logger.info("연속 조회 완료")

    # S-Oil(010950) 일봉 차트 연속조회 (500건씩)
    m_t8451 = ls.국내주식().차트().주식차트(
        t8451.T8451InBlock(
            shcode="010950",
            gubun="2",
            qrycnt=500,
            edate="99999999",
            sujung="N",
            exchgubun="K"
        )
    )

    responses = m_t8451.occurs_req(callback=on_status, delay=1)

    total_count = 0
    for i, resp in enumerate(responses):
        count = len(resp.block1) if resp.block1 else 0
        total_count += count
        logger.info(f"응답 #{i+1}: {count}건")

    logger.info(f"총 조회 건수: {total_count}건")


if __name__ == "__main__":
    test_req_t8451()
    # test_occurs_req_t8451()
