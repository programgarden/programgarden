import { useState, useEffect } from 'react';
import { Plus, X, ChevronDown } from 'lucide-react';

interface SymbolEntry {
  exchange: string;
  symbol: string;
}

interface ExchangeInfo {
  code: string;
  name: string;
  full_name: string;
}

interface SymbolEditorProps {
  value: SymbolEntry[];
  onChange: (value: SymbolEntry[]) => void;
  product?: string;
  onProductChange?: (product: string) => void;
}

// 기본 거래소 목록 (API 로드 전 fallback)
const DEFAULT_EXCHANGES: Record<string, Record<string, ExchangeInfo[]>> = {
  ls: {
    overseas_stock: [
      { code: '81', name: 'NYSE', full_name: 'New York Stock Exchange' },
      { code: '81', name: 'AMEX', full_name: 'American Stock Exchange' },
      { code: '82', name: 'NASDAQ', full_name: 'NASDAQ Stock Market' },
    ],
    overseas_futures: [
      { code: 'CME', name: 'CME', full_name: 'Chicago Mercantile Exchange' },
      { code: 'COMEX', name: 'COMEX', full_name: 'Commodity Exchange' },
      { code: 'NYMEX', name: 'NYMEX', full_name: 'New York Mercantile Exchange' },
      { code: 'CBOT', name: 'CBOT', full_name: 'Chicago Board of Trade' },
      { code: 'ICE', name: 'ICE', full_name: 'Intercontinental Exchange' },
    ],
  },
};

const PRODUCTS = [
  { value: 'overseas_stock', label: '해외주식' },
  { value: 'overseas_futures', label: '해외선물' },
];

// 증권사는 BrokerNode에서 관리 - 현재 ls만 지원
const DEFAULT_BROKER = 'ls';

