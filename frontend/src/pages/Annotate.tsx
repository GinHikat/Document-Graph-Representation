import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Star, SkipForward } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageContainer } from '@/components/layout/PageContainer';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { useAuthStore } from '@/stores/authStore';
import { useToast } from '@/hooks/use-toast';
import { annotationService } from '@/services/api';
import type { AnnotationTask, AnnotationRating, AnnotatorStats } from '@/types';
import { Badge } from '@/components/ui/badge';

export default function Annotate() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { isAuthenticated, user } = useAuthStore();
  const [stats, setStats] = useState<AnnotatorStats | null>(null);
  const [tasks, setTasks] = useState<AnnotationTask[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [rating, setRating] = useState<Partial<AnnotationRating>>({});

  const loadData = useCallback(async () => {
    try {
      const [statsData, tasksData] = await Promise.all([
        annotationService.getStats(),
        annotationService.getPending(),
      ]);
      setStats(statsData);
      setTasks(tasksData);
    } catch (error) {
      toast({
        title: 'Lỗi',
        description: 'Không thể tải dữ liệu',
        variant: 'destructive',
      });
    }
  }, [toast]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    loadData();
  }, [isAuthenticated, navigate, loadData]);

  const handleSubmit = async () => {
    const currentTask = tasks[currentIndex];
    if (!rating.overallComparison) {
      toast({
        title: 'Thiếu thông tin',
        description: 'Vui lòng chọn đánh giá tổng quan',
        variant: 'destructive',
      });
      return;
    }

    try {
      await annotationService.submit({
        questionId: currentTask.questionId,
        vectorCorrectness: rating.vectorCorrectness || 0,
        vectorCompleteness: rating.vectorCompleteness || 0,
        vectorRelevance: rating.vectorRelevance || 0,
        graphCorrectness: rating.graphCorrectness || 0,
        graphCompleteness: rating.graphCompleteness || 0,
        graphRelevance: rating.graphRelevance || 0,
        overallComparison: rating.overallComparison,
        comment: rating.comment,
      });

      toast({
        title: 'Thành công',
        description: 'Đã lưu đánh giá',
      });

      // Move to next
      if (currentIndex < tasks.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setRating({});
      } else {
        toast({
          title: 'Hoàn thành',
          description: 'Bạn đã hoàn thành tất cả câu hỏi',
        });
      }
    } catch (error) {
      toast({
        title: 'Lỗi',
        description: 'Không thể lưu đánh giá',
        variant: 'destructive',
      });
    }
  };

  const handleSkip = () => {
    if (currentIndex < tasks.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setRating({});
    }
  };

  const currentTask = tasks[currentIndex];
  const progress = tasks.length > 0 ? ((currentIndex + 1) / tasks.length) * 100 : 0;

  if (!isAuthenticated) {
    return null;
  }

  return (
    <PageContainer maxWidth="xl">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Annotator Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Xin chào, {user?.name}
            </p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats.totalAssigned}</div>
                <p className="text-sm text-muted-foreground">Tổng được giao</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-success">{stats.completedToday}</div>
                <p className="text-sm text-muted-foreground">Hoàn thành hôm nay</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-warning">{stats.pendingReview}</div>
                <p className="text-sm text-muted-foreground">Chờ đánh giá</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{(stats.agreementRate * 100).toFixed(1)}%</div>
                <p className="text-sm text-muted-foreground">Tỷ lệ đồng thuận</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Progress */}
        {tasks.length > 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">
                  Câu hỏi {currentIndex + 1} / {tasks.length}
                </span>
                <span className="text-sm text-muted-foreground">
                  {progress.toFixed(0)}%
                </span>
              </div>
              <Progress value={progress} />
            </CardContent>
          </Card>
        )}

        {/* Review Interface */}
        {currentTask ? (
          <>
            {/* Question */}
            <Card>
              <CardHeader>
                <CardTitle>Câu hỏi</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg">{currentTask.question}</p>
              </CardContent>
            </Card>

            {/* Answers Comparison */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-primary">Vector Answer</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed mb-4">
                    {currentTask.vectorAnswer.answer}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    Latency: {(currentTask.vectorAnswer.metrics.latencyMs / 1000).toFixed(2)}s
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-secondary">Graph Answer</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed mb-4">
                    {currentTask.graphAnswer.answer}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    Latency: {(currentTask.graphAnswer.metrics.latencyMs / 1000).toFixed(2)}s
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Rating Form */}
            <Card>
              <CardHeader>
                <CardTitle>Đánh giá</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Overall Comparison */}
                <div>
                  <Label className="text-base mb-3 block">So sánh tổng quan</Label>
                  <RadioGroup
                    value={rating.overallComparison}
                    onValueChange={(value) =>
                      setRating({ ...rating, overallComparison: value as AnnotationRating['overallComparison'] })
                    }
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="vector_much_better" id="vmb" />
                      <Label htmlFor="vmb">Vector tốt hơn nhiều</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="vector_better" id="vb" />
                      <Label htmlFor="vb">Vector tốt hơn một chút</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="equivalent" id="eq" />
                      <Label htmlFor="eq">Tương đương nhau</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="graph_better" id="gb" />
                      <Label htmlFor="gb">Graph tốt hơn một chút</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="graph_much_better" id="gmb" />
                      <Label htmlFor="gmb">Graph tốt hơn nhiều</Label>
                    </div>
                  </RadioGroup>
                </div>

                {/* Comments */}
                <div>
                  <Label htmlFor="comment" className="text-base mb-2 block">
                    Nhận xét
                  </Label>
                  <Textarea
                    id="comment"
                    placeholder="Nhận xét chi tiết về chất lượng câu trả lời..."
                    value={rating.comment || ''}
                    onChange={(e) => setRating({ ...rating, comment: e.target.value })}
                    rows={4}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Navigation */}
            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                disabled={currentIndex === 0}
              >
                <ChevronLeft className="h-4 w-4 mr-2" />
                Trước
              </Button>

              <div className="flex gap-2">
                <Button variant="outline" onClick={handleSkip}>
                  <SkipForward className="h-4 w-4 mr-2" />
                  Bỏ qua
                </Button>
                <Button onClick={handleSubmit}>
                  Gửi & Tiếp theo
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          </>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">Không có câu hỏi nào để đánh giá</p>
            </CardContent>
          </Card>
        )}
      </div>
    </PageContainer>
  );
}
