/**
 * DynamicCard - Dynamic Card Component
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-1: Tool-based Generative UI
 *
 * Renders dynamic cards based on card schema from backend.
 * Supports title, subtitle, content, image, and action buttons.
 */

import { FC } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/Card';
import type { CardAction } from '@/types/ag-ui';

export interface DynamicCardProps {
  /** Card title */
  title?: string;
  /** Card subtitle */
  subtitle?: string;
  /** Card content (plain text) */
  content?: string;
  /** Image URL */
  imageUrl?: string;
  /** Action buttons */
  actions?: CardAction[];
  /** Callback when action is clicked */
  onAction?: (action: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * DynamicCard - Renders cards with configurable content and actions
 */
export const DynamicCard: FC<DynamicCardProps> = ({
  title,
  subtitle,
  content,
  imageUrl,
  actions,
  onAction,
  className,
}) => {
  const hasHeader = title || subtitle;
  const hasFooter = actions && actions.length > 0;

  return (
    <Card className={cn('overflow-hidden', className)}>
      {imageUrl && (
        <div className="relative aspect-video">
          <img
            src={imageUrl}
            alt={title || 'Card image'}
            className="object-cover w-full h-full"
            loading="lazy"
          />
        </div>
      )}

      {hasHeader && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </CardHeader>
      )}

      {content && (
        <CardContent className={cn(!hasHeader && 'pt-6')}>
          {/* Render content as plain text with whitespace preservation */}
          <p className="text-sm text-foreground whitespace-pre-wrap">{content}</p>
        </CardContent>
      )}

      {hasFooter && (
        <CardFooter className="flex justify-end gap-2">
          {actions.map((action, index) => (
            <Button
              key={index}
              variant={action.variant || 'default'}
              onClick={() => onAction?.(action.action)}
            >
              {action.label}
            </Button>
          ))}
        </CardFooter>
      )}
    </Card>
  );
};

export default DynamicCard;
