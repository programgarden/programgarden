"""
ThrottleNode + RealMarketDataNode(OVC) 통합 테스트

해외선물 실시간 시세와 ThrottleNode의 skip/latest 모드 검증.
- 종목: MHIG26 (미니항생 2026년 2월물)
- 테스트 시간: HKEX 개장 시간 (한국 10:15~17:00, 18:00~03:00)
"""

import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import pytest
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 파일 경로를 프로젝트 루트로 지정
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# API 키 확인 (해외선물 모의투자)
APPKEY_FUTURE = os.getenv("APPKEY_FUTURE_FAKE")
APPSECRET_FUTURE = os.getenv("APPSECRET_FUTURE_FAKE")

# 테스트 종목 (미니항생 2026년 2월물, 8자리 패딩)
# 종목코드는 마스터 조회로 최신 종목 확인 권장
TEST_SYMBOLS = [
    {"exchange": "HKEX", "symbol": "MHIG26"},
]

# 테스트 스킵 조건
skip_if_no_credentials = pytest.mark.skipif(
    not APPKEY_FUTURE or not APPSECRET_FUTURE,
    reason="APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE 환경변수가 필요합니다"
)


def create_throttle_workflow_futures(mode: str = "skip", interval_sec: float = 5.0) -> dict:
    """ThrottleNode 포함 해외선물 워크플로우 생성"""
    return {
        "id": f"throttle-test-futures-{mode}",
        "name": f"Throttle {mode} 모드 테스트 - 해외선물",
        "description": f"RealMarketDataNode(OVC) + ThrottleNode({mode}) 통합 테스트",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "BrokerNode",
                "provider": "ls-sec.co.kr",
                "product": "overseas_futures",
                "credential_id": "broker-futures",
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": TEST_SYMBOLS,
            },
            {
                "id": "realMarket",
                "type": "RealMarketDataNode",
                "connection": "{{ nodes.broker.connection }}",
                "symbols": "{{ nodes.watchlist.symbols }}",
                "stay_connected": True,
            },
            {
                "id": "throttle",
                "type": "ThrottleNode",
                "mode": mode,
                "interval_sec": interval_sec,
                "pass_first": True,
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "realMarket"},
            {"from": "realMarket", "to": "throttle"},
        ],
        "credentials": [
            {
                "id": "broker-futures",
                "type": "broker_ls",
                "name": "LS증권 해외선물 모의투자",
                "data": {
                    "appkey": "",
                    "appsecret": "",
                    "paper_trading": True,
                },
            }
        ],
    }


