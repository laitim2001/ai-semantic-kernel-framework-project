/**
 * RiskBadge - Risk Level Badge Component
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-3: HITL Approval Components
 *
 * Displays risk level with color-coded styling.
 * Supports low, medium, high, and critical risk levels.
 */

import { FC } from 'react';
import type { RiskLevel } from '@/types/ag-ui';

export interface RiskBadgeProps {
  /** Risk level */
  level: RiskLevel;
  /** Show risk score */
  showScore?: boolean;
  /** Risk score (0-1) */
  score?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

/** Risk level configuration */
const riskConfig: Record<RiskLevel, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  low: {
    label: 'Low Risk',
    color: 'text-green-700',
    bgColor: 'bg-green-100 border-green-200',
    icon: '✓',
  },
  medium: {
    label: 'Medium Risk',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100 border-yellow-200',
    icon: '⚠',
  },
  high: {
    label: 'High Risk',
    color: 'text-orange-700',
    bgColor: 'bg-orange-100 border-orange-200',
    icon: '⚠',
  },
  critical: {
    label: 'Critical Risk',
    color: 'text-red-700',
    bgColor: 'bg-red-100 border-red-200',
    icon: '⛔',
  },
};

/**
 * RiskBadge Component
 *
 * Visual indicator for risk level with appropriate styling.
 */
export const RiskBadge: FC<RiskBadgeProps> = ({
  level,
  showScore = false,
  score,
  size = 'md',
  className = '',
}) => {
  const config = riskConfig[level] || riskConfig.low;

  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full border
        ${config.bgColor} ${config.color} ${sizeClasses[size]}
        font-medium ${className}
      `}
      data-testid={`risk-badge-${level}`}
      role="status"
      aria-label={`${config.label}${showScore && score !== undefined ? ` (${Math.round(score * 100)}%)` : ''}`}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
      {showScore && score !== undefined && (
        <span className="opacity-75">({Math.round(score * 100)}%)</span>
      )}
    </span>
  );
};

export default RiskBadge;
