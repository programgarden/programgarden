/**
 * ProgramGarden Flow Visualizer - Main App
 * 
 * Handles:
 * - Workflow rendering (nodes/edges)
 * - SSE event subscription
 * - State updates and animations
 */

// ========================================
// Configuration
// ========================================

const CONFIG = {
    // Set to 0 for real-time updates (production)
    // Set to 500+ for debugging/demo purposes
    EVENT_DELAY: 0,
    NODE_STATE_DELAY: 0,
    EDGE_STATE_DELAY: 0,
};

// ========================================
// State
// ========================================

const state = {
    workflow: null,
    eventSource: null,
    nodeStates: {},
    edgeStates: {},
    isRunning: false,
    // Event queue for sequential processing with delays
    eventQueue: [],
    isProcessingQueue: false,
    // Zoom state
    zoom: 0.6,  // Start at 60% zoom
    // Display outputs from DisplayNodes
    displayOutputs: {},
};

// ========================================
// DOM Elements
// ========================================

const elements = {
    btnRun: document.getElementById('btn-run'),
    btnStop: document.getElementById('btn-stop'),
    btnClearLog: document.getElementById('btn-clear-log'),
    btnZoomIn: document.getElementById('btn-zoom-in'),
    btnZoomOut: document.getElementById('btn-zoom-out'),
    btnZoomFit: document.getElementById('btn-zoom-fit'),
    zoomLevel: document.getElementById('zoom-level'),
    jobStatus: document.getElementById('job-status'),
    flowCanvas: document.getElementById('flow-canvas'),
    flowViewport: document.getElementById('flow-viewport'),
    edgesSvg: document.getElementById('edges-svg'),
    nodesContainer: document.getElementById('nodes-container'),
    logContainer: document.getElementById('log-container'),
    connectionStatus: document.getElementById('connection-status'),
};

// ========================================
// Initialization
// ========================================

async function init() {
    // Load workflow
    await loadWorkflow();
    
    // Setup event listeners
    setupEventListeners();
    
    // Connect to SSE
    connectSSE();
    
    // Apply initial zoom
    applyZoom();
}

async function loadWorkflow() {
    try {
        const response = await fetch('/workflow');
        state.workflow = await response.json();
        renderWorkflow();
        log('Workflow loaded', 'info');
    } catch (error) {
        log(`Failed to load workflow: ${error.message}`, 'error');
    }
}

function setupEventListeners() {
    elements.btnRun.addEventListener('click', runWorkflow);
    elements.btnStop.addEventListener('click', stopWorkflow);
    elements.btnClearLog.addEventListener('click', clearLog);
    
    // Zoom controls
    elements.btnZoomIn.addEventListener('click', () => setZoom(state.zoom + 0.1));
    elements.btnZoomOut.addEventListener('click', () => setZoom(state.zoom - 0.1));
    elements.btnZoomFit.addEventListener('click', zoomToFit);
    
    // Mouse wheel zoom
    elements.flowCanvas.addEventListener('wheel', (e) => {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            setZoom(state.zoom + delta);
        }
    });
}

// ========================================
// Zoom Functions
// ========================================

function setZoom(newZoom) {
    state.zoom = Math.max(0.2, Math.min(1.5, newZoom));
    applyZoom();
}

function applyZoom() {
    if (elements.flowViewport) {
        elements.flowViewport.style.transform = `scale(${state.zoom})`;
    }
    if (elements.zoomLevel) {
        elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
    }
}

function zoomToFit() {
    const canvas = elements.flowCanvas.getBoundingClientRect();
    const viewport = elements.flowViewport;
    if (!viewport) return;
    
    // Calculate required zoom to fit content
    const contentWidth = 1200;  // min-width from CSS
    const contentHeight = 800;  // min-height from CSS
    const scaleX = canvas.width / contentWidth;
    const scaleY = canvas.height / contentHeight;
    const fitZoom = Math.min(scaleX, scaleY, 1) * 0.9;  // 90% to add padding
    
    setZoom(fitZoom);
}

// ========================================
// SSE Connection
// ========================================

function connectSSE() {
    if (state.eventSource) {
        state.eventSource.close();
    }

    state.eventSource = new EventSource('/events');
    
    state.eventSource.onopen = () => {
        setConnectionStatus(true);
        log('Connected to event stream', 'success');
    };

    state.eventSource.onerror = () => {
        setConnectionStatus(false);
        log('Event stream disconnected, reconnecting...', 'warning');
        // EventSource automatically reconnects
    };

    // Event handlers - queue events for sequential processing
    state.eventSource.addEventListener('node_state', (e) => queueEvent('node_state', e));
    state.eventSource.addEventListener('edge_state', (e) => queueEvent('edge_state', e));
    state.eventSource.addEventListener('log', handleLogEvent);  // Logs don't need delay
    state.eventSource.addEventListener('job_state', handleJobState);  // Job state immediate
}

