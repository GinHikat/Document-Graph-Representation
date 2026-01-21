import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, ChevronDown, ChevronRight, Clock, Database, Target, Loader2, History, Keyboard, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageContainer } from '@/components/layout/PageContainer';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useQAStore } from '@/stores/qaStore';
import { useToast } from '@/hooks/use-toast';
import { Separator } from '@/components/ui/separator';
import { Markdown } from '@/components/ui/markdown';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';

const EXAMPLE_QUESTIONS = [
  // Graph context: 10, aggregates multiple tax rate conditions
  "Thuế suất ưu đãi 10% áp dụng cho trường hợp nào?",
  // Graph context: 10, cross-references exemption clauses
  "Những thu nhập nào được miễn thuế TNDN?",
  // Graph context: 9, traverses deductible/non-deductible relationships
  "Các khoản chi nào được trừ và không được trừ khi tính thuế TNDN?",
];

const PREFERENCE_OPTIONS = [
  { key: 'vector', shortcut: '1', label: 'qa.vectorBetter' },
  { key: 'equivalent', shortcut: '2', label: 'qa.equivalent' },
  { key: 'graph', shortcut: '3', label: 'qa.graphBetter' },
  { key: 'both_wrong', shortcut: '4', label: 'qa.bothWrong' },
] as const;

