/**
 * SSE (Server-Sent Events) Hook for Workflow Execution
 * 
 * Manages SSE connection lifecycle and event handling for real-time
 * workflow execution updates.
 * 
 * Usage:
 *   const { connect, disconnect, isConnected } = useSSE();
 *   
 *   // Before running workflow
 *   await connect();
 *   
 *   // After workflow completes or stops
 *   disconnect();
 */

import { useRef, useCallback, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useDisplayStore } from '@/stores/displayStore';

export function useSSE() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const {
    setNodeState,
    setEdgeState,
    setRunning,
    addLog,
    setNodeOutput,
  } = useWorkflowStore();

  const connect = useCallback((): Promise<void> => {
    return new Promise((resolve, reject) => {
      // Close existing connection if any
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      console.log('🔌 Connecting to SSE...');
      const es = new EventSource('/events');
      eventSourceRef.current = es;
      
      // Connection timeout
      const connectionTimeout = setTimeout(() => {
        if (es.readyState !== EventSource.OPEN) {
          console.error('❌ SSE connection timeout');
          es.close();
          eventSourceRef.current = null;
          reject(new Error('SSE connection timeout'));
        }
      }, 10000); // 10 second timeout

      // Node state changes
      es.addEventListener('node_state', (e) => {
        const data = JSON.parse(e.data);
        console.log('📥 node_state:', data);
        setNodeState(data.node_id, data.state);
        
        // Store node output when completed OR when running with outputs (realtime nodes)
        // Realtime nodes (RealAccountNode, RealMarketDataNode) stay in 'running' state
        // and send output updates continuously
        if (data.outputs) {
          if (data.state === 'completed' || data.state === 'running') {
            console.log(`📊 Updating outputs for ${data.node_id}:`, Object.keys(data.outputs));
            setNodeOutput(data.node_id, data.outputs);
          }
        }
        
        // Add log for state transitions (but not for running state realtime updates)
        // Skip logging if it's just a realtime update (running + has outputs)
        const isRealtimeUpdate = data.state === 'running' && data.outputs;
        if (!isRealtimeUpdate) {
          const emojiMap: Record<string, string> = {
            pending: '⏳',
            running: '🔄',
            completed: '✅',
            failed: '❌',
            skipped: '⏭️',
          };
          const emoji = emojiMap[data.state as string] || '❓';
          
          addLog({
            level: data.state === 'failed' ? 'error' : 'node',
            message: `${emoji} Node [${data.node_id}] → ${data.state.toUpperCase()}`,
            nodeId: data.node_id,
          });
        }
      });

      // Edge state changes
      es.addEventListener('edge_state', (e) => {
        const data = JSON.parse(e.data);
        console.log('📥 edge_state:', data);
        setEdgeState(
          data.from_node,
          data.from_port,
          data.to_node,
          data.to_port,
          data.state
        );
      });

      // Job state changes
      es.addEventListener('job_state', (e) => {
        const data = JSON.parse(e.data);
        console.log('📥 job_state:', data);
        
        if (['completed', 'failed', 'stopped', 'cancelled'].includes(data.status)) {
          setRunning(false);
          addLog({
            level: data.status === 'completed' ? 'success' : 'error',
            message: `🏁 Workflow ${data.status}`,
          });
        }
      });

      // Log events from server
      es.addEventListener('log', (e) => {
        const data = JSON.parse(e.data);
        console.log('📥 log:', data);
        addLog({
          level: data.level,
          message: data.message,
          nodeId: data.node_id,
        });
      });

      // Display data events for visualization nodes
      es.addEventListener('display_data', (e) => {
        try {
          const data = JSON.parse(e.data);
          console.log('📥 display_data:', data);
          
          // Handle both array and object data
          // - Array: line charts, tables with list data
          // - Object: positions, balance, raw JSON etc.
          let chartData = data.data;
          if (chartData === null || chartData === undefined) {
            chartData = [];
          }
          // Don't force to array - let ChartRenderer handle different types
          
          // Update display store with chart data
          // nodeId and timestamp are added automatically by the store
          useDisplayStore.getState().setNodeDisplayData(data.node_id, {
            chartType: data.chart_type || 'raw',
            title: data.title || '',
            data: chartData,
            xLabel: data.x_label,
            yLabel: data.y_label,
            options: data.options,
          });
          
          const itemCount = Array.isArray(chartData) ? chartData.length : Object.keys(chartData).length;
          addLog({
            level: 'info',
            message: `📊 Display updated: [${data.node_id}] - ${data.chart_type || 'raw'} (${itemCount} items)`,
            nodeId: data.node_id,
          });
        } catch (err) {
          console.error('❌ Error processing display_data:', err);
        }
      });

      // Connection opened
      es.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('✅ SSE connected');
        setIsConnected(true);
        resolve();
      };

      // Connection error
      es.onerror = (error) => {
        console.error('❌ SSE error:', error);
        setIsConnected(false);
        clearTimeout(connectionTimeout);
        
        // Close and reject on any error during initial connection
        if (es.readyState === EventSource.CLOSED) {
          addLog({ level: 'warning', message: '⚠️ Event stream disconnected' });
          eventSourceRef.current = null;
          reject(new Error('SSE connection failed'));
        } else if (es.readyState === EventSource.CONNECTING) {
          // Close the stale connection and reject
          es.close();
          eventSourceRef.current = null;
          addLog({ level: 'warning', message: '⚠️ Event stream connection failed' });
          reject(new Error('SSE connection failed'));
        }
      };
    });
  }, [setNodeState, setEdgeState, setRunning, addLog, setNodeOutput]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('🔌 Disconnecting SSE...');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  return {
    connect,
    disconnect,
    isConnected,
  };
}
