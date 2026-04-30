// =============================================================================
// IPA Platform - DevUI Stat Card Component
// =============================================================================
// Sprint 89: S89-1 - Statistics Dashboard
//
// Reusable statistic card for displaying key metrics.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
// =============================================================================

import { FC, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

export interface StatCardProps {
  /** Card title */
  title: string;
  /** Main value to display */
  value: string | number;
  /** Optional description or subtitle */
  description?: string;
  /** Icon component */
  icon?: LucideIcon;
  /** Trend indicator: positive, negative, or neutral */
  trend?: 'up' | 'down' | 'neutral';
  /** Trend value text */
  trendValue?: string;
  /** Color variant */
  variant?: 'default' | 'purple' | 'green' | 'blue' | 'yellow' | 'red';
  /** Additional content (e.g., progress bar) */
  children?: ReactNode;
  /** Click handler */
  onClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Stat Card Component
 * Displays a single statistic with optional icon, trend, and description
 */
export const StatCard: FC<StatCardProps> = ({
  title,
  value,
  description,
  icon: Icon,
  trend,
  trendValue,
  variant = 'default',
  children,
  onClick,
  className,
}) => {
  // Color configurations
  const variantStyles = {
    default: {
      bg: 'bg-white',
      iconBg: 'bg-gray-100',
      iconColor: 'text-gray-600',
      border: 'border-gray-200',
    },
    purple: {
      bg: 'bg-white',
      iconBg: 'bg-purple-100',
      iconColor: 'text-purple-600',
      border: 'border-purple-200',
    },
    green: {
      bg: 'bg-white',
      iconBg: 'bg-green-100',
      iconColor: 'text-green-600',
      border: 'border-green-200',
    },
    blue: {
      bg: 'bg-white',
      iconBg: 'bg-blue-100',
      iconColor: 'text-blue-600',
      border: 'border-blue-200',
    },
    yellow: {
      bg: 'bg-white',
      iconBg: 'bg-yellow-100',
      iconColor: 'text-yellow-600',
      border: 'border-yellow-200',
    },
    red: {
      bg: 'bg-white',
      iconBg: 'bg-red-100',
      iconColor: 'text-red-600',
      border: 'border-red-200',
    },
  };

  const styles = variantStyles[variant];

  // Trend color
  const trendStyles = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-500',
  };

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  };

  return (
    <div
      className={cn(
        'rounded-lg border p-4 transition-shadow',
        styles.bg,
        styles.border,
        onClick && 'cursor-pointer hover:shadow-md',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        {Icon && (
          <div
            className={cn(
              'flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0',
              styles.iconBg
            )}
          >
            <Icon className={cn('w-5 h-5', styles.iconColor)} />
          </div>
        )}

        <div className="flex-1 min-w-0">
          {/* Title */}
          <p className="text-sm font-medium text-gray-500 truncate">{title}</p>

          {/* Value */}
          <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>

          {/* Description or Trend */}
          {(description || trend) && (
            <div className="flex items-center gap-2 mt-1">
              {trend && trendValue && (
                <span className={cn('text-sm font-medium', trendStyles[trend])}>
                  {trendIcons[trend]} {trendValue}
                </span>
              )}
              {description && (
                <span className="text-sm text-gray-500">{description}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Additional content */}
      {children && <div className="mt-3">{children}</div>}
    </div>
  );
};

/**
 * Mini Stat Card for compact display
 */
export const MiniStatCard: FC<{
  label: string;
  value: string | number;
  icon?: LucideIcon;
  variant?: 'default' | 'success' | 'warning' | 'error';
  className?: string;
}> = ({ label, value, icon: Icon, variant = 'default', className }) => {
  const variantStyles = {
    default: 'bg-gray-50 text-gray-700',
    success: 'bg-green-50 text-green-700',
    warning: 'bg-yellow-50 text-yellow-700',
    error: 'bg-red-50 text-red-700',
  };

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg',
        variantStyles[variant],
        className
      )}
    >
      {Icon && <Icon className="w-4 h-4" />}
      <span className="text-sm font-medium">{label}:</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
};

export default StatCard;
