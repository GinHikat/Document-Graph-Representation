import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FileText, GitGraph, MessagesSquare, UserCheck, Lock, TrendingUp, Database, Clock } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageContainer } from '@/components/layout/PageContainer';
import { useAuthStore } from '@/stores/authStore';
import { statsService } from '@/services/api';

export default function Home() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuthStore();

  // Fetch real stats from backend
  const { data: systemStats, isLoading: statsLoading } = useQuery({
    queryKey: ['system-stats'],
    queryFn: statsService.getStats,
    staleTime: 60000, // 1 minute
    retry: 1,
  });

  const features = [
    {
      title: t('home.features.documents.title'),
      description: t('home.features.documents.description'),
      icon: FileText,
      link: '/documents',
      color: 'text-primary',
      locked: false,
    },
    {
      title: t('home.features.graph.title'),
      description: t('home.features.graph.description'),
      icon: GitGraph,
      link: '/graph',
      color: 'text-secondary',
      locked: false,
    },
    {
      title: t('home.features.qa.title'),
      description: t('home.features.qa.description'),
      icon: MessagesSquare,
      link: '/qa',
      color: 'text-accent',
      locked: false,
    },
    {
      title: t('home.features.annotator.title'),
      description: t('home.features.annotator.description'),
      icon: UserCheck,
      link: isAuthenticated ? '/annotate' : '/login',
      color: 'text-muted-foreground',
      locked: !isAuthenticated,
    },
  ];

  // Build stats from real data
  const stats = [
    {
      label: t('home.stats.documents'),
      value: statsLoading ? '...' : (systemStats?.document_count?.toLocaleString() ?? '0'),
      icon: Database
    },
    {
      label: t('home.stats.questions'),
      value: statsLoading ? '...' : (systemStats?.question_count?.toLocaleString() ?? '0'),
      icon: MessagesSquare
    },
    {
      label: t('home.stats.relationships'),
      value: statsLoading ? '...' : (systemStats?.relationship_count?.toLocaleString() ?? '0'),
      icon: TrendingUp
    },
    {
      label: t('home.stats.responseTime'),
      value: statsLoading ? '...' : (systemStats?.avg_response_time_ms ? `${(systemStats.avg_response_time_ms / 1000).toFixed(1)}s` : 'N/A'),
      icon: Clock
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="border-b bg-gradient-to-b from-background to-muted/20">
        <PageContainer className="py-12 md:py-20">
          <div className="text-center space-y-4">
            <Badge variant="secondary" className="mb-2">
              {t('home.badge')}
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              {t('home.title')}
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              {t('home.subtitle')}
            </p>
            <div className="flex gap-3 justify-center pt-4">
              <Button asChild size="lg" className="gap-2">
                <Link to="/qa">
                  <MessagesSquare className="h-4 w-4" />
                  {t('home.startCompare')}
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/documents">{t('home.manageDocuments')}</Link>
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
            <h2 className="text-3xl font-bold mb-3">{t('home.featuresTitle')}</h2>
            <p className="text-muted-foreground">
              {t('home.featuresSubtitle')}
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
                      {feature.locked ? t('home.loginToAccess') : t('home.access')}
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
            <h2 className="text-2xl font-bold">{t('home.aboutTitle')}</h2>
            <p className="text-muted-foreground leading-relaxed">
              {t('home.aboutParagraph1')} <span className="font-semibold text-primary">{t('home.vectorSearch')}</span> {t('home.vectorSearchDesc')}
              {' '}{t('common.and')} <span className="font-semibold text-secondary">{t('home.graphSearch')}</span> {t('home.graphSearchDesc')}.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              {t('home.aboutParagraph2')}
            </p>
          </div>
        </PageContainer>
      </section>
    </div>
  );
}