function setConnectionStatus(connected) {
    elements.connectionStatus.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
    elements.connectionStatus.textContent = connected ? '● Connected' : '● Disconnected';
}

// ========================================
// Event Queue (for visual delays)
// ========================================

function queueEvent(type, event) {
    state.eventQueue.push({ type, event });
    processEventQueue();
}

async function processEventQueue() {
    // Prevent concurrent processing
    if (state.isProcessingQueue) return;
    state.isProcessingQueue = true;
    
    while (state.eventQueue.length > 0) {
        const { type, event } = state.eventQueue.shift();
        
        if (type === 'node_state') {
            await processNodeState(event);
            await delay(CONFIG.NODE_STATE_DELAY);
        } else if (type === 'edge_state') {
            await processEdgeState(event);
            await delay(CONFIG.EDGE_STATE_DELAY);
        }
        
        // Base delay between events
        await delay(CONFIG.EVENT_DELAY);
    }
    
    state.isProcessingQueue = false;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ========================================
// Event Handlers
// ========================================

async function processNodeState(event) {
    const data = JSON.parse(event.data);
    const { node_id, node_type, state: nodeState, outputs, error } = data;
    
    state.nodeStates[node_id] = nodeState;
    updateNodeVisual(node_id, nodeState);
    
    const stateEmoji = {
        'pending': '⏳',
        'running': '🔄',
        'completed': '✅',
        'failed': '❌',
        'skipped': '⏭️'
    };
    
    let message = `${stateEmoji[nodeState] || '•'} Node [${node_id}] → ${nodeState.toUpperCase()}`;
    if (error) message += ` (${error})`;
    
    log(message, 'node');
    
    // Capture DisplayNode outputs for rendering
    if (node_type === 'DisplayNode' && nodeState === 'completed' && outputs) {
        state.displayOutputs[node_id] = outputs;
        renderDisplayOutputs();
    }
}

async function processEdgeState(event) {
    const data = JSON.parse(event.data);
    const { from_node, to_node, state: edgeState } = data;
    
    const edgeKey = `${from_node}->${to_node}`;
    state.edgeStates[edgeKey] = edgeState;
    updateEdgeVisual(from_node, to_node, edgeState);
    
    if (edgeState === 'transmitting') {
        log(`📤 Edge [${from_node}] → [${to_node}] transmitting...`, 'edge');
    } else if (edgeState === 'transmitted') {
        log(`📥 Edge [${from_node}] → [${to_node}] transmitted`, 'edge');
    }
}

function handleLogEvent(event) {
    const data = JSON.parse(event.data);
    const { message, level } = data;
    log(message, level || 'info');
}

function handleJobState(event) {
    const data = JSON.parse(event.data);
    const { status, job_id } = data;
    
    updateJobStatus(status);
    log(`📋 Job [${job_id || 'unknown'}] status: ${status.toUpperCase()}`, 'info');
    
    if (status === 'completed' || status === 'failed' || status === 'stopped') {
        state.isRunning = false;
        elements.btnRun.disabled = false;
        elements.btnStop.disabled = true;
    }
}

// ========================================
// Workflow Rendering
// ========================================

/**
 * Extract node ID from edge port string.
 * "start.start" -> "start"
 * "broker.connected" -> "broker"
 * "broker" -> "broker"
 */
function getNodeId(edgePort) {
    return edgePort.split('.')[0];
}

function renderWorkflow() {
    if (!state.workflow) return;
    
    const { nodes, edges } = state.workflow;
    
    // Calculate node positions (simple grid layout)
    const positions = calculateNodePositions(nodes, edges);
    
    // Clear existing
    elements.nodesContainer.innerHTML = '';
    elements.edgesSvg.innerHTML = '';
    
    // Define arrow marker
    elements.edgesSvg.innerHTML = `
        <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" 
                    refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" class="edge-arrow" />
            </marker>
        </defs>
    `;
    
    // Render edges first (below nodes)
    edges.forEach(edge => {
        const fromNodeId = getNodeId(edge.from);
        const toNodeId = getNodeId(edge.to);
        const fromPos = positions[fromNodeId];
        const toPos = positions[toNodeId];
        if (fromPos && toPos) {
            renderEdge(edge, fromPos, toPos, fromNodeId, toNodeId);
        }
    });
    
    // Render nodes
    nodes.forEach(node => {
        const pos = positions[node.id];
        if (pos) {
            renderNode(node, pos);
        }
    });
}

function calculateNodePositions(nodes, edges) {
    // Simple topological layout
    const positions = {};
    const levels = {};
    const processed = new Set();
    
    // Parse node IDs from edges (handle "node.port" format)
    const edgeFromNodes = edges.map(e => getNodeId(e.from));
    const edgeToNodes = edges.map(e => getNodeId(e.to));
    
    // Find roots (nodes with no incoming edges)
    const hasIncoming = new Set(edgeToNodes);
    const roots = nodes.filter(n => !hasIncoming.has(n.id)).map(n => n.id);
    
    // Build adjacency from edges
    const adjacency = {};
    edges.forEach(e => {
        const from = getNodeId(e.from);
        const to = getNodeId(e.to);
        if (!adjacency[from]) adjacency[from] = [];
        if (!adjacency[from].includes(to)) adjacency[from].push(to);
    });
    
    // BFS to assign levels
    const queue = roots.map(id => ({ id, level: 0 }));
    while (queue.length > 0) {
        const { id, level } = queue.shift();
        if (processed.has(id)) continue;
        
        processed.add(id);
        levels[id] = level;
        
        // Find children using adjacency
        const children = adjacency[id] || [];
        children.forEach(childId => {
            if (!processed.has(childId)) {
                queue.push({ id: childId, level: level + 1 });
            }
        });
    }
    
    // Group by level
    const byLevel = {};
    Object.entries(levels).forEach(([id, level]) => {
        if (!byLevel[level]) byLevel[level] = [];
        byLevel[level].push(id);
    });
    
    // Calculate positions
    const nodeWidth = 160;
    const nodeHeight = 60;
    const displayNodeWidth = 280;  // Wider for DisplayNode
    const displayNodeHeight = 200; // Taller for DisplayNode
    const horizontalGap = 80;
    const verticalGap = 40;
    
    const padding = 80;  // Left padding to prevent negative positions
    
    // First pass: calculate positions
    let minX = Infinity;
    const tempPositions = {};
    
    Object.entries(byLevel).forEach(([level, nodeIds]) => {
        const y = 60 + Number(level) * (nodeHeight + verticalGap);
        const totalWidth = nodeIds.length * nodeWidth + (nodeIds.length - 1) * horizontalGap;
        const startX = padding + (nodeIds.length > 1 ? 0 : 200);  // Center single nodes more
        
        nodeIds.forEach((id, index) => {
            const node = nodes.find(n => n.id === id);
            const isDisplayNode = node?.type === 'DisplayNode';
            const w = isDisplayNode ? displayNodeWidth : nodeWidth;
            const h = isDisplayNode ? displayNodeHeight : nodeHeight;
            
            const x = startX + index * (nodeWidth + horizontalGap);
            tempPositions[id] = { x, y, width: w, height: h };
            minX = Math.min(minX, x);
        });
    });
    
    // Second pass: shift all positions to ensure no negative x
    const shiftX = minX < padding ? (padding - minX) : 0;
    Object.keys(tempPositions).forEach(id => {
        positions[id] = {
            ...tempPositions[id],
            x: tempPositions[id].x + shiftX
        };
    });
    
    return positions;
}

function renderNode(node, pos) {
    const div = document.createElement('div');
    const isDisplayNode = node.type === 'DisplayNode';
    div.className = `node pending ${isDisplayNode ? 'display-node' : ''}`;
    div.id = `node-${node.id}`;
    div.style.left = `${pos.x}px`;
    div.style.top = `${pos.y}px`;
    div.style.width = `${pos.width}px`;
    if (isDisplayNode) {
        div.style.height = `${pos.height}px`;
    }
    
    const title = node.title || node.id;
    div.innerHTML = `
        <div class="node-header">
            <div class="node-id">${title}</div>
            <div class="node-type">${node.type}</div>
        </div>
        ${isDisplayNode ? '<div class="node-data-container"><div class="node-data-placeholder">Waiting for data...</div></div>' : ''}
    `;
    
    elements.nodesContainer.appendChild(div);
}

function renderEdge(edge, fromPos, toPos, fromNodeId, toNodeId) {
    // Calculate connection points
    const startX = fromPos.x + fromPos.width / 2;
    const startY = fromPos.y + fromPos.height;
    const endX = toPos.x + toPos.width / 2;
    const endY = toPos.y;
    
    // Create curved path
    const midY = (startY + endY) / 2;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`);
    path.setAttribute('class', 'edge idle');
    path.setAttribute('marker-end', 'url(#arrow)');
    // Use node IDs for edge ID (for state updates from server)
    path.id = `edge-${fromNodeId}-${toNodeId}`;
    
    elements.edgesSvg.appendChild(path);
}

function updateNodeVisual(nodeId, nodeState) {
    const node = document.getElementById(`node-${nodeId}`);
    if (!node) return;
    
    // Remove all state classes
    node.classList.remove('pending', 'running', 'completed', 'failed', 'skipped');
    // Add new state
    node.classList.add(nodeState);
}

function updateEdgeVisual(fromNode, toNode, edgeState) {
    const edge = document.getElementById(`edge-${fromNode}-${toNode}`);
    if (!edge) return;
    
    edge.classList.remove('idle', 'transmitting', 'transmitted');
    edge.classList.add(edgeState);
}

// ========================================
// Workflow Control
// ========================================

async function runWorkflow() {
    try {
        // Reset states
        resetStates();
        
        elements.btnRun.disabled = true;
        elements.btnStop.disabled = false;
        state.isRunning = true;
        
        log('Starting workflow...', 'info');
        
        const response = await fetch('/run', { method: 'POST' });
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        log(`Job started: ${result.jobId}`, 'success');
        updateJobStatus('running');
        
    } catch (error) {
        log(`Failed to start: ${error.message}`, 'error');
        elements.btnRun.disabled = false;
        elements.btnStop.disabled = true;
        state.isRunning = false;
    }
}

async function stopWorkflow() {
    try {
        log('Stopping workflow...', 'warning');
        
        const response = await fetch('/stop', { method: 'POST' });
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        log(`Job stopped: ${result.jobId}`, 'warning');
        
    } catch (error) {
        log(`Failed to stop: ${error.message}`, 'error');
    }
}

function resetStates() {
    // Reset node visuals
    document.querySelectorAll('.node').forEach(node => {
        node.classList.remove('running', 'completed', 'failed', 'skipped');
        node.classList.add('pending');
    });
    
    // Reset edge visuals
    document.querySelectorAll('.edge').forEach(edge => {
        edge.classList.remove('transmitting', 'transmitted');
        edge.classList.add('idle');
    });
    
    // Reset state tracking
    state.nodeStates = {};
    state.edgeStates = {};
}

function updateJobStatus(status) {
    const element = elements.jobStatus;
    element.className = `status-badge status-${status}`;
    element.textContent = status.toUpperCase();
}

// ========================================
// Logging
// ========================================

function log(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${escapeHtml(message)}`;
    
    elements.logContainer.appendChild(entry);
    
    // Auto-scroll to bottom
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
}

function clearLog() {
    elements.logContainer.innerHTML = '';
    log('Log cleared', 'info');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================================
// Display Outputs Rendering (inside node boxes)
// ========================================

function renderDisplayOutputs() {
    // Render data directly inside DisplayNode boxes
    const outputs = state.displayOutputs;
    
    for (const [nodeId, data] of Object.entries(outputs)) {
        const nodeElement = document.getElementById(`node-${nodeId}`);
        if (!nodeElement) continue;
        
        const container = nodeElement.querySelector('.node-data-container');
        if (!container) continue;
        
        // Render data into the node's data container
        container.innerHTML = renderDisplayData(data);
    }
}

function renderDisplayData(data) {
    // Handle different data types
    if (!data) {
        return '<div class="display-placeholder">No data</div>';
    }
    
    // Check chart_type from backend
    const chartType = data.chart_type || 'table';
    const title = data.title || '';
    
    // Line chart rendering
    if (chartType === 'line') {
        const chartData = data.chart_data || data.data || [];
        return renderLineChart(chartData, data.options || {});
    }
    
    // Table rendering
    const tableData = data.table_data || data.data || data.result || data.summary || data;
    
    // Array of objects → table
    if (Array.isArray(tableData) && tableData.length > 0 && typeof tableData[0] === 'object') {
        return renderTable(tableData);
    }
    
    // Single object → key-value table
    if (typeof tableData === 'object' && !Array.isArray(tableData)) {
        return renderKeyValueTable(tableData);
    }
    
    // Primitive or unknown → JSON
    return `<pre style="font-size: 0.75rem; overflow: auto;">${escapeHtml(JSON.stringify(tableData, null, 2))}</pre>`;
}

// Global chart instances to destroy before recreating
const chartInstances = {};

function renderLineChart(data, options) {
    if (!data || (Array.isArray(data) && data.length === 0)) {
        return '<div class="display-placeholder">No chart data</div>';
    }
    
    // Generate unique canvas ID
    const canvasId = 'chart-' + Math.random().toString(36).substr(2, 9);
    
    // Schedule chart creation after DOM update
    setTimeout(() => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Destroy existing chart if any
        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy();
        }
        
        // Prepare data for Chart.js
        let labels, values, benchmarkValues;
        
        if (Array.isArray(data)) {
            // Array format: [{date: '2025-01-01', value: 100}, ...]
            labels = data.map(d => d.date || d.timestamp || d.x || '');
            values = data.map(d => d.portfolio_value || d.value || d.y || d);
            if (data[0]?.benchmark) {
                benchmarkValues = data.map(d => d.benchmark);
            }
        } else if (typeof data === 'object') {
            // Object format: {dates: [...], values: [...]}
            labels = data.dates || data.labels || Object.keys(data);
            values = data.values || data.portfolio_value || Object.values(data);
            benchmarkValues = data.benchmark;
        }
        
        const datasets = [{
            label: options.y_axis || 'Portfolio Value',
            data: values,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            fill: true,
            tension: 0.1,
        }];
        
        if (benchmarkValues && options.show_benchmark) {
            datasets.push({
                label: 'Benchmark',
                data: benchmarkValues,
                borderColor: 'rgb(255, 159, 64)',
                backgroundColor: 'rgba(255, 159, 64, 0.1)',
                fill: false,
                tension: 0.1,
                borderDash: [5, 5],
            });
        }
        
        chartInstances[canvasId] = new Chart(canvas, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: datasets.length > 1, position: 'top' },
                },
                scales: {
                    x: { display: true, title: { display: true, text: options.x_axis || 'Date' } },
                    y: { display: true, title: { display: true, text: options.y_axis || 'Value' } },
                },
            },
        });
    }, 0);
    
    return `<div style="height: 150px; width: 100%;"><canvas id="${canvasId}"></canvas></div>`;
}

