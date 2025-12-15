import { useState } from 'react';
import { Search, ChevronDown, ChevronRight, Clock, Database, Target, Loader2, Zap, Radio } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageContainer } from '@/components/layout/PageContainer';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useQAStore } from '@/stores/qaStore';
import { useToast } from '@/hooks/use-toast';
import { Separator } from '@/components/ui/separator';

const EXAMPLE_QUESTIONS = [
  'Thuế suất VAT cho dịch vụ giáo dục?',
  'Điều kiện được miễn thuế thu nhập cá nhân?',
  'Thời hạn nộp thuế GTGT hàng tháng?',
  'Cách tính thuế thu nhập doanh nghiệp?',
];

export default function QA() {
  const { toast } = useToast();
  const {
    currentQuestion,
    results,
    isLoading,
    streaming,
    setCurrentQuestion,
    compare,
    compareStreaming,
    submitAnnotation,
  } = useQAStore();

  const [selectedPreference, setSelectedPreference] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);
  const [vectorSourcesOpen, setVectorSourcesOpen] = useState(false);
  const [graphSourcesOpen, setGraphSourcesOpen] = useState(false);
  const [cypherOpen, setCypherOpen] = useState(false);
  const [graphContextOpen, setGraphContextOpen] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);

  const handleCompare = async () => {
    if (!currentQuestion.trim()) {
      toast({
        title: 'Thiếu thông tin',
        description: 'Vui lòng nhập câu hỏi',
        variant: 'destructive',
      });
      return;
    }

    if (useStreaming) {
      await compareStreaming(currentQuestion);
    } else {
      await compare(currentQuestion);
    }
  };

  const handleSubmitAnnotation = async () => {
    if (!selectedPreference || !results) return;

    try {
      await submitAnnotation(results.questionId, selectedPreference, comment);
      toast({
        title: 'Thành công',
        description: 'Đã lưu đánh giá của bạn',
      });
      setSelectedPreference(null);
      setComment('');
      setShowComment(false);
    } catch (error) {
      toast({
        title: 'Lỗi',
        description: 'Không thể lưu đánh giá',
        variant: 'destructive',
      });
    }
  };

  return (
    <PageContainer maxWidth="full">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">So sánh Q&A</h1>
          <p className="text-muted-foreground mt-1">
            Đánh giá và so sánh Vector Search vs Graph-enhanced Search
          </p>
        </div>

        {/* Question Input */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div>
                <Textarea
                  placeholder="Nhập câu hỏi về thuế Việt Nam..."
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  rows={3}
                  className="resize-none text-lg"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <span className="text-sm text-muted-foreground">Ví dụ:</span>
                {EXAMPLE_QUESTIONS.map((q) => (
                  <Badge
                    key={q}
                    variant="secondary"
                    className="cursor-pointer hover:bg-secondary/80"
                    onClick={() => setCurrentQuestion(q)}
                  >
                    {q}
                  </Badge>
                ))}
              </div>

              <Button
                onClick={handleCompare}
                disabled={isLoading}
                size="lg"
                className="w-full"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    {streaming.isStreaming ? 'Đang truyền...' : 'Đang xử lý...'}
                  </>
                ) : (
                  <>
                    <Search className="h-5 w-5 mr-2" />
                    So sánh
                  </>
                )}
              </Button>

              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="streaming-mode"
                    checked={useStreaming}
                    onCheckedChange={setUseStreaming}
                  />
                  <Label htmlFor="streaming-mode" className="text-sm flex items-center gap-1">
                    <Zap className="h-4 w-4" />
                    Streaming mode
                  </Label>
                </div>
                {streaming.isStreaming && streaming.currentTool && (
                  <Badge variant="outline" className="animate-pulse">
                    <Radio className="h-3 w-3 mr-1" />
                    {streaming.currentTool}
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Streaming Preview */}
        {streaming.isStreaming && streaming.streamedText && (
          <Card className="border-blue-500/30 bg-blue-50/50 dark:bg-blue-950/20">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Đang tạo câu trả lời...
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm whitespace-pre-wrap">{streaming.streamedText}</p>
              {streaming.retrievedChunks > 0 && (
                <Badge variant="secondary" className="mt-2">
                  {streaming.retrievedChunks} chunks retrieved
                </Badge>
              )}
            </CardContent>
          </Card>
        )}

        {/* Comparison Results */}
        {results && (
          <>
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Vector Only */}
              <Card className="border-primary/30">
                <CardHeader className="bg-primary/5">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-primary flex items-center gap-2">
                      <Database className="h-5 w-5" />
                      Vector Only
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="prose prose-sm max-w-none">
                    <p className="text-foreground leading-relaxed">
                      {results.vector.answer}
                    </p>
                  </div>

                  <Separator />

                  {/* Sources */}
                  <Collapsible open={vectorSourcesOpen} onOpenChange={setVectorSourcesOpen}>
                    <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                      <span className="text-sm font-medium">
                        Nguồn tham khảo ({results.vector.sources.length})
                      </span>
                      {vectorSourcesOpen ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-2 mt-2">
                      {results.vector.sources.map((source, idx) => (
                        <div key={idx} className="p-3 bg-muted rounded-md text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-xs">
                              {source.documentName || 'Tài liệu'}
                            </span>
                            <Badge variant="secondary" className="text-xs">
                              {(source.score * 100).toFixed(0)}%
                            </Badge>
                          </div>
                          <p className="text-muted-foreground">{source.text}</p>
                        </div>
                      ))}
                    </CollapsibleContent>
                  </Collapsible>

                  {/* Metrics */}
                  <div className="flex gap-4 p-3 bg-muted/50 rounded-lg text-sm">
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span>{(results.vector.metrics.latencyMs / 1000).toFixed(2)}s</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span>{results.vector.metrics.chunksUsed} chunks</span>
                    </div>
                    {results.vector.metrics.confidenceScore && (
                      <div className="flex items-center gap-1">
                        <Target className="h-4 w-4 text-muted-foreground" />
                        <span>{(results.vector.metrics.confidenceScore * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Vector + Graph */}
              <Card className="border-secondary/30">
                <CardHeader className="bg-secondary/5">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-secondary flex items-center gap-2">
                      <Target className="h-5 w-5" />
                      Vector + Graph
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="pt-6 space-y-4">
                  <div className="prose prose-sm max-w-none">
                    <p className="text-foreground leading-relaxed">
                      {results.graph.answer}
                    </p>
                  </div>

                  <Separator />

                  {/* Cypher Query */}
                  {results.graph.cypherQuery && (
                    <Collapsible open={cypherOpen} onOpenChange={setCypherOpen}>
                      <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                        <span className="text-sm font-medium">Cypher Query đã dùng</span>
                        {cypherOpen ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2">
                        <div className="p-3 bg-muted rounded-md font-mono text-xs whitespace-pre-wrap">
                          {results.graph.cypherQuery}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  )}

                  {/* Graph Context */}
                  <Collapsible open={graphContextOpen} onOpenChange={setGraphContextOpen}>
                    <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                      <span className="text-sm font-medium">Graph Context</span>
                      {graphContextOpen ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2">
                      <div className="p-3 bg-muted rounded-md text-sm">
                        <p className="text-muted-foreground">
                          {results.graph.graphContext.length} graph contexts retrieved
                        </p>
                      </div>
                    </CollapsibleContent>
                  </Collapsible>

                  {/* Sources */}
                  <Collapsible open={graphSourcesOpen} onOpenChange={setGraphSourcesOpen}>
                    <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                      <span className="text-sm font-medium">
                        Nguồn tham khảo ({results.graph.sources.length})
                      </span>
                      {graphSourcesOpen ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </CollapsibleTrigger>
                    <CollapsibleContent className="space-y-2 mt-2">
                      {results.graph.sources.map((source, idx) => (
                        <div key={idx} className="p-3 bg-muted rounded-md text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-xs">
                              {source.documentName || 'Tài liệu'}
                            </span>
                            <Badge variant="secondary" className="text-xs">
                              {(source.score * 100).toFixed(0)}%
                            </Badge>
                          </div>
                          <p className="text-muted-foreground">{source.text}</p>
                        </div>
                      ))}
                    </CollapsibleContent>
                  </Collapsible>

                  {/* Metrics */}
                  <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-lg text-sm">
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span>{(results.graph.metrics.latencyMs / 1000).toFixed(2)}s</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span>{results.graph.metrics.chunksUsed} chunks</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Target className="h-4 w-4 text-muted-foreground" />
                      <span>{results.graph.metrics.graphNodesUsed} nodes</span>
                    </div>
                    <Badge variant="secondary">
                      {results.graph.metrics.graphHops} hops
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Annotation Bar */}
            <Card className="sticky bottom-4 shadow-lg">
              <CardContent className="p-4">
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-3">Đánh giá câu trả lời:</p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant={selectedPreference === 'vector' ? 'default' : 'outline'}
                        onClick={() => setSelectedPreference('vector')}
                      >
                        👈 Vector tốt hơn
                      </Button>
                      <Button
                        variant={selectedPreference === 'equivalent' ? 'default' : 'outline'}
                        onClick={() => setSelectedPreference('equivalent')}
                      >
                        🤝 Tương đương
                      </Button>
                      <Button
                        variant={selectedPreference === 'graph' ? 'default' : 'outline'}
                        onClick={() => setSelectedPreference('graph')}
                      >
                        Graph tốt hơn 👉
                      </Button>
                      <Button
                        variant={selectedPreference === 'both_wrong' ? 'destructive' : 'outline'}
                        onClick={() => setSelectedPreference('both_wrong')}
                      >
                        ❌ Cả hai sai
                      </Button>
                    </div>
                  </div>

                  {selectedPreference && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowComment(!showComment)}
                      >
                        {showComment ? 'Ẩn' : 'Thêm'} nhận xét
                      </Button>

                      {showComment && (
                        <Textarea
                          placeholder="Nhận xét của bạn (không bắt buộc)..."
                          value={comment}
                          onChange={(e) => setComment(e.target.value)}
                          rows={2}
                          className="resize-none"
                        />
                      )}

                      <Button
                        onClick={handleSubmitAnnotation}
                        className="w-full"
                      >
                        Gửi đánh giá
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </PageContainer>
  );
}
