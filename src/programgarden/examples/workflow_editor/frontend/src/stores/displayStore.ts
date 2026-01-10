import { create } from 'zustand';

/**
 * Display data for a single node
 */
export interface DisplayData {
  nodeId: string;
  chartType: 'line' | 'candlestick' | 'bar' | 'scatter' | 'radar' | 'heatmap' | 'table';
  title?: string;
  data: unknown[];
  xLabel?: string;
  yLabel?: string;
  options?: Record<string, unknown>;
  timestamp: Date;
}

interface DisplayStore {
  // Node ID -> Display data (last execution only)
  nodeDisplayData: Record<string, DisplayData>;
  
  // Actions
  setNodeDisplayData: (nodeId: string, data: Omit<DisplayData, 'nodeId' | 'timestamp'>) => void;
  clearNodeDisplayData: (nodeId: string) => void;
  clearAllDisplayData: () => void;
}

export const useDisplayStore = create<DisplayStore>((set) => ({
  nodeDisplayData: {},

  setNodeDisplayData: (nodeId, data) =>
    set((state) => ({
      nodeDisplayData: {
        ...state.nodeDisplayData,
        [nodeId]: {
          ...data,
          nodeId,
          timestamp: new Date(),
        },
      },
    })),

  clearNodeDisplayData: (nodeId) =>
    set((state) => {
      const { [nodeId]: _, ...rest } = state.nodeDisplayData;
      return { nodeDisplayData: rest };
    }),

  clearAllDisplayData: () => set({ nodeDisplayData: {} }),
}));