class TestThrottleWithOVC:
    """ThrottleNode + 해외선물 OVC 실시간 통합 테스트"""

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_skip_mode_with_futures_ticks(self):
        """
        skip 모드: 선물 틱 제어 확인
        
        - 5초 간격으로 설정
        - 30초 동안 틱 수신
        - ThrottleNode 상태 확인
        
        Note: 현재 테스트는 실시간 이벤트 트리거가 아닌 
        ThrottleNode의 초기 실행 및 상태 확인에 중점을 둡니다.
        """
        from programgarden import ProgramGarden

        workflow = create_throttle_workflow_futures(mode="skip", interval_sec=5.0)
        
        # Credential 주입
        for cred in workflow.get("credentials", []):
            if cred["id"] == "broker-futures":
                cred["data"]["appkey"] = APPKEY_FUTURE
                cred["data"]["appsecret"] = APPSECRET_FUTURE

        logger.info("=" * 60)
        logger.info("ThrottleNode SKIP 모드 테스트 시작 - 해외선물 (모의투자)")
        logger.info(f"종목: {TEST_SYMBOLS[0]['symbol']}")
        logger.info(f"interval_sec: 5초, 테스트 시간: 15초")
        logger.info("=" * 60)

        pg = ProgramGarden()
        job = None

        try:
            job = await pg.run_async(workflow)
            
            start_time = datetime.now()
            logger.info("⏳ 워크플로우 실행 및 ThrottleNode 상태 확인 중... (15초)")
            
            # 초기 실행 확인
            await asyncio.sleep(2)
            
            throttle_outputs = job.context.get_all_outputs("throttle")
            realmarket_outputs = job.context.get_all_outputs("realMarket")
            
            logger.info("-" * 40)
            logger.info("테스트 결과 (SKIP 모드 - 해외선물):")
            
            # ThrottleNode 출력 확인
            if throttle_outputs:
                stats = throttle_outputs.get("_throttle_stats", {})
                logger.info(f"  ThrottleNode 상태:")
                logger.info(f"    - passed: {stats.get('passed')}")
                logger.info(f"    - skipped_count: {stats.get('skipped_count', 0)}")
                logger.info(f"    - last_passed_at: {stats.get('last_passed_at')}")
                
                # 첫 실행은 pass_first=True이므로 통과해야 함
                assert stats.get("passed") is True, "첫 실행은 pass_first=True이므로 통과해야 합니다"
                logger.info("✅ ThrottleNode 첫 실행 통과 확인")
            else:
                logger.warning("⚠️ ThrottleNode 출력 없음")
            
            # RealMarketData 출력 확인
            if realmarket_outputs:
                symbols = realmarket_outputs.get("symbols", [])
                prices = realmarket_outputs.get("price", {})
                logger.info(f"  RealMarketDataNode 상태:")
                logger.info(f"    - symbols: {symbols}")
                logger.info(f"    - prices: {prices}")
                
                if prices:
                    logger.info("✅ 실시간 시세 수신 확인 (장 시간 내)")
                else:
                    logger.info("ℹ️ 가격 데이터 없음 (장 시간 외이거나 점심 휴식)")
            
            # 추가 대기 후 상태 재확인 (선물 틱이 오면 throttle 동작)
            logger.info("⏳ 추가 대기 중... (13초)")
            await asyncio.sleep(13)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"  총 테스트 시간: {elapsed:.1f}초")
            logger.info("✅ ThrottleNode skip 모드 기본 동작 테스트 완료")
            
        except Exception as e:
            logger.error(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if job:
                try:
                    await job.cancel()
                    logger.info("Job 취소 완료")
                except Exception as e:
                    logger.warning(f"Job 취소 중 에러: {e}")

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_latest_mode_with_futures_ticks(self):
        """
        latest 모드: 최신 선물 틱만 유지
        
        - 5초 간격으로 설정
        - ThrottleNode 초기 실행 확인
        
        Note: 현재 테스트는 실시간 이벤트 트리거가 아닌 
        ThrottleNode의 초기 실행 및 상태 확인에 중점을 둡니다.
        """
        from programgarden import ProgramGarden

        workflow = create_throttle_workflow_futures(mode="latest", interval_sec=5.0)
        
        # Credential 주입
        for cred in workflow.get("credentials", []):
            if cred["id"] == "broker-futures":
                cred["data"]["appkey"] = APPKEY_FUTURE
                cred["data"]["appsecret"] = APPSECRET_FUTURE

        logger.info("=" * 60)
        logger.info("ThrottleNode LATEST 모드 테스트 시작 - 해외선물 (모의투자)")
        logger.info(f"종목: {TEST_SYMBOLS[0]['symbol']}")
        logger.info(f"interval_sec: 5초, 테스트 시간: 15초")
        logger.info("=" * 60)

        pg = ProgramGarden()
        job = None

        try:
            job = await pg.run_async(workflow)
            
            start_time = datetime.now()
            logger.info("⏳ 워크플로우 실행 및 ThrottleNode 상태 확인 중... (15초)")
            
            # 초기 실행 확인
            await asyncio.sleep(2)
            
            throttle_outputs = job.context.get_all_outputs("throttle")
            realmarket_outputs = job.context.get_all_outputs("realMarket")
            
            logger.info("-" * 40)
            logger.info("테스트 결과 (LATEST 모드 - 해외선물):")
            
            # ThrottleNode 출력 확인
            if throttle_outputs:
                stats = throttle_outputs.get("_throttle_stats", {})
                logger.info(f"  ThrottleNode 상태:")
                logger.info(f"    - passed: {stats.get('passed')}")
                logger.info(f"    - skipped_count: {stats.get('skipped_count', 0)}")
                logger.info(f"    - last_passed_at: {stats.get('last_passed_at')}")
                
                # 첫 실행은 pass_first=True이므로 통과해야 함
                assert stats.get("passed") is True, "첫 실행은 pass_first=True이므로 통과해야 합니다"
                logger.info("✅ ThrottleNode 첫 실행 통과 확인")
            else:
                logger.warning("⚠️ ThrottleNode 출력 없음")
            
            # RealMarketData 출력 확인
            if realmarket_outputs:
                symbols = realmarket_outputs.get("symbols", [])
                prices = realmarket_outputs.get("price", {})
                logger.info(f"  RealMarketDataNode 상태:")
                logger.info(f"    - symbols: {symbols}")
                logger.info(f"    - prices: {prices}")
                
                if prices:
                    logger.info("✅ 실시간 시세 수신 확인 (장 시간 내)")
                else:
                    logger.info("ℹ️ 가격 데이터 없음 (장 시간 외이거나 점심 휴식)")
            
            # 추가 대기 후 상태 재확인
            logger.info("⏳ 추가 대기 중... (13초)")
            await asyncio.sleep(13)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"  총 테스트 시간: {elapsed:.1f}초")
            logger.info("✅ ThrottleNode latest 모드 기본 동작 테스트 완료")
            
        except Exception as e:
            logger.error(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if job:
                try:
                    await job.cancel()
                    logger.info("Job 취소 완료")
                except Exception as e:
                    logger.warning(f"Job 취소 중 에러: {e}")


if __name__ == "__main__":
    # 직접 실행 시
    import sys
    
    async def main():
        test = TestThrottleWithOVC()
        
        print("\n" + "=" * 70)
        print("ThrottleNode + 해외선물 OVC 통합 테스트 (모의투자)")
        print("=" * 70)
        
        if not APPKEY_FUTURE or not APPSECRET_FUTURE:
            print("❌ APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE 환경변수가 필요합니다.")
            sys.exit(1)
        
        # skip 모드 테스트
        print("\n[1/2] SKIP 모드 테스트")
        await test.test_skip_mode_with_futures_ticks()
        
        # 잠시 대기
        await asyncio.sleep(2)
        
        # latest 모드 테스트
        print("\n[2/2] LATEST 모드 테스트")
        await test.test_latest_mode_with_futures_ticks()
        
        print("\n" + "=" * 70)
        print("✅ 모든 테스트 완료")
        print("=" * 70)
    
    asyncio.run(main())
