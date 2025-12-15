import { Link } from 'react-router-dom';
import { FileText, GitGraph, MessagesSquare, UserCheck, Lock, TrendingUp, Database, Clock } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageContainer } from '@/components/layout/PageContainer';
import { useAuthStore } from '@/stores/authStore';

export default function Home() {
  const { isAuthenticated } = useAuthStore();

  const features = [
    {
      title: 'Quản lý tài liệu',
      description: 'Upload và quản lý văn bản pháp luật thuế',
      icon: FileText,
      link: '/documents',
      color: 'text-primary',
      locked: false,
    },
    {
      title: 'Trực quan hóa đồ thị',
      description: 'Khám phá mối quan hệ giữa các điều khoản',
      icon: GitGraph,
      link: '/graph',
      color: 'text-secondary',
      locked: false,
    },
    {
      title: 'So sánh Q&A',
      description: 'Đánh giá Vector vs Graph search',
      icon: MessagesSquare,
      link: '/qa',
      color: 'text-accent',
      locked: false,
    },
    {
      title: 'Annotator Dashboard',
      description: 'Đánh giá và cải thiện chất lượng',
      icon: UserCheck,
      link: isAuthenticated ? '/annotate' : '/login',
      color: 'text-muted-foreground',
      locked: !isAuthenticated,
    },
  ];

  const stats = [
    { label: 'Tài liệu', value: '248', icon: Database },
    { label: 'Câu hỏi', value: '1,542', icon: MessagesSquare },
    { label: 'Độ chính xác', value: '94.2%', icon: TrendingUp },
    { label: 'Thời gian phản hồi', value: '1.8s', icon: Clock },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="border-b bg-gradient-to-b from-background to-muted/20">
        <PageContainer className="py-12 md:py-20">
          <div className="text-center space-y-4">
            <Badge variant="secondary" className="mb-2">
              RAG System
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              Tax Legal RAG System
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              So sánh hiệu quả truy vấn Vector và Graph cho văn bản pháp luật thuế Việt Nam
            </p>
            <div className="flex gap-3 justify-center pt-4">
              <Button asChild size="lg" className="gap-2">
                <Link to="/qa">
                  <MessagesSquare className="h-4 w-4" />
                  Bắt đầu so sánh
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/documents">Quản lý tài liệu</Link>
              </Button>
            </div>
          </div>
        </PageContainer>
      </section>

      {/* Stats Section */}
      <section className="border-b">
        <PageContainer className="py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats.map((stat) => (
              <Card key={stat.label}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.label}</p>
                      <p className="text-2xl font-bold mt-1">{stat.value}</p>
                    </div>
                    <stat.icon className="h-8 w-8 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </PageContainer>
      </section>

      {/* Features Section */}
      <section>
        <PageContainer className="py-12">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold mb-3">Tính năng chính</h2>
            <p className="text-muted-foreground">
              Khám phá các công cụ phân tích và so sánh văn bản pháp luật
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="relative group hover:shadow-lg transition-all duration-200 hover:-translate-y-1"
              >
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`p-2 rounded-lg bg-muted ${feature.color}`}>
                      <feature.icon className="h-6 w-6" />
                    </div>
                    {feature.locked && (
                      <Lock className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    asChild
                    variant={feature.locked ? 'outline' : 'default'}
                    className="w-full"
                  >
                    <Link to={feature.link}>
                      {feature.locked ? 'Đăng nhập để truy cập' : 'Truy cập'}
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </PageContainer>
      </section>

      {/* About Section */}
      <section className="border-t bg-muted/30">
        <PageContainer className="py-12">
          <div className="max-w-3xl mx-auto text-center space-y-4">
            <h2 className="text-2xl font-bold">Về hệ thống</h2>
            <p className="text-muted-foreground leading-relaxed">
              Tax Legal RAG System là nền tảng nghiên cứu và so sánh hiệu quả của hai phương pháp
              truy vấn thông tin: <span className="font-semibold text-primary">Vector Search</span> (tìm kiếm dựa trên độ tương đồng ngữ nghĩa) 
              và <span className="font-semibold text-secondary">Graph-enhanced Search</span> (tìm kiếm kết hợp cấu trúc đồ thị).
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Hệ thống được thiết kế để đánh giá chất lượng câu trả lời cho các câu hỏi về
              pháp luật thuế Việt Nam, giúp cải thiện độ chính xác và tính hữu ích của các
              hệ thống hỏi đáp dựa trên AI.
            </p>
          </div>
        </PageContainer>
      </section>
    </div>
  );
}
