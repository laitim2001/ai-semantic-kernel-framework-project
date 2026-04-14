/**
 * AgentRosterPanel — shows which experts will handle the task.
 *
 * Displayed after EXPERT_ROSTER_PREVIEW event, before execution starts.
 * Toggle is UI-only in Sprint 165.
 *
 * Sprint 165 — Phase 46 Agent Expert Registry.
 */

import { FC } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Users,
  ToggleLeft,
  ToggleRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DomainBadge, CapabilitiesChips } from './ExpertBadges';
import {
  useExpertSelectionStore,
  type RosterExpert,
} from '@/stores/expertSelectionStore';

// =============================================================================
// Component
// =============================================================================

export const AgentRosterPanel: FC = () => {
  const {
    rosterPreview,
    disabledExperts,
    isRosterVisible,
    toggleExpert,
    enableAll,
    disableAll,
    showRoster,
    hideRoster,
  } = useExpertSelectionStore();

  if (rosterPreview.length === 0) return null;

  return (
    <div className="px-4 pb-2">
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardContent className="p-3 space-y-2">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-semibold text-blue-800 dark:text-blue-200">
                Expert Roster Preview
              </span>
              <Badge variant="outline" className="text-[10px] h-4">
                {rosterPreview.length} agents
              </Badge>
            </div>
            <button
              onClick={isRosterVisible ? hideRoster : showRoster}
              className="text-muted-foreground hover:text-foreground"
            >
              {isRosterVisible ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          </div>

          {/* Roster list */}
          {isRosterVisible && (
            <>
              <div className="space-y-1.5">
                {rosterPreview.map((expert) => (
                  <RosterRow
                    key={expert.role}
                    expert={expert}
                    isDisabled={disabledExperts.has(expert.role)}
                    onToggle={() => toggleExpert(expert.role)}
                  />
                ))}
              </div>

              {/* Bulk actions */}
              <div className="flex items-center gap-2 pt-1 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-[10px]"
                  onClick={enableAll}
                >
                  Enable All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-[10px]"
                  onClick={disableAll}
                >
                  Disable All
                </Button>
                <span className="text-[10px] text-muted-foreground ml-auto">
                  Toggle is preview-only (Sprint 165)
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// =============================================================================
// RosterRow
// =============================================================================

interface RosterRowProps {
  expert: RosterExpert;
  isDisabled: boolean;
  onToggle: () => void;
}

const RosterRow: FC<RosterRowProps> = ({ expert, isDisabled, onToggle }) => {
  return (
    <div
      className={cn(
        'flex items-center justify-between p-2 rounded-md transition-colors',
        isDisabled
          ? 'bg-gray-100 dark:bg-gray-900/30 opacity-50'
          : 'bg-white dark:bg-gray-800/50'
      )}
    >
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <DomainBadge domain={expert.domain} />
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium truncate">
              {expert.expertName}
            </span>
            <span className="text-[10px] text-muted-foreground">
              ({expert.displayNameZh})
            </span>
          </div>
          <p className="text-[10px] text-muted-foreground truncate">
            {expert.taskTitle}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <CapabilitiesChips capabilities={expert.capabilities} maxDisplay={2} />
        <button onClick={onToggle} className="text-muted-foreground hover:text-foreground">
          {isDisabled ? (
            <ToggleLeft className="h-5 w-5" />
          ) : (
            <ToggleRight className="h-5 w-5 text-blue-600" />
          )}
        </button>
      </div>
    </div>
  );
};

export default AgentRosterPanel;
