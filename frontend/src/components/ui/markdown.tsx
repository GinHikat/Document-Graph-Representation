import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';

interface MarkdownProps {
  content: string | null | undefined;
  className?: string;
}

export function Markdown({ content, className }: MarkdownProps) {
  // Handle null/undefined/empty content
  if (!content) {
    return <p className="text-muted-foreground italic">No content</p>;
  }

  return (
    <div
      className={cn(
        'prose prose-sm dark:prose-invert max-w-none',
        'prose-headings:font-semibold prose-headings:tracking-tight',
        'prose-h1:text-xl prose-h1:mb-4 prose-h1:mt-6',
        'prose-h2:text-lg prose-h2:mb-3 prose-h2:mt-5',
        'prose-h3:text-base prose-h3:mb-2 prose-h3:mt-4',
        'prose-p:leading-relaxed prose-p:mb-3 prose-p:text-foreground',
        'prose-ul:my-2 prose-ul:pl-4 prose-ul:list-disc',
        'prose-ol:my-2 prose-ol:pl-4 prose-ol:list-decimal',
        'prose-li:my-0.5 prose-li:text-foreground',
        'prose-strong:text-foreground prose-strong:font-semibold',
        'prose-code:bg-muted prose-code:text-foreground prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm',
        'prose-pre:bg-muted prose-pre:border prose-pre:rounded-lg prose-pre:p-4',
        'prose-blockquote:border-l-primary prose-blockquote:bg-muted/50 prose-blockquote:py-0.5 prose-blockquote:px-4',
        'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
        className
      )}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
