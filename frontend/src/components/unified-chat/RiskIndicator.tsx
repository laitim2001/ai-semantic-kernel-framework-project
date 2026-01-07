/**
 * RiskIndicator - Risk Level Display Component
 *
 * Sprint 64: Approval Flow & Risk Indicators
 * S64-3: Risk Indicator System
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays the current risk level with color coding, score,
 * and detailed tooltip showing risk factors and reasoning.
 */

import { FC } from 'react';
import { Shield, AlertTriangle, AlertOctagon, Skull } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/Badge';
import type { RiskLevel } from '@/types/ag-ui';

// =============================================================================
// Types
// =============================================================================

export interface RiskIndicatorProps {
  /** Risk level */
  level: RiskLevel;
  /** Risk score (0-100) */
  score: number;
  /** List of risk factors */
  factors?: string[];
  /** Assessment reasoning */
  reasoning?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show the score */
  showScore?: boolean;
  /** Whether to show tooltip on hover */
  showTooltip?: boolean;
  /** Optional click handler */
  onClick?: () => void;
  /** Additional className */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

/** Risk level configuration */
const riskConfig: Record<
  RiskLevel,
  {
    icon: typeof Shield;
    label: string;
    colorClass: string;
    bgClass: string;
    borderClass: string;
    badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline';
    pulseClass: string;
  }
> = {
  low: {
    icon: Shield,
    label: 'Low',
    colorClass: 'text-green-600',
    bgClass: 'bg-green-500',
    borderClass: 'border-green-300',
    badgeVariant: 'default',
    pulseClass: '',
  },
  medium: {
    icon: AlertTriangle,
    label: 'Medium',
    colorClass: 'text-yellow-600',
    bgClass: 'bg-yellow-500',
    borderClass: 'border-yellow-300',
    badgeVariant: 'secondary',
    pulseClass: '',
  },
  high: {
    icon: AlertOctagon,
    label: 'High',
    colorClass: 'text-orange-600',
    bgClass: 'bg-orange-500',
    borderClass: 'border-orange-300',
    badgeVariant: 'destructive',
    pulseClass: 'animate-pulse',
  },
  critical: {
    icon: Skull,
    label: 'Critical',
    colorClass: 'text-red-600',
    bgClass: 'bg-red-500',
    borderClass: 'border-red-300',
    badgeVariant: 'destructive',
    pulseClass: 'animate-pulse',
  },
};

/** Size configuration */
const sizeConfig = {
  sm: {
    container: 'gap-1',
    dot: 'h-2 w-2',
    icon: 'h-3 w-3',
    text: 'text-xs',
    badge: 'text-xs px-1.5 py-0',
  },
  md: {
    container: 'gap-1.5',
    dot: 'h-2.5 w-2.5',
    icon: 'h-4 w-4',
    text: 'text-sm',
    badge: 'text-xs px-2 py-0.5',
  },
  lg: {
    container: 'gap-2',
    dot: 'h-3 w-3',
    icon: 'h-5 w-5',
    text: 'text-base',
    badge: 'text-sm px-2.5 py-1',
  },
};

// =============================================================================
// Component
// =============================================================================

/**
 * RiskIndicator Component
 *
 * Displays a risk level indicator with color coding and optional tooltip.
 * The tooltip shows detailed risk factors and assessment reasoning.
 *
 * @example
 * ```tsx
 * <RiskIndicator
 *   level="high"
 *   score={75}
 *   factors={['File deletion', 'External API call']}
 *   reasoning="Operation involves file system changes and external network calls"
 *   size="md"
 *   showScore={true}
 *   showTooltip={true}
 * />
 * ```
 */
export const RiskIndicator: FC<RiskIndicatorProps> = ({
  level,
  score,
  factors = [],
  reasoning,
  size = 'md',
  showScore = false,
  showTooltip = true,
  onClick,
  className,
}) => {
  const config = riskConfig[level];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  const indicator = (
    <div
      className={cn(
        'inline-flex items-center',
        sizes.container,
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`Risk level: ${config.label}${showScore ? ` (${score}/100)` : ''}`}
    >
      {/* Risk Dot */}
      <span
        className={cn(
          'rounded-full',
          sizes.dot,
          config.bgClass,
          config.pulseClass
        )}
      />

      {/* Risk Label */}
      <span className={cn(sizes.text, config.colorClass, 'font-medium')}>
        {config.label}
      </span>

      {/* Risk Score */}
      {showScore && (
        <span className={cn(sizes.text, 'text-muted-foreground')}>
          ({score})
        </span>
      )}
    </div>
  );

  if (!showTooltip) {
    return indicator;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{indicator}</TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <div className="space-y-2">
            {/* Header */}
            <div className="flex items-center gap-2">
              <Icon className={cn('h-4 w-4', config.colorClass)} />
              <span className="font-medium">Risk Assessment: {config.label}</span>
            </div>

            {/* Score Bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Risk Score</span>
                <span className={cn('font-medium', config.colorClass)}>
                  {score}/100
                </span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all', config.bgClass)}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>

            {/* Divider */}
            {(factors.length > 0 || reasoning) && (
              <hr className="border-border" />
            )}

            {/* Risk Factors */}
            {factors.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-1">Risk Factors:</p>
                <ul className="text-xs text-muted-foreground space-y-0.5">
                  {factors.map((factor, index) => (
                    <li key={index} className="flex items-start gap-1.5">
                      <span className="text-muted-foreground mt-1">•</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Reasoning */}
            {reasoning && (
              <div>
                <p className="text-xs font-medium mb-1">Assessment Reasoning:</p>
                <p className="text-xs text-muted-foreground">{reasoning}</p>
              </div>
            )}

            {/* Level Guide */}
            <div className="pt-1 border-t border-border">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                  <span>Low</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
                  <span>Med</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-orange-500" />
                  <span>High</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                  <span>Crit</span>
                </div>
              </div>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export default RiskIndicator;