function renderTable(rows) {
    if (!rows || rows.length === 0) return '<div class="display-placeholder">No rows</div>';
    
    const columns = Object.keys(rows[0]);
    
    let html = '<table class="display-table">';
    html += '<thead><tr>';
    for (const col of columns) {
        html += `<th>${escapeHtml(col)}</th>`;
    }
    html += '</tr></thead>';
    
    html += '<tbody>';
    for (const row of rows.slice(0, 20)) {  // Limit to 20 rows
        html += '<tr>';
        for (const col of columns) {
            const value = row[col];
            const formatted = formatValue(value, col);
            html += `<td class="${formatted.className}">${formatted.text}</td>`;
        }
        html += '</tr>';
    }
    html += '</tbody></table>';
    
    if (rows.length > 20) {
        html += `<div class="display-placeholder">... and ${rows.length - 20} more rows</div>`;
    }
    
    return html;
}

function renderKeyValueTable(obj) {
    let html = '<table class="display-table">';
    html += '<thead><tr><th>Key</th><th>Value</th></tr></thead>';
    html += '<tbody>';
    
    for (const [key, value] of Object.entries(obj)) {
        const formatted = formatValue(value, key);
        html += `<tr><td>${escapeHtml(key)}</td><td class="${formatted.className}">${formatted.text}</td></tr>`;
    }
    
    html += '</tbody></table>';
    return html;
}

function formatValue(value, key) {
    // Format numeric values with colors for PnL
    if (typeof value === 'number') {
        const isPercentField = key.toLowerCase().includes('rate') || key.toLowerCase().includes('percent') || key.toLowerCase().includes('return');
        const isPnlField = key.toLowerCase().includes('pnl') || key.toLowerCase().includes('profit') || key.toLowerCase().includes('loss');
        
        let text;
        if (isPercentField) {
            text = (value * (Math.abs(value) < 1 ? 100 : 1)).toFixed(2) + '%';
        } else if (Number.isInteger(value)) {
            text = value.toLocaleString();
        } else {
            text = value.toFixed(4);
        }
        
        let className = '';
        if (isPnlField || isPercentField) {
            className = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
        }
        
        return { text, className };
    }
    
    if (value === null || value === undefined) {
        return { text: '-', className: '' };
    }
    
    if (typeof value === 'object') {
        return { text: JSON.stringify(value), className: '' };
    }
    
    return { text: String(value), className: '' };
}

// ========================================
// Start
// ========================================

document.addEventListener('DOMContentLoaded', init);
