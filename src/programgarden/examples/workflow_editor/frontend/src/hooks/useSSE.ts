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

      // Node state changes
      es.addEventListener('node_state', (e) => {
        const data = JSON.parse(e.data);
        console.log('📥 node_state:', data);
        setNodeState(data.node_id, data.state);
        
        // Add log for state transitions
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
          
          // Ensure data.data is an array
          const chartData = Array.isArray(data.data) ? data.data : [];
          
          // Update display store with chart data
          // nodeId and timestamp are added automatically by the store
          useDisplayStore.getState().setNodeDisplayData(data.node_id, {
            chartType: data.chart_type || 'line',
            title: data.title || '',
            data: chartData,
            xLabel: data.x_label,
            yLabel: data.y_label,
            options: data.options,
          });
          
          addLog({
            level: 'info',
            message: `📊 Display updated: [${data.node_id}] - ${data.chart_type || 'line'} chart (${chartData.length} items)`,
            nodeId: data.node_id,
          });
        } catch (err) {
          console.error('❌ Error processing display_data:', err);
        }
      });

      // Connection opened
      es.onopen = () => {
        console.log('✅ SSE connected');
        setIsConnected(true);
        resolve();
      };

      // Connection error
      es.onerror = (error) => {
        console.error('❌ SSE error:', error);
        setIsConnected(false);
        
        // Only reject if we haven't connected yet
        if (es.readyState === EventSource.CONNECTING) {
          // Still trying to connect - wait
        } else if (es.readyState === EventSource.CLOSED) {
          addLog({ level: 'warning', message: '⚠️ Event stream disconnected' });
          reject(new Error('SSE connection failed'));
        }
      };
    });
  }, [setNodeState, setEdgeState, setRunning, addLog]);

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
