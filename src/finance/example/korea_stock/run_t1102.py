import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1102

logger = logging.getLogger(__name__)

load_dotenv()


def test_req_t1102():
    """t1102 주식현재가(시세)조회 테스트 - 종합 시세/펀더멘탈/증권사동향"""

    logging.basicConfig(level=logging.DEBUG)

    ls = LS()

    login_result = ls.login(
        appkey=os.getenv("APPKEY_KOREA"),
        appsecretkey=os.getenv("APPSECRET_KOREA")
    )

    if login_result is False:
        logger.error("로그인 실패")
        return

    # 삼성전자(005930) 종합 시세 조회
    m_t1102 = ls.국내주식().시세().주식현재가시세(
        t1102.T1102InBlock(shcode="005930", exchgubun="K")
    )

    response = m_t1102.req()

    if response.error_msg:
        logger.error(f"요청 실패: {response.error_msg}")
        logger.error(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")
        return

    logger.info(f"rsp_cd: {response.rsp_cd}, rsp_msg: {response.rsp_msg}")

    if response.block:
        b = response.block
        sign_str = {
            "1": "상한", "2": "상승", "3": "보합", "4": "하한", "5": "하락"
        }.get(b.sign, b.sign)

        logger.info(f"=== {b.hname} ({b.shcode}) - {b.janginfo} ===")
        logger.info(f"현재가: {b.price:,} ({sign_str} {b.change:,} / {b.diff}%)")
        logger.info(f"시가: {b.open:,}({b.opentime}) | 고가: {b.high:,}({b.hightime}) | 저가: {b.low:,}({b.lowtime})")
        logger.info(f"거래량: {b.volume:,} | 전일거래량: {b.jnilvolume:,} | 거래량차: {b.volumediff:,}")
        logger.info(f"거래대금: {b.value:,}백만 | 기준가: {b.recprice:,} | 가중평균: {b.avg:,}")
        logger.info(f"상한가: {b.uplmtprice:,} | 하한가: {b.dnlmtprice:,}")

        logger.info(f"--- 투자지표 ---")
        logger.info(f"PER: {b.per} | PBR: {b.pbrx} | T.PER: {b.t_per}")
        logger.info(f"시가총액: {b.total:,}억 | 상장주식수: {b.listing:,}천주 | 액면가: {b.parprice:,}")
        logger.info(f"52주 고가: {b.high52w:,}({b.high52wdate}) | 52주 저가: {b.low52w:,}({b.low52wdate})")

        logger.info(f"--- 증권사 매매동향 Top5 (매도) ---")
        for i in range(1, 6):
            name = getattr(b, f"offerno{i}")
            vol = getattr(b, f"dvol{i}")
            diff = getattr(b, f"ddiff{i}")
            if name:
                logger.info(f"  {name}: {vol:,}주 ({diff}%)")

        logger.info(f"--- 증권사 매매동향 Top5 (매수) ---")
        for i in range(1, 6):
            name = getattr(b, f"bidno{i}")
            vol = getattr(b, f"svol{i}")
            diff = getattr(b, f"sdiff{i}")
            if name:
                logger.info(f"  {name}: {vol:,}주 ({diff}%)")

        logger.info(f"--- 외국계 ---")
        logger.info(f"외국계 매도: {b.fwdvl:,}주 | 매수: {b.fwsvl:,}주")

        logger.info(f"--- 재무 실적 ---")
        logger.info(f"[{b.name}] 매출: {b.bfsales:,}억 | 영업이익: {b.bfoperatingincome:,}억 | 순이익: {b.bfnetincome:,}억 | EPS: {b.bfeps}")
        logger.info(f"[{b.name2}] 매출: {b.bfsales2:,}억 | 영업이익: {b.bfoperatingincome2:,}억 | 순이익: {b.bfnetincome2:,}억 | EPS: {b.bfeps2}")


if __name__ == "__main__":
    test_req_t1102()
