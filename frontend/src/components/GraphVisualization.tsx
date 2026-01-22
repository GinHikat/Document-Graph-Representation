import { useEffect, useRef, useState, useCallback, useMemo, useImperativeHandle, forwardRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { GraphData, GraphNode, GraphLink } from '@/types';

// Type for ForceGraph2D ref methods
interface ForceGraphMethods {
  zoomToFit: (duration?: number, padding?: number) => void;
  zoom: (scale?: number, duration?: number) => number;
  centerAt: (x?: number, y?: number, duration?: number) => void;
}

// Exposed methods for parent components
export interface GraphVisualizationRef {
  zoomIn: () => void;
  zoomOut: () => void;
  zoomToFit: () => void;
  getZoomLevel: () => number;
}

interface GraphVisualizationProps {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
  onNodeHover?: (node: GraphNode | null) => void;
  height?: number;
  width?: number;
}

// Color map for different node types
const NODE_COLORS: Record<string, string> = {
  document: '#4ecdc4',
  article: '#45b7d1',
  tax_type: '#96ceb4',
  taxpayer: '#ffeaa7',
  exemption: '#dfe6e9',
  default: '#95a5a6',
  highlighted: '#ff6b6b',
};

// Transform data for react-force-graph (it needs mutable objects)
interface GraphNodeInternal extends GraphNode {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphLinkInternal {
  source: string | GraphNodeInternal;
  target: string | GraphNodeInternal;
  type: string;
  properties?: Record<string, unknown>;
}

interface GraphDataInternal {
  nodes: GraphNodeInternal[];
  links: GraphLinkInternal[];
}

export const GraphVisualization = forwardRef<GraphVisualizationRef, GraphVisualizationProps>(({
  data,
  onNodeClick,
  onNodeHover,
  height = 600,
  width,
}, ref) => {
  const graphRef = useRef<ForceGraphMethods | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [currentZoom, setCurrentZoom] = useState<number>(1);

  // Expose zoom methods to parent
  useImperativeHandle(ref, () => ({
    zoomIn: () => {
      if (graphRef.current) {
        const newZoom = currentZoom * 1.3;
        graphRef.current.zoom(newZoom, 300);
        setCurrentZoom(newZoom);
      }
    },
    zoomOut: () => {
      if (graphRef.current) {
        const newZoom = currentZoom / 1.3;
        graphRef.current.zoom(newZoom, 300);
        setCurrentZoom(newZoom);
      }
    },
    zoomToFit: () => {
      if (graphRef.current) {
        graphRef.current.zoomToFit(400, 50);
      }
    },
    getZoomLevel: () => currentZoom,
  }), [currentZoom]);

  // Transform data for force graph
  const graphData: GraphDataInternal = useMemo(() => ({
    nodes: data.nodes.map(n => ({ ...n })),
    links: data.links.map(l => ({
      source: l.source,
      target: l.target,
      type: l.type,
      properties: l.properties,
    })),
  }), [data]);

  // Handle container resize
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Center graph on mount/data change
  useEffect(() => {
    if (graphRef.current && data.nodes.length > 0) {
      setTimeout(() => {
        graphRef.current?.zoomToFit(400, 50);
      }, 500);
    }
  }, [data]);

  const handleNodeClick = useCallback((node: GraphNodeInternal) => {
    setHighlightNodes(new Set([node.id]));
    if (onNodeClick) {
      onNodeClick(node as GraphNode);
    }
  }, [onNodeClick]);

  const handleNodeHover = useCallback((node: GraphNodeInternal | null) => {
    if (onNodeHover) {
      onNodeHover(node as GraphNode | null);
    }
  }, [onNodeHover]);

  const getNodeColor = useCallback((node: GraphNodeInternal): string => {
    if (highlightNodes.has(node.id)) {
      return NODE_COLORS.highlighted;
    }
    return NODE_COLORS[node.type] || NODE_COLORS.default;
  }, [highlightNodes]);

  const getNodeSize = useCallback((node: GraphNodeInternal): number => {
    // Calculate size based on number of connections
    const connections = graphData.links.filter(
      l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return sourceId === node.id || targetId === node.id;
      }
    ).length;
    return Math.max(4, Math.min(12, 4 + connections));
  }, [graphData.links]);

  const nodeCanvasObject = useCallback((
    node: GraphNodeInternal,
    ctx: CanvasRenderingContext2D,
    globalScale: number
  ) => {
    const label = node.label || node.id;
    const fontSize = Math.max(10 / globalScale, 2);
    const nodeSize = getNodeSize(node);

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x || 0, node.y || 0, nodeSize, 0, 2 * Math.PI);
    ctx.fillStyle = getNodeColor(node);
    ctx.fill();

    // Draw border
    ctx.strokeStyle = highlightNodes.has(node.id) ? '#c0392b' : '#2c3e50';
    ctx.lineWidth = highlightNodes.has(node.id) ? 2 / globalScale : 1 / globalScale;
    ctx.stroke();

    // Draw label only when zoomed in enough
    if (globalScale > 0.5) {
      ctx.font = `${fontSize}px Sans-Serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Truncate label if too long
      const maxLength = 20;
      const displayLabel = label.length > maxLength
        ? label.substring(0, maxLength) + '...'
        : label;

      // Draw label background
      const textWidth = ctx.measureText(displayLabel).width;
      const padding = 2 / globalScale;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.fillRect(
        (node.x || 0) - textWidth / 2 - padding,
        (node.y || 0) + nodeSize + 2 / globalScale,
        textWidth + padding * 2,
        fontSize + padding
      );

      // Draw label text
      ctx.fillStyle = '#2c3e50';
      ctx.fillText(
        displayLabel,
        node.x || 0,
        (node.y || 0) + nodeSize + fontSize / 2 + 4 / globalScale
      );
    }
  }, [getNodeColor, getNodeSize, highlightNodes]);

  const linkCanvasObject = useCallback((
    link: GraphLinkInternal,
    ctx: CanvasRenderingContext2D,
    globalScale: number
  ) => {
    const source = link.source as GraphNodeInternal;
    const target = link.target as GraphNodeInternal;

    if (!source.x || !source.y || !target.x || !target.y) return;

    // Draw line
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.strokeStyle = 'rgba(100, 100, 100, 0.5)';
    ctx.lineWidth = 1 / globalScale;
    ctx.stroke();

    // Draw arrow
    const arrowLength = 6 / globalScale;
    const angle = Math.atan2(target.y - source.y, target.x - source.x);
    const nodeRadius = 6;
    const endX = target.x - nodeRadius * Math.cos(angle);
    const endY = target.y - nodeRadius * Math.sin(angle);

    ctx.beginPath();
    ctx.moveTo(endX, endY);
    ctx.lineTo(
      endX - arrowLength * Math.cos(angle - Math.PI / 6),
      endY - arrowLength * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
      endX - arrowLength * Math.cos(angle + Math.PI / 6),
      endY - arrowLength * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fillStyle = 'rgba(100, 100, 100, 0.7)';
    ctx.fill();
  }, []);

  if (data.nodes.length === 0) {
    return (
      <div
        ref={containerRef}
        className="w-full flex items-center justify-center bg-muted/20 rounded-lg"
        style={{ height }}
      >
        <p className="text-muted-foreground">No graph data available</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full" style={{ height }}>
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={width || containerWidth}
        height={height}
        nodeLabel={(node: GraphNodeInternal) => `${node.label}\nType: ${node.type}`}
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        nodePointerAreaPaint={(node: GraphNodeInternal, color, ctx) => {
          const size = getNodeSize(node);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x || 0, node.y || 0, size + 2, 0, 2 * Math.PI);
          ctx.fill();
        }}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />
    </div>
  );
});

GraphVisualization.displayName = 'GraphVisualization';

export default GraphVisualization;
