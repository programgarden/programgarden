import { useCallback, useRef, DragEvent } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  NodeTypes,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useWorkflowStore } from '@/stores/workflowStore';
import CustomNode from './CustomNode';
import DisplayNodeComponent from './DisplayNodeComponent';
import { getCategoryColor } from '@/utils/nodeColors';

const nodeTypes: NodeTypes = {
  customNode: CustomNode,
  displayNode: DisplayNodeComponent,
};

export default function WorkflowCanvas() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    selectNode,
    selectEdge,
    nodeTypes: registeredNodeTypes,
  } = useWorkflowStore();

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      event.stopPropagation();

      // Try multiple data formats for compatibility
      let nodeType = event.dataTransfer.getData('application/nodeType');
      if (!nodeType) {
        nodeType = event.dataTransfer.getData('text/plain');
      }
      const category = event.dataTransfer.getData('application/category') || 'group';

      console.log('Drop event:', { nodeType, category, clientX: event.clientX, clientY: event.clientY });

      if (!nodeType) {
        console.warn('No nodeType found in drag data');
        return;
      }

      // Use React Flow's screenToFlowPosition for accurate coordinates
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      console.log('Calculated position:', position);

      // Find schema for this node type
      const schema = registeredNodeTypes.find((t) => t.node_type === nodeType);
      addNode(nodeType, category, position, schema);
    },
    [addNode, registeredNodeTypes, screenToFlowPosition]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string }) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
    selectEdge(null);
  }, [selectNode, selectEdge]);

  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: { id: string }) => {
      selectEdge(edge.id);
    },
    [selectEdge]
  );

  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        deleteKeyCode={['Backspace', 'Delete']}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: false,
        }}
        className="bg-gray-900"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#374151"
        />
        <Controls className="!bg-gray-800 !border-gray-700 !rounded-lg" />
        <MiniMap
          nodeColor={(node) => getCategoryColor(node.data?.category as string || 'group')}
          maskColor="rgba(0, 0, 0, 0.8)"
          className="!bg-gray-800 !border-gray-700 !rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}
