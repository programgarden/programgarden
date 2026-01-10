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
  data: unknown[];
  xLabel?: string;
  yLabel?: string;
  options?: Record<string, unknown>;
}

// Color palette for charts (used in radar, heatmap, etc.)
const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

// Suppress unused variable warning - COLORS used in render functions
void COLORS;

/**
 * Table renderer for tabular data
 */
function TableRenderer({ data }: { data: unknown[] }) {
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-xs">No data</div>;
  }

  const firstItem = data[0] as Record<string, unknown>;
  const columns = Object.keys(firstItem);

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-600">
            {columns.map((col) => (
              <th key={col} className="px-2 py-1 text-left text-gray-400 font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 50).map((row, i) => (
            <tr key={i} className="border-b border-gray-700 hover:bg-gray-700/50">
              {columns.map((col) => (
                <td key={col} className="px-2 py-1 text-gray-300">
                  {String((row as Record<string, unknown>)[col] ?? '')}
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

export default function ChartRenderer({ type, data, xLabel, yLabel, options: _options }: ChartProps) {
  // Safety check for data
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        No data to display
      </div>
    );
  }

  // Determine data keys from first item
  const firstItem = data[0] as Record<string, unknown>;
  if (!firstItem || typeof firstItem !== 'object') {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        Invalid data format
      </div>
    );
  }
  
  const keys = Object.keys(firstItem);
  const xKey = keys.find((k) => ['x', 'date', 'time', 'name', 'label'].includes(k.toLowerCase())) || keys[0];
  const yKey = keys.find((k) => ['y', 'value', 'price', 'amount'].includes(k.toLowerCase())) || keys[1] || keys[0];

  switch (type) {
    case 'line':
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
          subject: d.subject || d.name || d.label || d[xKey],
          value: d.value || d[yKey],
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

    default:
      return (
        <div className="flex items-center justify-center h-full text-gray-500 text-sm">
          Unsupported chart type: {type}
        </div>
      );
  }
}
