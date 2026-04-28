/**
 * MemoryPage - Memory System Viewer
 *
 * Sprint 140: Phase 40 - Memory Management
 *
 * Memory search, user memory browsing, and statistics dashboard.
 */

import { useState } from 'react';
import {
  Brain,
  Search,
  Trash2,
  RefreshCw,
  Users,
  Database,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { formatRelativeTime } from '@/lib/utils';
import {
  useMemorySearch,
  useUserMemories,
  useMemoryStats,
  useDeleteMemory,
} from '@/hooks/useMemory';

// =============================================================================
// Component
// =============================================================================

export function MemoryPage() {
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [userIdInput, setUserIdInput] = useState('');
  const [activeUserId, setActiveUserId] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: stats } = useMemoryStats();
  const { data: searchResults, isLoading: searchLoading } = useMemorySearch(
    searchQuery,
    activeUserId || undefined
  );
  const { data: userMemories, isLoading: userLoading } = useUserMemories(activeUserId);
  const deleteMutation = useDeleteMemory();

  const handleSearch = () => {
    setSearchQuery(searchInput.trim());
    setActiveUserId(userIdInput.trim());
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Brain className="h-6 w-6" />
          記憶系統
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          查看和搜索 Agent 儲存的記憶，瀏覽使用者記憶歷史
        </p>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-gray-500 flex items-center gap-1">
                <Database className="h-4 w-4" />
                總記憶數
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-2xl font-bold">{stats.total_memories}</span>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-gray-500 flex items-center gap-1">
                <Users className="h-4 w-4" />
                使用者數
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-2xl font-bold">{stats.total_users}</span>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-gray-500 flex items-center gap-1">
                <Clock className="h-4 w-4" />
                最近更新
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-sm">
                {formatRelativeTime(stats.last_updated)}
              </span>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">記憶搜索</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="搜索記憶內容..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Input
              placeholder="User ID（可選）"
              value={userIdInput}
              onChange={(e) => setUserIdInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-48"
            />
            <Button onClick={handleSearch} disabled={!searchInput.trim()}>
              <Search className="h-4 w-4 mr-2" />
              搜索
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Search Results */}
      {searchLoading && (
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      )}

      {searchResults && searchQuery && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">
            搜索結果（{searchResults.total} 條）
          </h2>
          {searchResults.memories.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Brain className="h-8 w-8 mx-auto mb-2 text-gray-300" />
              <p>未找到相關記憶</p>
            </div>
          ) : (
            searchResults.memories.map((memory) => (
              <MemoryCard
                key={memory.id}
                id={memory.id}
                content={memory.content}
                score={memory.score}
                createdAt={memory.created_at}
                userId={memory.user_id}
                isExpanded={expandedId === memory.id}
                onToggle={() =>
                  setExpandedId(expandedId === memory.id ? null : memory.id)
                }
                onDelete={() => deleteMutation.mutate(memory.id)}
                deletePending={deleteMutation.isPending}
              />
            ))
          )}
        </div>
      )}

      {/* User Memories */}
      {activeUserId && !searchQuery && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">
            使用者記憶：{activeUserId}
          </h2>
          {userLoading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : !userMemories?.memories?.length ? (
            <div className="text-center py-8 text-gray-500">
              <p>此使用者暫無記憶</p>
            </div>
          ) : (
            userMemories.memories.map((memory) => (
              <MemoryCard
                key={memory.id}
                id={memory.id}
                content={memory.content}
                createdAt={memory.created_at}
                userId={memory.user_id}
                isExpanded={expandedId === memory.id}
                onToggle={() =>
                  setExpandedId(expandedId === memory.id ? null : memory.id)
                }
                onDelete={() => deleteMutation.mutate(memory.id)}
                deletePending={deleteMutation.isPending}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Memory Card Sub-component
// =============================================================================

function MemoryCard({
  id,
  content,
  score,
  createdAt,
  userId,
  isExpanded,
  onToggle,
  onDelete,
  deletePending,
}: {
  id: string;
  content: string;
  score?: number;
  createdAt: string;
  userId: string;
  isExpanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  deletePending: boolean;
}) {
  const preview = content.length > 100 ? content.slice(0, 100) + '...' : content;

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-2">
          <button
            onClick={onToggle}
            className="flex-1 text-left"
          >
            <p className="text-sm text-gray-800">
              {isExpanded ? content : preview}
            </p>
          </button>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={onToggle}
              className="p-1 rounded hover:bg-gray-100 text-gray-400"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              disabled={deletePending}
              className="text-red-500 hover:text-red-700 h-7 w-7 p-0"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
          <span>{formatRelativeTime(createdAt)}</span>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
            {userId}
          </Badge>
          {score !== undefined && (
            <span>相關度：{(score * 100).toFixed(1)}%</span>
          )}
          <span className="font-mono text-gray-400">{id.slice(0, 8)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
