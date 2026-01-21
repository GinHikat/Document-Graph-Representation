import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, Scale, Users, Tag, HelpCircle, Hash, Calendar, Link as LinkIcon, Copy, Check, ChevronDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { GraphNode } from '@/types';

interface NodeDetailsPanelProps {
  node: GraphNode;
}

// Icon mapping for node types
const NODE_TYPE_ICONS: Record<string, React.ElementType> = {
  document: FileText,
  article: Scale,
  tax_type: Tag,
  taxpayer: Users,
  exemption: HelpCircle,
};

// Color mapping for node types
const NODE_TYPE_COLORS: Record<string, string> = {
  document: 'bg-[#4ecdc4] text-white',
  article: 'bg-[#45b7d1] text-white',
  tax_type: 'bg-[#96ceb4] text-black',
  taxpayer: 'bg-[#ffeaa7] text-black',
  exemption: 'bg-[#dfe6e9] text-black',
};

// Property display config - which properties to show prominently
const PROMINENT_PROPERTIES = ['name', 'title', 'text', 'content', 'description', 'số', 'điều', 'khoản'];

// Format property value for display
function formatPropertyValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Có' : 'Không';
  if (typeof value === 'number') return value.toLocaleString('vi-VN');
  if (value instanceof Date) return value.toLocaleDateString('vi-VN');
  if (typeof value === 'string') {
    // Check if it's a date string
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
      try {
        return new Date(value).toLocaleDateString('vi-VN');
      } catch {
        return value;
      }
    }
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(v => formatPropertyValue(v)).join(', ');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

// Get appropriate icon for property key
function getPropertyIcon(key: string): React.ElementType {
  const lowerKey = key.toLowerCase();
  if (lowerKey.includes('id')) return Hash;
  if (lowerKey.includes('date') || lowerKey.includes('time') || lowerKey.includes('ngày')) return Calendar;
  if (lowerKey.includes('link') || lowerKey.includes('url') || lowerKey.includes('ref')) return LinkIcon;
  return Tag;
}

// Humanize property key
function humanizeKey(key: string): string {
  // Common Vietnamese property names
  const keyMappings: Record<string, string> = {
    'name': 'Tên',
    'title': 'Tiêu đề',
    'text': 'Nội dung',
    'content': 'Nội dung',
    'description': 'Mô tả',
    'type': 'Loại',
    'id': 'ID',
    'created_at': 'Ngày tạo',
    'updated_at': 'Ngày cập nhật',
    'document_id': 'ID Tài liệu',
    'article_number': 'Số điều',
    'clause_number': 'Số khoản',
    'effective_date': 'Ngày hiệu lực',
    'so': 'Số',
    'dieu': 'Điều',
    'khoan': 'Khoản',
    'muc': 'Mục',
    'chuong': 'Chương',
  };

  const lowerKey = key.toLowerCase();
  if (keyMappings[lowerKey]) return keyMappings[lowerKey];

  // Convert snake_case or camelCase to readable format
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, str => str.toUpperCase());
}

// Check if value is a long text that needs special display
function isLongText(value: unknown): boolean {
  return typeof value === 'string' && value.length > 100;
}

