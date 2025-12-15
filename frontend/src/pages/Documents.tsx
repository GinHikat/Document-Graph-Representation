import { useEffect, useState } from 'react';
import { Upload, Trash2, RefreshCw, FileText, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageContainer } from '@/components/layout/PageContainer';
import { useDocumentStore } from '@/stores/documentStore';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { Progress } from '@/components/ui/progress';
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

export default function Documents() {
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

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    try {
      await uploadDocuments(fileArray);
      toast({
        title: 'Upload thành công',
        description: `Đã tải lên ${fileArray.length} tài liệu`,
      });
    } catch (error) {
      toast({
        title: 'Lỗi upload',
        description: 'Không thể tải tài liệu lên',
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
        title: 'Xóa thành công',
        description: `Đã xóa ${selectedIds.length} tài liệu`,
      });
      setShowDeleteDialog(false);
    } catch (error) {
      toast({
        title: 'Lỗi xóa',
        description: 'Không thể xóa tài liệu',
        variant: 'destructive',
      });
    }
  };

  const handleReprocess = async () => {
    try {
      await reprocessDocuments(selectedIds);
      toast({
        title: 'Đang xử lý lại',
        description: `Bắt đầu xử lý lại ${selectedIds.length} tài liệu`,
      });
      clearSelection();
    } catch (error) {
      toast({
        title: 'Lỗi',
        description: 'Không thể xử lý lại tài liệu',
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
            Hoàn thành
          </Badge>
        );
      case 'processing':
        return (
          <Badge variant="secondary">
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            Đang xử lý
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive">
            <AlertCircle className="h-3 w-3 mr-1" />
            Thất bại
          </Badge>
        );
      default:
        return null;
    }
  };

  const allSelected = documents.length > 0 && selectedIds.length === documents.length;

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Quản lý tài liệu</h1>
            <p className="text-muted-foreground mt-1">
              Upload và quản lý văn bản pháp luật thuế
            </p>
          </div>
        </div>

        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle>Tải lên tài liệu</CardTitle>
            <CardDescription>
              Hỗ trợ định dạng PDF, DOCX. Có thể tải nhiều file cùng lúc.
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
                Kéo thả file vào đây hoặc click để chọn
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                PDF, DOCX (tối đa 50MB mỗi file)
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
                  Chọn file
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
              Đã chọn {selectedIds.length} tài liệu
            </span>
            <div className="ml-auto flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleReprocess}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Xử lý lại
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteDialog(true)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Xóa
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSelection}
              >
                Bỏ chọn
              </Button>
            </div>
          </div>
        )}

        {/* Documents Table */}
        <Card>
          <CardHeader>
            <CardTitle>Danh sách tài liệu</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
                <p className="text-muted-foreground">Chưa có tài liệu nào</p>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center p-3 border-b font-medium text-sm">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={() => allSelected ? clearSelection() : selectAll()}
                    className="mr-3"
                  />
                  <div className="flex-1">Tên tài liệu</div>
                  <div className="w-40">Ngày tải lên</div>
                  <div className="w-32">Trạng thái</div>
                  <div className="w-24">Thao tác</div>
                </div>

                {documents.map((doc) => (
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
                        onClick={() => setShowDeleteDialog(true)}
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
            <AlertDialogTitle>Xác nhận xóa</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc muốn xóa {selectedIds.length} tài liệu đã chọn?
              Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Xóa</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageContainer>
  );
}
