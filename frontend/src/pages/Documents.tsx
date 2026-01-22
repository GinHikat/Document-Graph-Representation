import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, Trash2, RefreshCw, FileText, AlertCircle, CheckCircle2, Loader2, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageContainer } from '@/components/layout/PageContainer';
import { useDocumentStore } from '@/stores/documentStore';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

type StatusFilter = 'all' | 'completed' | 'processing' | 'failed';

export default function Documents() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const {
    documents,
    selectedIds,
    uploadProgress,
    isLoading,
    loadDocuments,
    uploadDocuments,
    deleteDocuments,
    reprocessDocuments,
    toggleSelection,
    clearSelection,
    selectAll,
  } = useDocumentStore();

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Filtered documents based on search and status
  const filteredDocuments = useMemo(() => {
    return documents.filter(doc => {
      const matchesSearch = searchQuery === '' ||
        doc.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || doc.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [documents, searchQuery, statusFilter]);

  // Count by status for filter badges
  const statusCounts = useMemo(() => {
    return {
      all: documents.length,
      completed: documents.filter(d => d.status === 'completed').length,
      processing: documents.filter(d => d.status === 'processing').length,
      failed: documents.filter(d => d.status === 'failed').length,
    };
  }, [documents]);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    try {
      await uploadDocuments(fileArray);
      toast({
        title: t('documents.uploadSuccess'),
        description: t('documents.uploadSuccessDescription', { count: fileArray.length }),
      });
    } catch (error) {
      toast({
        title: t('documents.uploadError'),
        description: t('documents.uploadErrorDescription'),
        variant: 'destructive',
      });
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleDelete = async () => {
    try {
      await deleteDocuments(selectedIds);
      toast({
        title: t('documents.deleteSuccess'),
        description: t('documents.deleteSuccessDescription', { count: selectedIds.length }),
      });
      setShowDeleteDialog(false);
    } catch (error) {
      toast({
        title: t('documents.deleteError'),
        description: t('documents.deleteErrorDescription'),
        variant: 'destructive',
      });
    }
  };

  const handleReprocess = async () => {
    try {
      await reprocessDocuments(selectedIds);
      toast({
        title: t('documents.reprocessing'),
        description: t('documents.reprocessingDescription', { count: selectedIds.length }),
      });
      clearSelection();
    } catch (error) {
      toast({
        title: t('documents.reprocessError'),
        description: t('documents.reprocessErrorDescription'),
        variant: 'destructive',
      });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="default" className="bg-success">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            {t('documents.statusCompleted')}
          </Badge>
        );
      case 'processing':
        return (
          <Badge variant="secondary">
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            {t('documents.statusProcessing')}
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive">
            <AlertCircle className="h-3 w-3 mr-1" />
            {t('documents.statusFailed')}
          </Badge>
        );
      default:
        return null;
    }
  };

  const allSelected = filteredDocuments.length > 0 &&
    filteredDocuments.every(doc => selectedIds.includes(doc.id));

  const handleSelectAllFiltered = () => {
    if (allSelected) {
      clearSelection();
    } else {
      // Select only filtered documents
      const filteredIds = filteredDocuments.map(doc => doc.id);
      filteredIds.forEach(id => {
        if (!selectedIds.includes(id)) {
          toggleSelection(id);
        }
      });
    }
  };

  const clearFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
  };

  const hasActiveFilters = searchQuery !== '' || statusFilter !== 'all';

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{t('documents.title')}</h1>
            <p className="text-muted-foreground mt-1">
              {t('documents.subtitle')}
            </p>
          </div>
        </div>

        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle>{t('documents.uploadTitle')}</CardTitle>
            <CardDescription>
              {t('documents.uploadDescription')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging ? 'border-primary bg-primary/5' : 'border-border'
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg font-medium mb-2">
                {t('documents.dragDropText')}
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                {t('documents.formatHint')}
              </p>
              <input
                type="file"
                multiple
                accept=".pdf,.docx"
                onChange={(e) => handleFileSelect(e.target.files)}
                className="hidden"
                id="file-upload"
              />
              <Button asChild>
                <label htmlFor="file-upload" className="cursor-pointer">
                  {t('documents.selectFile')}
                </label>
              </Button>
            </div>

            {uploadProgress && (
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{uploadProgress.step}</span>
                  <span className="text-sm text-muted-foreground">
                    {uploadProgress.progress}%
                  </span>
                </div>
                <Progress value={uploadProgress.progress} className="h-2" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Bulk Actions */}
        {selectedIds.length > 0 && (
          <div className="flex items-center gap-2 p-4 bg-muted rounded-lg">
            <span className="text-sm font-medium">
              {t('documents.selected', { count: selectedIds.length })}
            </span>
            <div className="ml-auto flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleReprocess}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                {t('documents.reprocess')}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteDialog(true)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                {t('common.delete')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSelection}
              >
                {t('documents.deselect')}
              </Button>
            </div>
          </div>
        )}

        {/* Documents Table */}
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-4">
              <CardTitle>{t('documents.listTitle')}</CardTitle>

              {/* Search and Filter Bar */}
              <div className="flex flex-col sm:flex-row gap-3">
                {/* Search Input */}
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder={t('common.search') + '...'}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 pr-9"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      aria-label="Clear search"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>

                {/* Status Filter Chips */}
                <div className="flex gap-2 flex-wrap">
                  <Badge
                    variant={statusFilter === 'all' ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => setStatusFilter('all')}
                  >
                    {t('common.filter')}: All ({statusCounts.all})
                  </Badge>
                  <Badge
                    variant={statusFilter === 'completed' ? 'default' : 'outline'}
                    className="cursor-pointer bg-success/10 hover:bg-success/20"
                    onClick={() => setStatusFilter('completed')}
                  >
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    {statusCounts.completed}
                  </Badge>
                  <Badge
                    variant={statusFilter === 'processing' ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => setStatusFilter('processing')}
                  >
                    <Loader2 className="h-3 w-3 mr-1" />
                    {statusCounts.processing}
                  </Badge>
                  <Badge
                    variant={statusFilter === 'failed' ? 'destructive' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => setStatusFilter('failed')}
                  >
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {statusCounts.failed}
                  </Badge>
                </div>
              </div>

              {/* Active filters indicator */}
              {hasActiveFilters && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>
                    Showing {filteredDocuments.length} of {documents.length} documents
                  </span>
                  <Button variant="ghost" size="sm" onClick={clearFilters}>
                    <X className="h-3 w-3 mr-1" />
                    Clear filters
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
                <p className="text-muted-foreground">
                  {hasActiveFilters
                    ? 'No documents match your filters'
                    : t('documents.noDocuments')}
                </p>
                {hasActiveFilters && (
                  <Button variant="link" onClick={clearFilters} className="mt-2">
                    Clear filters
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center p-3 border-b font-medium text-sm">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={handleSelectAllFiltered}
                    className="mr-3"
                  />
                  <div className="flex-1">{t('documents.documentName')}</div>
                  <div className="w-40">{t('documents.uploadDate')}</div>
                  <div className="w-32">{t('documents.status')}</div>
                  <div className="w-24">{t('documents.actions')}</div>
                </div>

                {filteredDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center p-3 hover:bg-muted/50 rounded-lg transition-colors"
                  >
                    <Checkbox
                      checked={selectedIds.includes(doc.id)}
                      onCheckedChange={() => toggleSelection(doc.id)}
                      className="mr-3"
                    />
                    <div className="flex-1 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{doc.name}</span>
                    </div>
                    <div className="w-40 text-sm text-muted-foreground">
                      {new Date(doc.uploadedAt).toLocaleDateString('vi-VN')}
                    </div>
                    <div className="w-32">
                      {getStatusBadge(doc.status)}
                    </div>
                    <div className="w-24">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          toggleSelection(doc.id);
                          setShowDeleteDialog(true);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('documents.confirmDeleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('documents.confirmDeleteDescription', { count: selectedIds.length })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>{t('common.delete')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageContainer>
  );
}