export function NodeDetailsPanel({ node }: NodeDetailsPanelProps) {
  const { t } = useTranslation();
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());

  const TypeIcon = NODE_TYPE_ICONS[node.type] || HelpCircle;
  const typeColor = NODE_TYPE_COLORS[node.type] || 'bg-gray-500 text-white';

  // Copy to clipboard helper
  const copyToClipboard = async (text: string, fieldName: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  // Toggle expand for a field
  const toggleExpand = (fieldName: string) => {
    setExpandedFields(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fieldName)) {
        newSet.delete(fieldName);
      } else {
        newSet.add(fieldName);
      }
      return newSet;
    });
  };

  // Check if text needs "show more" (more than 80 chars)
  const needsExpand = (text: string) => text.length > 80;
  const isExpanded = (fieldName: string) => expandedFields.has(fieldName);

  // Separate prominent and other properties
  const entries = Object.entries(node.properties || {});
  const prominentEntries = entries.filter(([key]) =>
    PROMINENT_PROPERTIES.some(p => key.toLowerCase().includes(p))
  );
  const otherEntries = entries.filter(([key]) =>
    !PROMINENT_PROPERTIES.some(p => key.toLowerCase().includes(p))
  );

  // Find main text content (for readable display)
  const mainTextEntry = prominentEntries.find(([key]) =>
    ['text', 'content', 'description', 'nội dung'].some(p => key.toLowerCase().includes(p))
  );

  return (
    <Card className="transition-all duration-300 border-2 border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <TypeIcon className="h-5 w-5" />
            {t('graph.nodeDetails')}
          </CardTitle>
          <Badge className={typeColor}>
            {node.type}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Node Label - Main identifier - always show full text */}
        <div className="p-3 bg-primary/5 rounded-lg border border-primary/10">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-muted-foreground">{t('graph.label')}</p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => copyToClipboard(node.label, 'label')}
                  >
                    {copiedField === 'label' ? (
                      <Check className="h-3 w-3 text-green-500" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{copiedField === 'label' ? 'Đã copy!' : 'Copy label'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          {/* Label with expand/collapse and blur effect */}
          {needsExpand(node.label) && !isExpanded('label') ? (
            <div className="relative">
              <p className="font-medium text-base leading-relaxed break-words line-clamp-2">
                {node.label}
              </p>
              {/* Blur gradient overlay */}
              <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-primary/5 to-transparent" />
              <button
                onClick={() => toggleExpand('label')}
                className="mt-1 text-xs text-primary hover:text-primary/80 flex items-center gap-1"
              >
                <ChevronDown className="h-3 w-3" />
                Xem thêm ({node.label.length} ký tự)
              </button>
            </div>
          ) : (
            <div>
              <p className="font-medium text-base leading-relaxed break-words">{node.label}</p>
              {needsExpand(node.label) && (
                <button
                  onClick={() => toggleExpand('label')}
                  className="mt-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  Thu gọn
                </button>
              )}
            </div>
          )}
        </div>

        {/* Main Text Content - If exists, show prominently */}
        {mainTextEntry && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {humanizeKey(mainTextEntry[0])}
            </p>
            <ScrollArea className="h-[150px] rounded-md border p-3 bg-muted/30">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {formatPropertyValue(mainTextEntry[1])}
              </p>
            </ScrollArea>
          </div>
        )}

        <Separator />

        {/* Other Properties - Formatted as key-value pairs */}
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted-foreground">
            {t('graph.properties')}
          </p>

          <ScrollArea className="h-[180px]">
            <div className="space-y-2 pr-3">
              {/* Show prominent properties first (except main text) */}
              {prominentEntries
                .filter(entry => entry !== mainTextEntry)
                .map(([key, value]) => {
                  const PropIcon = getPropertyIcon(key);
                  const formattedValue = formatPropertyValue(value);
                  const isLong = isLongText(value);

                  return (
                    <div
                      key={key}
                      className={`rounded-md border bg-card p-2 ${isLong ? 'col-span-full' : ''}`}
                    >
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                        <PropIcon className="h-3 w-3" />
                        <span>{humanizeKey(key)}</span>
                      </div>
                      {isLong ? (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap line-clamp-3">
                          {formattedValue}
                        </p>
                      ) : (
                        <p className="text-sm font-medium truncate" title={formattedValue}>
                          {formattedValue}
                        </p>
                      )}
                    </div>
                  );
                })}

              {/* Then show other properties */}
              {otherEntries.map(([key, value]) => {
                const PropIcon = getPropertyIcon(key);
                const formattedValue = formatPropertyValue(value);
                const isLong = isLongText(value);

                return (
                  <div
                    key={key}
                    className={`rounded-md border bg-muted/30 p-2 ${isLong ? 'col-span-full' : ''}`}
                  >
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                      <PropIcon className="h-3 w-3" />
                      <span>{humanizeKey(key)}</span>
                    </div>
                    {isLong ? (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap line-clamp-3">
                        {formattedValue}
                      </p>
                    ) : (
                      <p className="text-sm truncate" title={formattedValue}>
                        {formattedValue}
                      </p>
                    )}
                  </div>
                );
              })}

              {entries.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  {t('graph.noProperties')}
                </p>
              )}
            </div>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}

export default NodeDetailsPanel;
