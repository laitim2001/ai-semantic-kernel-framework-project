/**
 * ExpertBadges Component
 *
 * Displays domain badges and capability chips for agents
 * powered by the Agent Expert Registry.
 *
 * Sprint 161 — Phase 46 Agent Expert Registry.
 */

import { FC } from 'react';
import { Badge } from '@/components/ui/Badge';
import {
  Globe,
  Database,
  Code,
  Shield,
  Cloud,
  HelpCircle,
  Settings,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Domain Configuration
// =============================================================================

interface DomainConfigItem {
  label: string;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  borderColor: string;
}

const DOMAIN_CONFIG: Record<string, DomainConfigItem> = {
  network: {
    label: '網路',
    icon: Globe,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    borderColor: 'border-blue-200 dark:border-blue-800',
  },
  database: {
    label: '資料庫',
    icon: Database,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    borderColor: 'border-purple-200 dark:border-purple-800',
  },
  application: {
    label: '應用層',
    icon: Code,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-950/30',
    borderColor: 'border-green-200 dark:border-green-800',
  },
  security: {
    label: '資安',
    icon: Shield,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    borderColor: 'border-red-200 dark:border-red-800',
  },
  cloud: {
    label: '雲端',
    icon: Cloud,
    color: 'text-cyan-600 dark:text-cyan-400',
    bgColor: 'bg-cyan-50 dark:bg-cyan-950/30',
    borderColor: 'border-cyan-200 dark:border-cyan-800',
  },
  general: {
    label: '通用',
    icon: HelpCircle,
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-950/30',
    borderColor: 'border-gray-200 dark:border-gray-800',
  },
  custom: {
    label: '自訂',
    icon: Settings,
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-950/30',
    borderColor: 'border-orange-200 dark:border-orange-800',
  },
};

const DEFAULT_DOMAIN_CONFIG: DomainConfigItem = DOMAIN_CONFIG.general;

// =============================================================================
// DomainBadge
// =============================================================================

interface DomainBadgeProps {
  domain: string;
  className?: string;
}

/**
 * DomainBadge — color-coded badge showing the expert's domain.
 */
export const DomainBadge: FC<DomainBadgeProps> = ({ domain, className }) => {
  const config = DOMAIN_CONFIG[domain] || DEFAULT_DOMAIN_CONFIG;
  const Icon = config.icon;

  return (
    <Badge
      variant="outline"
      className={cn(
        'text-xs h-5 px-1.5',
        config.color,
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      <Icon className="h-3 w-3 mr-1" />
      {config.label}
    </Badge>
  );
};

// =============================================================================
// CapabilitiesChips
// =============================================================================

interface CapabilitiesChipsProps {
  capabilities: string[];
  maxDisplay?: number;
  className?: string;
}

/**
 * CapabilitiesChips — renders capability tags as small outline badges.
 */
export const CapabilitiesChips: FC<CapabilitiesChipsProps> = ({
  capabilities,
  maxDisplay = 4,
  className,
}) => {
  if (!capabilities || capabilities.length === 0) return null;

  const displayed = capabilities.slice(0, maxDisplay);
  const remaining = capabilities.length - maxDisplay;

  return (
    <div className={cn('flex items-center gap-1 flex-wrap', className)}>
      {displayed.map((cap) => (
        <Badge
          key={cap}
          variant="outline"
          className="text-[10px] h-4 px-1 font-normal text-muted-foreground"
        >
          {cap.replace(/_/g, ' ')}
        </Badge>
      ))}
      {remaining > 0 && (
        <span className="text-[10px] text-muted-foreground">
          +{remaining}
        </span>
      )}
    </div>
  );
};

export default DomainBadge;
