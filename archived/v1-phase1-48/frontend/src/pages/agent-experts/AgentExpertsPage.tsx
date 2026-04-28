/**
 * AgentExpertsPage — List all agent expert definitions.
 *
 * Features: search, domain filter, card grid with DomainBadge + CapabilitiesChips.
 * Built-in experts show a lock icon, delete is disabled.
 *
 * Sprint 164 — Phase 46 Agent Expert Registry.
 */

import { FC, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Plus,
  Search,
  Lock,
  RefreshCw,
  Pencil,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useExpertsList, useDeleteExpert, useReloadExperts } from '@/hooks/useExperts';
import { DomainBadge, CapabilitiesChips } from '@/components/unified-chat/agent-team/ExpertBadges';

const DOMAIN_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'network', label: '網路' },
  { value: 'database', label: '資料庫' },
  { value: 'application', label: '應用層' },
  { value: 'security', label: '資安' },
  { value: 'cloud', label: '雲端' },
  { value: 'general', label: '通用' },
  { value: 'custom', label: '自訂' },
];

export const AgentExpertsPage: FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [domainFilter, setDomainFilter] = useState('');

  const { data, isLoading, refetch } = useExpertsList(
    domainFilter || undefined
  );
  const deleteMutation = useDeleteExpert();
  const reloadMutation = useReloadExperts();

  const experts = data?.experts ?? [];
  const filtered = experts.filter((e) =>
    searchQuery
      ? e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.description.toLowerCase().includes(searchQuery.toLowerCase())
      : true
  );

  const handleDelete = async (name: string) => {
    if (!confirm(`確定要刪除專家「${name}」嗎？此操作無法復原。`)) return;
    await deleteMutation.mutateAsync(name);
  };

  const handleReload = async () => {
    await reloadMutation.mutateAsync();
    refetch();
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agent 專家配置</h1>
          <p className="text-muted-foreground mt-1">
            管理 AI Agent 專家定義 — 每個專家有獨立的 prompt、工具、模型配置
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReload}
            disabled={reloadMutation.isPending}
          >
            <RefreshCw className={cn('h-4 w-4 mr-1', reloadMutation.isPending && 'animate-spin')} />
            Reload
          </Button>
          <Button onClick={() => navigate('/agent-experts/new')}>
            <Plus className="h-4 w-4 mr-1" />
            建立專家
          </Button>
        </div>
      </div>

      {/* Search + Filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜尋專家名稱..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex items-center gap-1">
          {DOMAIN_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDomainFilter(opt.value)}
              className={cn(
                'px-3 py-1.5 text-xs rounded-full font-medium transition-colors',
                domainFilter === opt.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="text-sm text-muted-foreground">
        {isLoading ? '載入中...' : `共 ${filtered.length} 個專家`}
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((expert) => (
          <Link
            key={expert.name}
            to={`/agent-experts/${expert.name}`}
            className="block"
          >
            <Card className="hover:shadow-md hover:border-primary/50 transition-all cursor-pointer h-full">
              <CardContent className="p-4 space-y-3">
                {/* Title row */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    {expert.is_builtin && (
                      <Lock className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                    )}
                    <span className="font-semibold text-sm truncate">
                      {expert.display_name}
                    </span>
                  </div>
                  <Badge
                    variant={expert.enabled ? 'default' : 'secondary'}
                    className="text-[10px] h-4"
                  >
                    {expert.enabled ? '啟用' : '停用'}
                  </Badge>
                </div>

                {/* Chinese name + domain */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {expert.display_name_zh}
                  </span>
                  <DomainBadge domain={expert.domain} />
                </div>

                {/* Description */}
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {expert.description || 'No description'}
                </p>

                {/* Capabilities */}
                <CapabilitiesChips
                  capabilities={expert.capabilities}
                  maxDisplay={3}
                />

                {/* Footer */}
                <div className="flex items-center justify-between pt-1 border-t">
                  <span className="text-[10px] text-muted-foreground font-mono">
                    v{expert.version} · {expert.tools.length} tools
                  </span>
                  <div className="flex items-center gap-1" onClick={(e) => e.preventDefault()}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => navigate(`/agent-experts/${expert.name}/edit`)}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    {!expert.is_builtin && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-destructive"
                        onClick={() => handleDelete(expert.name)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Empty state */}
      {!isLoading && filtered.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">沒有找到符合條件的專家</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => { setSearchQuery(''); setDomainFilter(''); }}
          >
            清除篩選
          </Button>
        </div>
      )}
    </div>
  );
};

export default AgentExpertsPage;
