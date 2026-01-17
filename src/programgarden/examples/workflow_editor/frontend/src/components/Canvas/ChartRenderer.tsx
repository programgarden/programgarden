/**
 * ChartRenderer - Recharts-based chart rendering component
 * 
 * Supports: line, candlestick, bar, scatter, radar, heatmap, table
 */
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface ChartProps {
  type: string;
  data: unknown[] | Record<string, unknown>;  // Can be array or object
  xLabel?: string;
  yLabel?: string;
  options?: Record<string, unknown>;
}

// Color palette for charts (used in radar, heatmap, etc.)
const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

// Suppress unused variable warning - COLORS used in render functions
void COLORS;

/**
 * Format cell value for display in table
 * Handles nested objects, arrays, numbers, etc.
 */
function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'number') {
    // Format numbers nicely
    return Number.isInteger(value) ? value.toString() : value.toFixed(4).replace(/\.?0+$/, '');
  }
  if (typeof value === 'boolean') {
    return value ? '✓' : '✗';
  }
  if (typeof value === 'object') {
    // For nested objects/arrays, show a compact JSON
    return JSON.stringify(value);
  }
  return String(value);
}

/**
 * Table renderer for tabular data
 * Supports flat arrays of objects and nested position-like structures
 */
function TableRenderer({ data }: { data: unknown[] }) {
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-xs">No data</div>;
  }

  const firstItem = data[0] as Record<string, unknown>;
  
  // Check if data is positions-like: [{ SYMBOL: { ... }, SYMBOL2: { ... } }]
  // This is when each item is an object whose values are also objects
  const firstValue = Object.values(firstItem)[0];
  if (typeof firstValue === 'object' && firstValue !== null && !Array.isArray(firstValue)) {
    // Flatten positions-like data: extract the inner objects
    const flattenedData: Record<string, unknown>[] = [];
    data.forEach((item) => {
      const itemObj = item as Record<string, unknown>;
      Object.values(itemObj).forEach((innerValue) => {
        if (typeof innerValue === 'object' && innerValue !== null) {
          flattenedData.push(innerValue as Record<string, unknown>);
        }
      });
    });
    
    if (flattenedData.length > 0) {
      const columns = Object.keys(flattenedData[0]);
      return (
        <div className="overflow-auto h-full">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-600">
                {columns.map((col) => (
                  <th key={col} className="px-2 py-1 text-left text-gray-400 font-medium whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {flattenedData.slice(0, 50).map((row, i) => (
                <tr key={i} className="border-b border-gray-700 hover:bg-gray-700/50">
                  {columns.map((col) => (
                    <td key={col} className="px-2 py-1 text-gray-300 whitespace-nowrap">
                      {formatCellValue(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {flattenedData.length > 50 && (
            <div className="text-gray-500 text-xs p-2">
              ... and {flattenedData.length - 50} more rows
            </div>
          )}
        </div>
      );
    }
  }

  // Standard flat array of objects
  const columns = Object.keys(firstItem);

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-600">
            {columns.map((col) => (
              <th key={col} className="px-2 py-1 text-left text-gray-400 font-medium whitespace-nowrap">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 50).map((row, i) => (
            <tr key={i} className="border-b border-gray-700 hover:bg-gray-700/50">
              {columns.map((col) => (
                <td key={col} className="px-2 py-1 text-gray-300 whitespace-nowrap">
                  {formatCellValue((row as Record<string, unknown>)[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 50 && (
        <div className="text-gray-500 text-xs p-2">
          ... and {data.length - 50} more rows
        </div>
      )}
    </div>
  );
}

/**
 * Raw JSON data renderer for fallback display
 * Shows prettified JSON with syntax highlighting
 */
function RawDataRenderer({ data }: { data: unknown }) {
  // Convert data to pretty JSON string with syntax highlighting
  const renderJson = (obj: unknown, indent: number = 0): React.ReactNode[] => {
    const indentStr = '  '.repeat(indent);
    const elements: React.ReactNode[] = [];
    
    if (obj === null) {
      return [<span key="null" className="text-gray-500">null</span>];
    }
    if (obj === undefined) {
      return [<span key="undefined" className="text-gray-500">undefined</span>];
    }
    if (typeof obj === 'boolean') {
      return [<span key="bool" className="text-purple-400">{obj.toString()}</span>];
    }
    if (typeof obj === 'number') {
      const formatted = Number.isInteger(obj) ? obj.toString() : obj.toFixed(4).replace(/\.?0+$/, '');
      return [<span key="num" className="text-blue-400">{formatted}</span>];
    }
    if (typeof obj === 'string') {
      return [<span key="str" className="text-green-400">"{obj}"</span>];
    }
    
    if (Array.isArray(obj)) {
      if (obj.length === 0) {
        return [<span key="empty-arr" className="text-gray-400">[]</span>];
      }
      elements.push(<span key="arr-open" className="text-gray-400">[</span>);
      elements.push(<br key="arr-open-br" />);
      obj.forEach((item, i) => {
        elements.push(<span key={`arr-indent-${i}`}>{indentStr}  </span>);
        elements.push(...renderJson(item, indent + 1));
        if (i < obj.length - 1) {
          elements.push(<span key={`arr-comma-${i}`} className="text-gray-500">,</span>);
        }
        elements.push(<br key={`arr-br-${i}`} />);
      });
      elements.push(<span key="arr-close-indent">{indentStr}</span>);
      elements.push(<span key="arr-close" className="text-gray-400">]</span>);
      return elements;
    }
    
    if (typeof obj === 'object') {
      const entries = Object.entries(obj);
      if (entries.length === 0) {
        return [<span key="empty-obj" className="text-gray-400">{'{}'}</span>];
      }
      elements.push(<span key="obj-open" className="text-gray-400">{'{'}</span>);
      elements.push(<br key="obj-open-br" />);
      entries.forEach(([key, value], i) => {
        elements.push(<span key={`obj-indent-${i}`}>{indentStr}  </span>);
        elements.push(<span key={`obj-key-${i}`} className="text-yellow-400">"{key}"</span>);
        elements.push(<span key={`obj-colon-${i}`} className="text-gray-500">: </span>);
        elements.push(...renderJson(value, indent + 1));
        if (i < entries.length - 1) {
          elements.push(<span key={`obj-comma-${i}`} className="text-gray-500">,</span>);
        }
        elements.push(<br key={`obj-br-${i}`} />);
      });
      elements.push(<span key="obj-close-indent">{indentStr}</span>);
      elements.push(<span key="obj-close" className="text-gray-400">{'}'}</span>);
      return elements;
    }
    
    return [<span key="unknown" className="text-gray-300">{String(obj)}</span>];
  };

  // Count items for header
  const itemCount = Array.isArray(data) 
    ? data.length 
    : (typeof data === 'object' && data !== null ? Object.keys(data).length : 1);

  return (
    <div className="h-full overflow-auto p-2 bg-gray-900/80 rounded">
      <div className="text-gray-500 text-xs mb-2 flex items-center gap-1 sticky top-0 bg-gray-900/90 py-1">
        📋 Raw Output
        <span className="text-gray-600">
          ({itemCount} {Array.isArray(data) ? 'items' : 'fields'})
        </span>
      </div>
      <pre className="text-xs font-mono leading-relaxed whitespace-pre-wrap break-all">
        {renderJson(data)}
      </pre>
    </div>
  );
}

/**
 * Heatmap renderer (simplified grid)
 */
function HeatmapRenderer({ data }: { data: unknown[] }) {
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-xs">No data</div>;
  }

  // Assume data is array of { x, y, value }
  const maxValue = Math.max(...data.map((d) => Math.abs(Number((d as Record<string, unknown>).value) || 0)));
  
  return (
    <div className="grid gap-0.5 h-full overflow-auto" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(20px, 1fr))` }}>
      {data.slice(0, 100).map((item, i) => {
        const value = Number((item as Record<string, unknown>).value) || 0;
        const intensity = Math.abs(value) / (maxValue || 1);
        const color = value >= 0 
          ? `rgba(34, 197, 94, ${intensity})` 
          : `rgba(239, 68, 68, ${intensity})`;
        
        return (
          <div
            key={i}
            className="aspect-square rounded-sm"
            style={{ backgroundColor: color }}
            title={`${value}`}
          />
        );
      })}
    </div>
  );
}

/**
 * Candlestick renderer (simplified using bar chart)
 */
function CandlestickRenderer({ data }: { data: unknown[] }) {
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-xs">No data</div>;
  }

  // Transform OHLC data for visualization
  const chartData = data.map((item) => {
    const d = item as Record<string, unknown>;
    const open = Number(d.open) || 0;
    const close = Number(d.close) || 0;
    const high = Number(d.high) || 0;
    const low = Number(d.low) || 0;
    const isUp = close >= open;
    
    return {
      x: d.x || d.date || d.time,
      open,
      close,
      high,
      low,
      body: Math.abs(close - open),
      bodyStart: Math.min(open, close),
      isUp,
    };
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} barGap={0}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="x" tick={{ fontSize: 9, fill: '#9ca3af' }} />
        <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
          labelStyle={{ color: '#fff' }}
        />
        <Bar dataKey="body" stackId="a">
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.isUp ? '#22c55e' : '#ef4444'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function ChartRenderer({ type, data, xLabel, yLabel, options }: ChartProps) {
  // Safety check for data - handle both array and object
  const isEmpty = !data || (Array.isArray(data) ? data.length === 0 : Object.keys(data).length === 0);
  
  if (isEmpty) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        No data to display
      </div>
    );
  }

  // Handle object data (like positions) - render as raw
  if (!Array.isArray(data)) {
    return <RawDataRenderer data={data} />;
  }

  // Determine data keys from first item
  const firstItem = data[0] as Record<string, unknown>;
  if (!firstItem || typeof firstItem !== 'object') {
    return <RawDataRenderer data={data} />;
  }
  
  const keys = Object.keys(firstItem);
  // x_field, y_field는 명시적으로 지정해야 함 (자동 추론 제거)
  const xKey = options?.x_field as string | undefined;
  const yKey = options?.y_field as string | undefined;

  switch (type) {
    case 'line':
      // line 차트는 x_field, y_field 필수
      if (!xKey || !yKey) {
        return (
          <div className="flex items-center justify-center h-full text-yellow-400 text-xs p-2">
            ⚠️ line 차트에는 x_field, y_field 지정 필요<br/>
            사용 가능한 필드: {keys.join(', ')}
          </div>
        );
      }
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data as Record<string, unknown>[]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey={xKey} 
              tick={{ fontSize: 9, fill: '#9ca3af' }}
              label={xLabel ? { value: xLabel, position: 'bottom', fontSize: 10, fill: '#9ca3af' } : undefined}
            />
            <YAxis 
              tick={{ fontSize: 9, fill: '#9ca3af' }}
              label={yLabel ? { value: yLabel, angle: -90, position: 'left', fontSize: 10, fill: '#9ca3af' } : undefined}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 11 }}
              labelStyle={{ color: '#fff' }}
            />
            <Line 
              type="monotone" 
              dataKey={yKey} 
              stroke="#8b5cf6" 
              strokeWidth={2} 
              dot={data.length <= 20}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      );

    case 'multi_line': {
      // Multi-line chart: multiple series grouped by series_key
      // Data format: [{symbol: 'AAPL', date: '20250101', rsi: 28.5}, ...]
      // multi_line도 x_field, y_field, series_key 필수
      if (!xKey || !yKey) {
        return (
          <div className="flex items-center justify-center h-full text-yellow-400 text-xs p-2">
            ⚠️ multi_line 차트에는 x_field, y_field, series_key 지정 필요<br/>
            사용 가능한 필드: {keys.join(', ')}
          </div>
        );
      }
      const seriesKey = (options?.series_key as string) || 'symbol';
      const xFieldKey = xKey;
      const yFieldKey = yKey;
      
      // Group data by series_key
      const groupedData: Record<string, Record<string, unknown>[]> = {};
      (data as Record<string, unknown>[]).forEach((item) => {
        const key = String(item[seriesKey] || 'unknown');
        if (!groupedData[key]) {
          groupedData[key] = [];
        }
        groupedData[key].push(item);
      });
      
      const seriesNames = Object.keys(groupedData);
      
      // Merge all data points with series-specific y values
      // Result: [{date: '20250101', AAPL: 28.5, NVDA: 45.2}, ...]
      const mergedData: Record<string, unknown>[] = [];
      const allXValues = new Set<string>();
      
      Object.entries(groupedData).forEach(([, items]) => {
        items.forEach((item) => {
          allXValues.add(String(item[xFieldKey]));
        });
      });
      
      // Sort x values (works for dates like '20250101')
      const sortedXValues = Array.from(allXValues).sort();
      
      sortedXValues.forEach((xVal) => {
        const point: Record<string, unknown> = { [xFieldKey]: xVal };
        seriesNames.forEach((series) => {
          const item = groupedData[series]?.find((i) => String(i[xFieldKey]) === xVal);
          point[series] = item ? item[yFieldKey] : null;
        });
        mergedData.push(point);
      });
      
      // Line colors for different series
      const lineColors = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6', '#f97316'];
      
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mergedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey={xFieldKey}
              tick={{ fontSize: 9, fill: '#9ca3af' }}
              label={xLabel ? { value: xLabel, position: 'bottom', fontSize: 10, fill: '#9ca3af' } : undefined}
            />
            <YAxis 
              tick={{ fontSize: 9, fill: '#9ca3af' }}
              label={yLabel ? { value: yLabel, angle: -90, position: 'left', fontSize: 10, fill: '#9ca3af' } : undefined}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 11 }}
              labelStyle={{ color: '#fff' }}
            />
            {seriesNames.map((series, idx) => (
              <Line
                key={series}
                type="monotone"
                dataKey={series}
                name={series}
                stroke={lineColors[idx % lineColors.length]}
                strokeWidth={2}
                dot={mergedData.length <= 30}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      );
    }

    case 'bar':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data as Record<string, unknown>[]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey={xKey} tick={{ fontSize: 9, fill: '#9ca3af' }} />
            <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 11 }}
              labelStyle={{ color: '#fff' }}
            />
            <Bar dataKey={yKey} fill="#8b5cf6" />
          </BarChart>
        </ResponsiveContainer>
      );

    case 'scatter':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey={xKey} tick={{ fontSize: 9, fill: '#9ca3af' }} name={xKey} />
            <YAxis dataKey={yKey} tick={{ fontSize: 9, fill: '#9ca3af' }} name={yKey} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 11 }}
              cursor={{ strokeDasharray: '3 3' }}
            />
            <Scatter data={data as Record<string, unknown>[]} fill="#8b5cf6" />
          </ScatterChart>
        </ResponsiveContainer>
      );

    case 'radar':
      // Radar expects data with 'subject' and value keys
      const radarData = data.map((item) => {
        const d = item as Record<string, unknown>;
        return {
          subject: d.subject || d.name || d.label || (xKey ? d[xKey] : ''),
          value: d.value || (yKey ? d[yKey] : 0),
          fullMark: 100,
        };
      });

      return (
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData}>
            <PolarGrid stroke="#374151" />
            <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9, fill: '#9ca3af' }} />
            <PolarRadiusAxis tick={{ fontSize: 8, fill: '#9ca3af' }} />
            <Radar
              dataKey="value"
              stroke="#8b5cf6"
              fill="#8b5cf6"
              fillOpacity={0.5}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', fontSize: 11 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      );

    case 'candlestick':
      return <CandlestickRenderer data={data} />;

    case 'heatmap':
      return <HeatmapRenderer data={data} />;

    case 'table':
      return <TableRenderer data={data} />;

    case 'raw':
      // Raw JSON viewer for unsupported data types
      return <RawDataRenderer data={data} />;

    default:
      // Fallback: try to render as raw JSON if we have data
      if (data && (Array.isArray(data) ? data.length > 0 : Object.keys(data).length > 0)) {
        return <RawDataRenderer data={data} />;
      }
      return (
        <div className="flex items-center justify-center h-full text-gray-500 text-sm">
          Unsupported chart type: {type}
        </div>
      );
  }
}
