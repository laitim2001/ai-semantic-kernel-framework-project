// =============================================================================
// IPA Platform - Templates Page
// =============================================================================
// Sprint 5: Frontend UI - Template Marketplace
//
// Browse and use agent templates.
// =============================================================================

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Star, Download, Bot } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatNumber } from '@/lib/utils';
import type { Template } from '@/types';

const categories = [
  '全部',
  'IT Operations',
  'Customer Service',
  'Analytics',
  'HR',
  'Finance',
];

export function TemplatesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('全部');

  interface TemplateListResponse {
    templates: Template[];
    total: number;
    page: number;
    page_size: number;
  }

  const { data, isLoading } = useQuery({
    queryKey: ['templates', searchQuery, selectedCategory],
    queryFn: () => {
      // Don't send category param when "全部" is selected
      const categoryParam = selectedCategory === '全部' ? '' : `&category=${selectedCategory}`;
      return api.get<TemplateListResponse>(
        `/templates/?search=${searchQuery}${categoryParam}`
      );
    },
  });

  // Use mock data if API not available, handle response format
  const templates = Array.isArray(data) ? data : (data?.templates || generateMockTemplates());

  const filteredTemplates = templates.filter((t) => {
    const matchesSearch = t.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === '全部' || t.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  if (isLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">模板市場</h1>
        <p className="text-gray-500">瀏覽和使用預建 Agent 模板</p>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索模板..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {categories.map((category) => (
            <Button
              key={category}
              variant={selectedCategory === category ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(category)}
            >
              {category}
            </Button>
          ))}
        </div>
      </div>

      {/* Templates grid */}
      {filteredTemplates.length === 0 ? (
        <EmptyState
          title="找不到模板"
          description="嘗試調整搜索條件"
          icon={<Bot className="w-6 h-6 text-gray-400" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map((template) => (
            <Card
              key={template.id}
              className="hover:shadow-md transition-shadow"
            >
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-primary/20 to-primary/10 rounded-lg flex items-center justify-center shrink-0">
                    <Bot className="w-6 h-6 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {template.name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {template.description}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-2 flex-wrap">
                  <Badge variant="outline">{template.category}</Badge>
                  <Badge variant="secondary">v{template.version}</Badge>
                </div>

                <div className="mt-4 flex flex-wrap gap-1">
                  {template.tags.slice(0, 3).map((tag: string) => (
                    <span
                      key={tag}
                      className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-4 flex items-center justify-between pt-4 border-t">
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Star className="w-4 h-4 text-yellow-500" />
                      {template.rating.toFixed(1)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Download className="w-4 h-4" />
                      {formatNumber(template.downloads)}
                    </span>
                  </div>
                  <Button size="sm">使用模板</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// Generate mock data
function generateMockTemplates(): Template[] {
  return [
    {
      id: 'tpl-1',
      name: 'IT 支援 Agent',
      description: '處理常見 IT 支援請求，包括密碼重置、軟體安裝、設備問題等',
      category: 'IT Operations',
      version: '1.2.0',
      author: 'IPA Team',
      tags: ['IT', 'Support', 'ServiceNow'],
      config_schema: {},
      default_config: {},
      downloads: 1234,
      rating: 4.8,
      created_at: new Date().toISOString(),
    },
    {
      id: 'tpl-2',
      name: '客服回覆 Agent',
      description: '自動回覆客戶常見問題，支援多語言和情感分析',
      category: 'Customer Service',
      version: '2.0.0',
      author: 'IPA Team',
      tags: ['Customer Service', 'FAQ', 'Multilingual'],
      config_schema: {},
      default_config: {},
      downloads: 2567,
      rating: 4.9,
      created_at: new Date().toISOString(),
    },
    {
      id: 'tpl-3',
      name: '報表分析 Agent',
      description: '分析業務數據並生成智能報表摘要',
      category: 'Analytics',
      version: '1.0.0',
      author: 'IPA Team',
      tags: ['Analytics', 'Reports', 'Data'],
      config_schema: {},
      default_config: {},
      downloads: 567,
      rating: 4.5,
      created_at: new Date().toISOString(),
    },
    {
      id: 'tpl-4',
      name: 'HR 助理 Agent',
      description: '處理員工查詢，包括請假申請、政策問題等',
      category: 'HR',
      version: '1.1.0',
      author: 'IPA Team',
      tags: ['HR', 'Employee', 'Policy'],
      config_schema: {},
      default_config: {},
      downloads: 890,
      rating: 4.6,
      created_at: new Date().toISOString(),
    },
  ];
}
