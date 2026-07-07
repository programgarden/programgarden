import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t8409

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t8409():
    """t8409 업종차트(N분) 테스트 (단건 조회)."""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 코스피 종합(001) 업종의 1분봉 차트 최근 5건.
    # 신경로: ls.indtp().업종차트분(...) (= ls.업종().t8409(...)).
    m = ls.indtp().업종차트분(
        t8409.T8409InBlock(
            shcode="001",       # 업종코드 — '001' 코스피 종합
            ncnt=1,             # 단위 — 0:30초, 1:1분, n:n분
            qrycnt=5,           # 요청 건수
            nday="0",           # 조회영업일수 — '0' 미사용
            sdate=" ",          # 시작일자 — 공백(미사용)
            edate="99999999",   # 종료일자 — 최초 조회 기준일
            comp_yn="N",        # 압축여부 — N:압축안함
        )
    )

    response = m.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    # 주의: 아래 모든 OHLC 는 업종 '지수(index points)' 이며 KRW '가격'이 아니다.
    # 거래대금(disvalue/value)은 백만원, 거래량(jivolume/jdiff_vol)은 천주 단위
    # (LS 미선언 → 샘플 응답 교차검증 확정값).
    if response.cont_block:
        cb = response.cont_block
        logger.info("=" * 100)
        logger.info(f"[메타 — shcode={cb.shcode}, 레코드카운트={cb.rec_count}]")
        logger.info(
            f"  전일 지수 OHLC  시:{cb.jisiga:,.2f} 고:{cb.jihigh:,.2f} "
            f"저:{cb.jilow:,.2f} 종:{cb.jiclose:,.2f} | 전일거래량:{cb.jivolume:,}천주"
        )
        logger.info(
            f"  당일 지수 OHLC  시:{cb.disiga:,.2f} 고:{cb.dihigh:,.2f} "
            f"저:{cb.dilow:,.2f} 종:{cb.diclose:,.2f} | 당일거래대금:{cb.disvalue:,}백만원"
        )
        logger.info(f"  업종 시작:{cb.s_time} 종료:{cb.e_time}")
        if cb.cts_date or cb.cts_time:
            logger.info(f"  연속커서 cts_date:{cb.cts_date} cts_time:{cb.cts_time}")

    logger.info(f"조회 분봉 행 수: {len(response.block)}건")
    logger.info("=" * 100)
    logger.info(
        f"{'일자':<10} {'시간':<8} {'시가':>10} {'고가':>10} "
        f"{'저가':>10} {'종가':>10} {'거래량':>12} {'거래대금':>14}"
    )
    logger.info("-" * 100)

    for row in response.block:
        # 주의: open/high/low/close 는 업종 지수(index points), KRW 가격이 아님.
        # jdiff_vol=천주, value=백만원.
        logger.info(
            f"{row.date:<10} {row.time:<8} {row.open:>10,.2f} {row.high:>10,.2f} "
            f"{row.low:>10,.2f} {row.close:>10,.2f} {row.jdiff_vol:>12,} {row.value:>14,}"
        )


def test_occurs_req_t8409():
    """t8409 연속조회 예제 — cts_date/cts_time 기반 대량 분봉 차트 수집."""

    logging.basicConfig(level=logging.INFO)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    m = ls.indtp().업종차트분(
        t8409.T8409InBlock(
            shcode="001",
            ncnt=1,
            qrycnt=500,
            nday="0",
            sdate=" ",
            edate="99999999",
            comp_yn="N",
        )
    )

    responses = m.occurs_req(delay=1)

    total = sum(len(r.block) for r in responses)
    logger.info(f"연속조회 페이지 수: {len(responses)} | 누적 행 수: {total}")

    last_err = next((r.error_msg for r in responses if r.error_msg), None)
    if last_err:
        logger.error(f"연속조회 중 오류: {last_err}")


if __name__ == "__main__":
    test_req_t8409()
