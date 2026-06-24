import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1514

logger = logging.getLogger(__name__)

load_dotenv()

# 전일대비구분(sign) 표시 매핑 — LS 컨벤션 '1'..'5'
_SIGN = {"1": "상한", "2": "상승", "3": "보합", "4": "하한", "5": "하락"}


def test_req_t1514():
    """t1514 업종기간별추이 테스트 (단건 조회)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피 종합(001) 업종의 일봉 기간추이 최근 10건, 거래량비중(rate_gbn=1)
    m = ls.국내주식().업종테마().업종기간별추이(
        t1514.T1514InBlock(
            upcode="001",   # 업종코드 — '001' 코스피 종합
            gubun2="1",     # 주기 — 1:일 2:주 3:월
            cnt=10,
            rate_gbn="1",   # 거래비중 기준 — 1:거래량비중 2:거래대금비중
        )
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block and response.block.cts_date:
        logger.info(f"연속조회키(cts_date): {response.block.cts_date}")

    logger.info(f"조회 건수: {len(response.block1)}건")
    logger.info("=" * 110)
    logger.info(
        f"{'일자':<10} {'지수':>10} {'전일대비':>9} {'등락률':>7} "
        f"{'거래량':>12} | {'상승':>4}/{'보합':>4}/{'하락':>4} {'상승비율':>7}"
    )
    logger.info("-" * 110)

    for item in response.block1:
        sign_str = _SIGN.get(item.sign, item.sign)
        # 주의: high/unchg/low 는 '가격'이 아니라 업종 내 상승/보합/하락 '종목 수'.
        logger.info(
            f"{item.date:<10} {item.jisu:>10,.2f} {sign_str}{item.change:>+8.2f} "
            f"{item.diff:>+6.2f}% {item.volume:>12,} | "
            f"{item.high:>4,}/{item.unchg:>4,}/{item.low:>4,} {item.uprate:>6.2f}%"
        )

    # 첫 행 전체 필드 덤프 — 라이브 스모크에서 24개 컬럼 파싱을 눈으로 확인
    if response.block1:
        r0 = response.block1[0]
        logger.info("=" * 110)
        logger.info(f"[첫 행({r0.date}) 전체 필드 — upcode={r0.upcode}]")
        logger.info(
            f"  지수 OHLC  시:{r0.openjisu:,.2f} 고:{r0.highjisu:,.2f} "
            f"저:{r0.lowjisu:,.2f} 종:{r0.jisu:,.2f}"
        )
        logger.info(
            f"  거래        value1:{r0.value1:,} value2:{r0.value2:,} | "
            f"거래증가율:{r0.diff_vol:+.2f}% 거래비중:{r0.rate:.2f}%"
        )
        logger.info(
            f"  시장폭(종목수)  상한:{r0.up} 상승:{r0.high} 보합:{r0.unchg} "
            f"하락:{r0.low} 하한:{r0.down} / 종목수:{r0.totjo}"
        )
        logger.info(
            f"  수급        외인순매수:{r0.frgsvolume:,} 기관순매수:{r0.orgsvolume:,} | "
            f"업종배당수익률:{r0.divrate:.2f}%"
        )


def test_occurs_req_t1514():
    """t1514 연속조회 예제 — cts_date 기반 대량 기간추이 수집."""

    logging.basicConfig(level=logging.INFO)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m = ls.국내주식().업종테마().업종기간별추이(
        t1514.T1514InBlock(
            upcode="001",
            gubun2="1",
            cnt=500,
            rate_gbn="1",
        )
    )

    responses = m.occurs_req(delay=1)

    total = sum(len(r.block1) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)} | 누적 행 수: {total}")

    last_err = next((r.error_msg for r in responses if r.error_msg), None)
    if last_err:
        logger.error(f"연속조회 중 오류: {last_err}")


if __name__ == "__main__":
    test_req_t1514()