export default function SymbolEditor({
  value: rawValue,
  onChange,
  product: initialProduct,
  onProductChange,
}: SymbolEditorProps) {
  // value가 배열이 아니면 빈 배열로 처리
  const value = Array.isArray(rawValue) ? rawValue : [];
  
  const [product, setProduct] = useState(initialProduct || 'overseas_stock');
  // 증권사는 BrokerNode에서 관리 - 현재 ls만 지원
  const broker = DEFAULT_BROKER;
  const [exchanges, setExchanges] = useState<ExchangeInfo[]>([]);
  const [loading, setLoading] = useState(false);

  // 거래소 목록 로드
  useEffect(() => {
    const loadExchanges = async () => {
      setLoading(true);
      try {
        // API에서 거래소 목록 로드 시도
        const response = await fetch(`/api/exchanges?broker=${broker}&product=${product}`);
        if (response.ok) {
          const data = await response.json();
          setExchanges(data.exchanges || []);
        } else {
          // API 실패 시 기본값 사용
          setExchanges(DEFAULT_EXCHANGES[broker]?.[product] || []);
        }
      } catch {
        // 에러 시 기본값 사용
        setExchanges(DEFAULT_EXCHANGES[broker]?.[product] || []);
      }
      setLoading(false);
    };

    loadExchanges();
  }, [broker, product]);

  // product/broker가 사용자에 의해 변경될 때만 상위로 전파 (handleProductChange에서 처리)
  // useEffect 제거 - 무한 루프 방지

  const handleProductChange = (newProduct: string) => {
    setProduct(newProduct);
    onProductChange?.(newProduct);  // 상위로 전파
    
    // 상품 변경 시 기존 심볼의 거래소가 유효한지 확인
    const newExchanges = DEFAULT_EXCHANGES[broker]?.[newProduct] || [];
    const validExchangeNames = new Set(newExchanges.map(e => e.name));
    
    // 유효하지 않은 거래소를 가진 심볼은 기본 거래소로 변경
    const defaultExchange = newExchanges[0]?.name || '';
    const updatedSymbols = value.map(entry => ({
      ...entry,
      exchange: validExchangeNames.has(entry.exchange) ? entry.exchange : defaultExchange,
    }));
    
    if (JSON.stringify(updatedSymbols) !== JSON.stringify(value)) {
      onChange(updatedSymbols);
    }
  };

  const addSymbol = () => {
    const defaultExchange = exchanges[0]?.name || 'NASDAQ';
    onChange([...value, { exchange: defaultExchange, symbol: '' }]);
  };

  const updateSymbol = (index: number, updates: Partial<SymbolEntry>) => {
    const newSymbols = [...value];
    newSymbols[index] = { ...newSymbols[index], ...updates };
    onChange(newSymbols);
  };

  const removeSymbol = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const getExchangeColor = (exchangeName: string): string => {
    const colors: Record<string, string> = {
      NYSE: 'bg-blue-600',
      AMEX: 'bg-blue-500',
      NASDAQ: 'bg-green-600',
      CME: 'bg-orange-600',
      COMEX: 'bg-yellow-600',
      NYMEX: 'bg-red-600',
      CBOT: 'bg-purple-600',
      ICE: 'bg-cyan-600',
    };
    return colors[exchangeName] || 'bg-gray-600';
  };

  return (
    <div className="space-y-3">
      {/* Product 선택 (항상 표시, BrokerNode 연결 시 비활성화 가능) */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-xs text-gray-400">상품 유형</label>
          {initialProduct && (
            <span className="text-xs text-green-400">✓ BrokerNode 연동</span>
          )}
        </div>
        <select
          value={product}
          onChange={(e) => handleProductChange(e.target.value)}
          className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
        >
          {PRODUCTS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        {initialProduct && product !== initialProduct && (
          <p className="text-xs text-amber-400 mt-1">
            ⚠️ BrokerNode({PRODUCTS.find(p => p.value === initialProduct)?.label})와 다른 상품입니다
          </p>
        )}
      </div>

      {/* 심볼 목록 헤더 */}
      <div className="flex items-center justify-between">
        <label className="text-xs text-gray-400">
          관심종목 ({value.length}개)
        </label>
        <button
          onClick={addSymbol}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
        >
          <Plus className="w-3 h-3" />
          추가
        </button>
      </div>

      {/* 심볼 목록 */}
      {value.length === 0 ? (
        <div className="text-center py-4 text-gray-500 text-sm border border-dashed border-gray-600 rounded">
          종목이 없습니다. "추가" 버튼을 클릭하세요.
        </div>
      ) : (
        <div className="space-y-2">
          {value.map((entry, index) => (
            <div key={index} className="flex items-center gap-2">
              {/* 거래소 선택 */}
              <div className="relative w-28">
                <select
                  value={entry.exchange}
                  onChange={(e) => updateSymbol(index, { exchange: e.target.value })}
                  className={`w-full px-2 py-1.5 pr-7 ${getExchangeColor(entry.exchange)} border-0 rounded text-sm text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer`}
                  disabled={loading}
                >
                  {exchanges.map(ex => (
                    <option key={ex.name} value={ex.name} className="bg-gray-800">
                      {ex.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-white/70 pointer-events-none" />
              </div>

              {/* 종목코드 입력 */}
              <input
                type="text"
                value={entry.symbol}
                onChange={(e) => updateSymbol(index, { symbol: e.target.value.toUpperCase() })}
                placeholder={product === 'overseas_stock' ? 'AAPL' : 'NQH25'}
                className="flex-1 px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 font-mono focus:outline-none focus:border-blue-500"
              />

              {/* 삭제 버튼 */}
              <button
                onClick={() => removeSymbol(index)}
                className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded transition-colors"
                title="삭제"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 거래소 범례 */}
      <div className="flex flex-wrap gap-1 pt-2 border-t border-gray-700">
        {exchanges.map(ex => (
          <span
            key={ex.name}
            className={`px-2 py-0.5 ${getExchangeColor(ex.name)} rounded text-xs text-white`}
            title={ex.full_name}
          >
            {ex.name}
          </span>
        ))}
      </div>
    </div>
  );
}
