import { useState, useEffect, useCallback, useRef } from 'react';
import { Play, Edit, ZoomIn, ZoomOut, Maximize, Download, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageContainer } from '@/components/layout/PageContainer';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { graphService, healthService } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import { GraphVisualization, type GraphVisualizationRef } from '@/components/GraphVisualization';
import { NodeDetailsPanel } from '@/components/NodeDetailsPanel';
import type { GraphData, GraphNode } from '@/types';

export default function Graph() {
  const { toast } = useToast();
  const graphVisualizationRef = useRef<GraphVisualizationRef>(null);
  const nodeDetailsPanelRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState('');
  const [cypher, setCypher] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodeLimit, setNodeLimit] = useState(100);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  const checkBackendHealth = useCallback(async () => {
    try {
      setBackendStatus('checking');
      const health = await healthService.check();
      if (health.neo4j_connected) {
        setBackendStatus('connected');
        toast({
          title: 'Backend connected',
          description: `Neo4j connected with ${health.node_count || 0} nodes`,
        });
      } else {
        setBackendStatus('disconnected');
        setError('Neo4j database not connected');
      }
    } catch (err) {
      setBackendStatus('disconnected');
      setError('Cannot connect to backend server. Is it running on localhost:8000?');
    }
  }, [toast]);

  const loadGraph = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await graphService.getGraphNodes(nodeLimit);
      setGraphData(data);
      toast({
        title: 'Graph loaded',
        description: `${data.nodes.length} nodes, ${data.links.length} relationships`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load graph';
      setError(message);
      toast({
        title: 'Error loading graph',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [nodeLimit, toast]);

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  // Load graph data on mount and when limit changes
  useEffect(() => {
    if (backendStatus === 'connected') {
      loadGraph();
    }
  }, [backendStatus, loadGraph]);

  const handleGenerateCypher = async () => {
    if (!query.trim()) {
      toast({
        title: 'Thiếu thông tin',
        description: 'Vui lòng nhập mô tả truy vấn',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    try {
      const result = await graphService.text2cypher(query);
      setCypher(result.cypher);
      toast({
        title: 'Thành công',
        description: 'Đã tạo Cypher query',
      });
    } catch (err) {
      toast({
        title: 'Lỗi',
        description: 'Không thể tạo Cypher query',
        variant: 'destructive',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExecute = async () => {
    if (!cypher.trim()) {
      toast({
        title: 'Thiếu thông tin',
        description: 'Vui lòng tạo hoặc nhập Cypher query',
        variant: 'destructive',
      });
      return;
    }

    setIsExecuting(true);
    try {
      const data = await graphService.execute(cypher);
      setGraphData(data);
      toast({
        title: 'Thành công',
        description: `Tìm thấy ${data.nodes.length} nodes và ${data.links.length} mối quan hệ`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không thể thực thi query';
      toast({
        title: 'Lỗi',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node);
    // Auto-scroll to node details panel
    setTimeout(() => {
      nodeDetailsPanelRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }, 100);
  };

  const handleExportJSON = () => {
    const dataStr = JSON.stringify(graphData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'graph-data.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageContainer maxWidth="full">
      <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-8rem)]">
        {/* Left Panel - Controls */}
        <div className="lg:w-[30%] space-y-4 overflow-y-auto">
          {/* Backend Status */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${
                    backendStatus === 'connected' ? 'bg-green-500' :
                    backendStatus === 'checking' ? 'bg-yellow-500 animate-pulse' :
                    'bg-red-500'
                  }`} />
                  <span className="text-sm">
                    {backendStatus === 'connected' ? 'Backend Connected' :
                     backendStatus === 'checking' ? 'Checking...' :
                     'Backend Disconnected'}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={checkBackendHealth}
                  disabled={backendStatus === 'checking'}
                >
                  <RefreshCw className={`h-4 w-4 ${backendStatus === 'checking' ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Graph Controls */}
          <Card>
            <CardHeader>
              <CardTitle>Điều khiển đồ thị</CardTitle>
              <CardDescription>
                Tải đồ thị Test_rel_2 từ Neo4j
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Số node tối đa: {nodeLimit}
                </label>
                <Slider
                  value={[nodeLimit]}
                  onValueChange={(v) => setNodeLimit(v[0])}
                  min={10}
                  max={500}
                  step={10}
                  className="mt-2"
                />
              </div>

              <Button
                onClick={loadGraph}
                disabled={isLoading || backendStatus !== 'connected'}
                className="w-full"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                {isLoading ? 'Đang tải...' : 'Tải đồ thị'}
              </Button>
            </CardContent>
          </Card>

          {/* Cypher Query */}
          <Card>
            <CardHeader>
              <CardTitle>Truy vấn Cypher</CardTitle>
              <CardDescription>
                Mô tả bằng tiếng Việt hoặc viết Cypher query trực tiếp
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Mô tả truy vấn
                </label>
                <Textarea
                  placeholder="Ví dụ: Tìm tất cả điều khoản về thuế GTGT..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  rows={3}
                  className="resize-none"
                />
              </div>

              <Button
                onClick={handleGenerateCypher}
                disabled={isGenerating || backendStatus !== 'connected'}
                className="w-full"
                variant="secondary"
              >
                {isGenerating ? 'Đang tạo...' : 'Sinh Cypher'}
              </Button>

              {cypher && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium">Cypher Query</label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEditing(!isEditing)}
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      {isEditing ? 'Xem' : 'Chỉnh sửa'}
                    </Button>
                  </div>
                  {isEditing ? (
                    <Textarea
                      value={cypher}
                      onChange={(e) => setCypher(e.target.value)}
                      rows={6}
                      className="font-mono text-sm resize-none"
                    />
                  ) : (
                    <div className="p-3 bg-muted rounded-md font-mono text-sm whitespace-pre-wrap break-all">
                      {cypher}
                    </div>
                  )}
                </div>
              )}

              <Button
                onClick={handleExecute}
                disabled={isExecuting || !cypher || backendStatus !== 'connected'}
                className="w-full bg-success hover:bg-success/90"
              >
                <Play className="h-4 w-4 mr-2" />
                {isExecuting ? 'Đang chạy...' : 'Chạy Query'}
              </Button>
            </CardContent>
          </Card>

          {/* Node Details - Enhanced Panel */}
          {selectedNode && (
            <div ref={nodeDetailsPanelRef}>
              <NodeDetailsPanel node={selectedNode} />
            </div>
          )}

          {/* Legend */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Chú giải</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#4ecdc4' }} />
                <span className="text-sm">Văn bản (document)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#45b7d1' }} />
                <span className="text-sm">Điều khoản (article)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#96ceb4' }} />
                <span className="text-sm">Loại thuế (tax_type)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#ffeaa7' }} />
                <span className="text-sm">Đối tượng nộp thuế (taxpayer)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#ff6b6b' }} />
                <span className="text-sm">Node đang chọn</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Graph Visualization */}
        <Card className="lg:w-[70%] relative">
          <CardContent className="h-full p-0">
            {/* Error Display */}
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
                <div className="text-center space-y-4 p-8">
                  <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
                  <p className="text-lg font-medium text-destructive">{error}</p>
                  <Button onClick={checkBackendHealth} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry Connection
                  </Button>
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoading && !error && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                <div className="text-center space-y-2">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
                  <p className="text-sm text-muted-foreground">Loading graph...</p>
                </div>
              </div>
            )}

            {/* Graph Canvas */}
            <div className="w-full h-full">
              <GraphVisualization
                ref={graphVisualizationRef}
                data={graphData}
                onNodeClick={handleNodeClick}
                height={600}
              />
            </div>

            {/* Floating Controls - Now Functional */}
            <div className="absolute top-4 right-4 flex gap-2">
              <Button
                variant="secondary"
                size="icon"
                title="Zoom In"
                aria-label="Zoom in"
                onClick={() => graphVisualizationRef.current?.zoomIn()}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                size="icon"
                title="Zoom Out"
                aria-label="Zoom out"
                onClick={() => graphVisualizationRef.current?.zoomOut()}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button
                variant="secondary"
                size="icon"
                title="Fit to Screen"
                aria-label="Fit to screen"
                onClick={() => graphVisualizationRef.current?.zoomToFit()}
              >
                <Maximize className="h-4 w-4" />
              </Button>
            </div>

            {/* Graph Stats */}
            <div className="absolute bottom-4 left-4 flex gap-4">
              <Badge variant="outline" className="bg-background">
                {graphData.nodes.length} nodes
              </Badge>
              <Badge variant="outline" className="bg-background">
                {graphData.links.length} relationships
              </Badge>
            </div>

            {/* Export Buttons */}
            {graphData.nodes.length > 0 && (
              <div className="absolute bottom-4 right-4 flex gap-2">
                <Button variant="secondary" size="sm" onClick={handleExportJSON}>
                  <Download className="h-4 w-4 mr-2" />
                  JSON
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