export default function QA() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const {
    currentQuestion,
    results,
    history,
    isLoading,
    error,
    setCurrentQuestion,
    compare,
    submitAnnotation,
  } = useQAStore();

  const [selectedPreference, setSelectedPreference] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);
  const [vectorSourcesOpen, setVectorSourcesOpen] = useState(false);
  const [graphSourcesOpen, setGraphSourcesOpen] = useState(false);
  const [cypherOpen, setCypherOpen] = useState(false);
  const [graphContextOpen, setGraphContextOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-expand sources when results arrive
  useEffect(() => {
    if (results) {
      setVectorSourcesOpen(true);
      setGraphSourcesOpen(true);
      // Reset annotation state for new results
      setSelectedPreference(null);
      setComment('');
      setShowComment(false);
    }
  }, [results]);

  const handleCompare = async () => {
    if (!currentQuestion.trim()) {
      toast({
        title: t('qa.missingInfo'),
        description: t('qa.enterQuestion'),
        variant: 'destructive',
      });
      return;
    }

    await compare(currentQuestion);
  };

  const handleSubmitAnnotation = useCallback(async () => {
    if (!selectedPreference || !results || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await submitAnnotation(results.questionId, selectedPreference, comment);
      toast({
        title: t('common.success'),
        description: t('qa.annotationSaved'),
      });
      setSelectedPreference(null);
      setComment('');
      setShowComment(false);
    } catch (error) {
      toast({
        title: t('common.error'),
        description: t('qa.annotationError'),
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedPreference, results, isSubmitting, comment, submitAnnotation, toast, t]);

  const selectPreferenceWithFeedback = useCallback((preference: string) => {
    setSelectedPreference(preference);
    const option = PREFERENCE_OPTIONS.find(o => o.key === preference);
    if (option) {
      toast({
        title: `Selected: ${t(option.label)}`,
        description: 'Press ⌘+Enter to submit',
      });
    }
  }, [toast, t]);

  // Keyboard shortcuts - only active when results are visible
  const shortcuts = useMemo(() => {
    if (!results) return [];

    return [
      ...PREFERENCE_OPTIONS.map(option => ({
        key: option.shortcut,
        action: () => selectPreferenceWithFeedback(option.key),
        description: t(option.label),
      })),
      {
        key: 'Enter',
        modifiers: { meta: true } as const,
        action: handleSubmitAnnotation,
        description: 'Submit annotation',
      },
      {
        key: 'Enter',
        modifiers: { ctrl: true } as const,
        action: handleSubmitAnnotation,
        description: 'Submit annotation',
      },
    ];
  }, [results, t, selectPreferenceWithFeedback, handleSubmitAnnotation]);

  useKeyboardShortcuts(shortcuts, { enabled: !!results });

  // Replay a question from history
  const handleHistoryClick = (question: string) => {
    setCurrentQuestion(question);
    setHistoryOpen(false);
  };

  return (
    <TooltipProvider>
      <PageContainer maxWidth="full">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">{t('qa.title')}</h1>
              <p className="text-muted-foreground mt-1">
                {t('qa.subtitle')}
              </p>
            </div>

            {/* History Sidebar Trigger */}
            <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm">
                  <History className="h-4 w-4 mr-2" />
                  {t('qa.history')} ({history.length})
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-2">
                    <History className="h-5 w-5" />
                    {t('qa.questionHistory')}
                  </SheetTitle>
                </SheetHeader>
                <ScrollArea className="h-[calc(100vh-8rem)] mt-4">
                  <div className="space-y-2 pr-4">
                    {history.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-8">
                        {t('qa.noHistory')}
                      </p>
                    ) : (
                      history.map((item, idx) => (
                        <Card
                          key={item.questionId || idx}
                          className="cursor-pointer hover:bg-muted/50 transition-colors"
                          onClick={() => handleHistoryClick(item.question)}
                        >
                          <CardContent className="p-3">
                            <p className="text-sm line-clamp-2">{item.question}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <span className="text-xs text-muted-foreground">
                                {new Date(item.timestamp).toLocaleTimeString()}
                              </span>
                              {item.annotation && (
                                <Badge variant="secondary" className="text-xs">
                                  <CheckCircle2 className="h-3 w-3 mr-1" />
                                  {item.annotation.preference}
                                </Badge>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </SheetContent>
            </Sheet>
          </div>

          {/* Question Input */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div>
                  <Textarea
                    placeholder={t('qa.questionPlaceholder')}
                    value={currentQuestion}
                    onChange={(e) => setCurrentQuestion(e.target.value)}
                    rows={3}
                    className="resize-none text-lg"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <span className="text-sm text-muted-foreground">{t('qa.examples')}:</span>
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
                      {t('qa.processing')}
                    </>
                  ) : (
                    <>
                      <Search className="h-5 w-5 mr-2" />
                      {t('qa.compare')}
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{t('common.error')}</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
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
                    <Markdown content={results.vector?.answer} />

                    <Separator />

                    {/* Sources - Auto-expanded */}
                    <Collapsible open={vectorSourcesOpen} onOpenChange={setVectorSourcesOpen}>
                      <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                        <span className="text-sm font-medium">
                          {t('qa.sources')} ({results.vector?.sources?.length ?? 0})
                        </span>
                        {vectorSourcesOpen ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </CollapsibleTrigger>
                      <CollapsibleContent className="space-y-2 mt-2">
                        {results.vector?.sources?.map((source, idx) => (
                          <div key={idx} className="p-3 bg-muted rounded-md text-sm">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium text-xs">
                                {source.documentName || t('qa.document')}
                              </span>
                              <Badge variant="secondary" className="text-xs">
                                {source.score != null ? `${(source.score * 100).toFixed(0)}%` : '-'}
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
                        <span>{((results.vector?.metrics?.latencyMs ?? 0) / 1000).toFixed(2)}s</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Database className="h-4 w-4 text-muted-foreground" />
                        <span>{results.vector?.metrics?.chunksUsed ?? 0} chunks</span>
                      </div>
                      {results.vector?.metrics?.confidenceScore && (
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
                    <Markdown content={results.graph?.answer} />

                    <Separator />

                    {/* Cypher Query */}
                    {results.graph?.cypherQuery && (
                      <Collapsible open={cypherOpen} onOpenChange={setCypherOpen}>
                        <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                          <span className="text-sm font-medium">{t('qa.cypherQuery')}</span>
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
                            {results.graph?.graphContext?.length ?? 0} graph contexts retrieved
                          </p>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>

                    {/* Sources - Auto-expanded */}
                    <Collapsible open={graphSourcesOpen} onOpenChange={setGraphSourcesOpen}>
                      <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-muted/50 rounded-md">
                        <span className="text-sm font-medium">
                          {t('qa.sources')} ({results.graph?.sources?.length ?? 0})
                        </span>
                        {graphSourcesOpen ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </CollapsibleTrigger>
                      <CollapsibleContent className="space-y-2 mt-2">
                        {results.graph?.sources?.map((source, idx) => (
                          <div key={idx} className="p-3 bg-muted rounded-md text-sm">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium text-xs">
                                {source.documentName || t('qa.document')}
                              </span>
                              <Badge variant="secondary" className="text-xs">
                                {source.score != null ? `${(source.score * 100).toFixed(0)}%` : '-'}
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
                        <span>{((results.graph?.metrics?.latencyMs ?? 0) / 1000).toFixed(2)}s</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Database className="h-4 w-4 text-muted-foreground" />
                        <span>{results.graph?.metrics?.chunksUsed ?? 0} chunks</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Target className="h-4 w-4 text-muted-foreground" />
                        <span>{results.graph?.metrics?.graphNodesUsed ?? 0} nodes</span>
                      </div>
                      <Badge variant="secondary">
                        {results.graph?.metrics?.graphHops ?? 0} hops
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Enhanced Annotation Bar with Keyboard Shortcuts */}
              <Card className="sticky bottom-4 shadow-lg border-2">
                <CardContent className="p-4">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{t('qa.rateAnswer')}:</p>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Keyboard className="h-3 w-3" />
                        <span>Use 1-4 keys</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {PREFERENCE_OPTIONS.map((option) => (
                        <Tooltip key={option.key}>
                          <TooltipTrigger asChild>
                            <Button
                              variant={selectedPreference === option.key
                                ? (option.key === 'both_wrong' ? 'destructive' : 'default')
                                : 'outline'}
                              onClick={() => selectPreferenceWithFeedback(option.key)}
                              className="relative"
                            >
                              <span className="absolute -top-2 -right-2 bg-muted text-muted-foreground text-xs w-5 h-5 rounded-full flex items-center justify-center border">
                                {option.shortcut}
                              </span>
                              {t(option.label)}
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Press {option.shortcut} to select</p>
                          </TooltipContent>
                        </Tooltip>
                      ))}
                    </div>

                    {selectedPreference && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowComment(!showComment)}
                        >
                          {showComment ? t('qa.hideComment') : t('qa.addComment')}
                        </Button>

                        {showComment && (
                          <Textarea
                            placeholder={t('qa.commentPlaceholder')}
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            rows={2}
                            className="resize-none"
                          />
                        )}

                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              onClick={handleSubmitAnnotation}
                              className="w-full"
                              disabled={isSubmitting}
                            >
                              {isSubmitting ? (
                                <>
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                  {t('common.loading')}
                                </>
                              ) : (
                                <>
                                  {t('qa.submitRating')}
                                  <span className="ml-2 text-xs opacity-70">⌘+Enter</span>
                                </>
                              )}
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Press ⌘+Enter (or Ctrl+Enter) to submit</p>
                          </TooltipContent>
                        </Tooltip>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </PageContainer>
    </TooltipProvider>
  );
}
