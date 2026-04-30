/**
 * KnowledgePage - Knowledge Base Management
 *
 * Sprint 140: Phase 40 - Knowledge Management
 *
 * Tab-based page: Document Management | Semantic Search | Skills List
 * With Qdrant service status indicator.
 */

import { useState, useRef } from 'react';
import {
  BookOpen,
  Upload,
  Search,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FileText,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/Table';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';
import {
  useDocuments,
  useKnowledgeSearch,
  useUploadDocument,
  useDeleteDocument,
  useSkills,
  useKnowledgeStatus,
} from '@/hooks/useKnowledge';

// =============================================================================
// Types
// =============================================================================

type TabId = 'documents' | 'search' | 'skills';

const tabs: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'documents', label: '文檔管理', icon: FileText },
  { id: 'search', label: '語義搜索', icon: Search },
  { id: 'skills', label: '技能列表', icon: Zap },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// =============================================================================
// Component
// =============================================================================

export function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<TabId>('documents');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const { data: statusData } = useKnowledgeStatus();
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();

  const handleUpload = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((file) => {
      uploadMutation.mutate({ file });
    });
  };

  const handleSearch = () => {
    setSearchQuery(searchInput.trim());
  };

  const isUnavailable = statusData?.status === 'unavailable';

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BookOpen className="h-6 w-6" />
            知識庫管理
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            管理 Agent 可使用的知識資源，上傳文檔並進行語義搜索
          </p>
        </div>
        {/* Service status */}
        {statusData && (
          <div className="flex items-center gap-2 text-sm">
            {statusData.status === 'healthy' ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-amber-500" />
            )}
            <span className="text-gray-600">
              向量服務：{statusData.status === 'healthy' ? '正常' : statusData.status}
            </span>
          </div>
        )}
      </div>

      {/* Service unavailable warning */}
      {isUnavailable && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 text-amber-700 rounded-lg border border-amber-200">
          <AlertTriangle className="h-5 w-5" />
          <span>向量資料庫服務目前不可用，部分功能可能受限。</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'documents' && (
        <DocumentsTab
          onUpload={handleUpload}
          uploadPending={uploadMutation.isPending}
          onDelete={(id) => deleteMutation.mutate(id)}
          deletePending={deleteMutation.isPending}
        />
      )}
      {activeTab === 'search' && (
        <SearchTab
          searchInput={searchInput}
          searchQuery={searchQuery}
          onInputChange={setSearchInput}
          onSearch={handleSearch}
        />
      )}
      {activeTab === 'skills' && <SkillsTab />}
    </div>
  );
}

// =============================================================================
// Documents Tab
// =============================================================================

function DocumentsTab({
  onUpload,
  uploadPending,
  onDelete,
  deletePending,
}: {
  onUpload: (files: FileList | null) => void;
  uploadPending: boolean;
  onDelete: (id: string) => void;
  deletePending: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { data, isLoading } = useDocuments();

  return (
    <div className="space-y-4">
      {/* Upload area */}
      <Card>
        <CardContent className="pt-6">
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              onUpload(e.dataTransfer.files);
            }}
          >
            <Upload className="h-8 w-8 mx-auto mb-2 text-gray-400" />
            <p className="text-sm text-gray-600">
              拖拽文件到此處或{' '}
              <span className="text-blue-600 font-medium">點擊上傳</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">
              支援 PDF、TXT、MD、DOCX 格式
            </p>
            {uploadPending && (
              <div className="mt-2 flex items-center justify-center gap-2 text-sm text-blue-600">
                <RefreshCw className="h-4 w-4 animate-spin" />
                上傳中...
              </div>
            )}
          </div>
          <input
            ref={(el) => { fileInputRef.current = el; }}
            type="file"
            className="hidden"
            accept=".pdf,.txt,.md,.docx"
            multiple
            onChange={(e) => onUpload(e.target.files)}
          />
        </CardContent>
      </Card>

      {/* Document list */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>文檔名稱</TableHead>
                <TableHead>格式</TableHead>
                <TableHead>大小</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>上傳時間</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!data?.documents?.length ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                    <p>暫無文檔</p>
                  </TableCell>
                </TableRow>
              ) : (
                data.documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium text-sm">{doc.name}</TableCell>
                    <TableCell className="text-xs uppercase text-gray-500">{doc.format}</TableCell>
                    <TableCell className="text-sm text-gray-600">{formatFileSize(doc.size)}</TableCell>
                    <TableCell>
                      <Badge variant={doc.status === 'indexed' ? 'secondary' : 'outline'}>
                        {doc.status === 'indexed' ? '已索引' : doc.status === 'processing' ? '處理中' : doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {formatRelativeTime(doc.uploaded_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(doc.id)}
                        disabled={deletePending}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Search Tab
// =============================================================================

function SearchTab({
  searchInput,
  searchQuery,
  onInputChange,
  onSearch,
}: {
  searchInput: string;
  searchQuery: string;
  onInputChange: (val: string) => void;
  onSearch: () => void;
}) {
  const { data, isLoading } = useKnowledgeSearch(searchQuery);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder="輸入搜索關鍵詞..."
          value={searchInput}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          className="flex-1"
        />
        <Button onClick={onSearch} disabled={!searchInput.trim()}>
          <Search className="h-4 w-4 mr-2" />
          搜索
        </Button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      )}

      {data && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">找到 {data.total} 個結果</p>
          {data.results.map((result, idx) => (
            <Card key={idx}>
              <CardContent className="pt-4">
                <p className="text-sm text-gray-800 whitespace-pre-wrap">
                  {result.content}
                </p>
                <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                  <span>相似度：{(result.score * 100).toFixed(1)}%</span>
                  <span>來源：{result.source_document}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Skills Tab
// =============================================================================

function SkillsTab() {
  const { data, isLoading } = useSkills();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="border rounded-lg">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>技能名稱</TableHead>
            <TableHead>描述</TableHead>
            <TableHead>狀態</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {!data?.skills?.length ? (
            <TableRow>
              <TableCell colSpan={3} className="text-center py-8 text-gray-500">
                <Zap className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                <p>暫無技能</p>
              </TableCell>
            </TableRow>
          ) : (
            data.skills.map((skill) => (
              <TableRow key={skill.name}>
                <TableCell className="font-medium text-sm">{skill.name}</TableCell>
                <TableCell className="text-sm text-gray-600">{skill.description}</TableCell>
                <TableCell>
                  <Badge variant={skill.status === 'active' ? 'default' : 'outline'}>
                    {skill.status === 'active' ? '啟用' : '停用'}
                  </Badge>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
