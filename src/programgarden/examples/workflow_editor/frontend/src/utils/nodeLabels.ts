/**
 * 노드 타입별 사용자 친화적 라벨 (한글/영문)
 */

export type Locale = 'ko' | 'en';

export interface NodeLabelInfo {
  ko: string;
  en: string;
}

export const NODE_LABELS: Record<string, NodeLabelInfo> = {
  // Infra
  StartNode: { ko: '시작', en: 'Start' },
  BrokerNode: { ko: '브로커 연결', en: 'Broker Connection' },
  
  // Data
  WatchlistNode: { ko: '관심종목', en: 'Watchlist' },
  ScreenerNode: { ko: '종목 스크리너', en: 'Stock Screener' },
  HistoricalDataNode: { ko: '과거 데이터', en: 'Historical Data' },
  RealMarketDataNode: { ko: '실시간 시세', en: 'Real-time Market Data' },
  AccountNode: { ko: '계좌 정보', en: 'Account Info' },
  SQLiteNode: { ko: 'SQLite DB', en: 'SQLite DB' },
  PostgresNode: { ko: 'PostgreSQL DB', en: 'PostgreSQL DB' },
  MarketDataNode: { ko: '시장 데이터', en: 'Market Data' },
  
  // Condition
  ConditionNode: { ko: '조건 판단', en: 'Condition Check' },
  LogicNode: { ko: '논리 연산', en: 'Logic Gate' },
  
  // Order
  NewOrderNode: { ko: '신규 주문', en: 'New Order' },
  ModifyOrderNode: { ko: '주문 정정', en: 'Modify Order' },
  CancelOrderNode: { ko: '주문 취소', en: 'Cancel Order' },
  LiquidateNode: { ko: '청산', en: 'Liquidate' },
  
  // Risk
  PositionSizingNode: { ko: '포지션 크기', en: 'Position Sizing' },
  RiskGuardNode: { ko: '리스크 관리', en: 'Risk Guard' },
  RiskConditionNode: { ko: '리스크 조건', en: 'Risk Condition' },
  PortfolioNode: { ko: '포트폴리오', en: 'Portfolio' },
  
  // Trigger
  ScheduleNode: { ko: '예약 실행', en: 'Schedule' },
  TradingHoursFilterNode: { ko: '거래시간 필터', en: 'Trading Hours Filter' },
  
  // Event
  EventHandlerNode: { ko: '이벤트 핸들러', en: 'Event Handler' },
  AlertNode: { ko: '알림', en: 'Alert' },
  TelegramNode: { ko: '텔레그램 알림', en: 'Telegram Alert' },
  
  // Display
  DisplayNode: { ko: '차트 표시', en: 'Chart Display' },
  
  // Group
  GroupNode: { ko: '그룹', en: 'Group' },
  
  // Backtest
  BacktestEngineNode: { ko: '백테스트 엔진', en: 'Backtest Engine' },
  BacktestExecutorNode: { ko: '백테스트 실행', en: 'Backtest Executor' },
  BacktestResultNode: { ko: '백테스트 결과', en: 'Backtest Result' },
  PerformanceConditionNode: { ko: '성능 조건', en: 'Performance Condition' },
  
  // Job
  DeployNode: { ko: '배포', en: 'Deploy' },
  JobControlNode: { ko: '작업 제어', en: 'Job Control' },
  TradingHaltNode: { ko: '거래 중지', en: 'Trading Halt' },
  
  // Calculation
  CustomPnLNode: { ko: '손익 계산', en: 'PnL Calculator' },
  PnLCalculatorNode: { ko: '손익 계산', en: 'PnL Calculator' },
  
  // Realtime
  RealAccountNode: { ko: '실시간 계좌', en: 'Real-time Account' },
  RealOrderEventNode: { ko: '실시간 주문 이벤트', en: 'Real-time Order Event' },
  
  // Market
  MarketUniverseNode: { ko: '시장 유니버스', en: 'Market Universe' },
  SymbolQueryNode: { ko: '전체 종목 조회', en: 'All Symbols' },
  SymbolFilterNode: { ko: '종목 필터', en: 'Symbol Filter' },
  ExchangeStatusNode: { ko: '거래소 상태', en: 'Exchange Status' },
  
  // HTTP
  HTTPRequestNode: { ko: 'HTTP 요청', en: 'HTTP Request' },
};

/**
 * 노드 라벨 가져오기
 * @param nodeType 노드 타입 (예: StartNode)
 * @param locale 언어 (기본: ko)
 * @returns 사용자 친화적 라벨
 */
export function getNodeLabel(nodeType: string, locale: Locale = 'ko'): string {
  const labels = NODE_LABELS[nodeType];
  if (labels) {
    return labels[locale];
  }
  // 등록되지 않은 노드는 Node 접미사 제거 후 반환
  return nodeType.replace(/Node$/, '');
}
