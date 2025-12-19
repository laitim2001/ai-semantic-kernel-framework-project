// =============================================================================
// IPA Platform - Agent Detail Page
// =============================================================================
// Sprint 5: Frontend UI - S5-4 Agent Management
//
// Detailed view of a single agent with test interface.
// =============================================================================

import { useState, useRef, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Settings, Play, Send, Bot, User, Trash2 } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { formatNumber } from '@/lib/utils';
import type { Agent } from '@/types';

// 對話訊息類型
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [testInput, setTestInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', id],
    queryFn: () => api.get<Agent>(`/agents/${id}`),
    enabled: !!id,
  });

  // 自動滾動到最新訊息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const testMutation = useMutation({
    mutationFn: (message: string) =>
      api.post<{ result: string; stats: Record<string, unknown>; tool_calls: unknown[] }>(`/agents/${id}/run`, { message }),
    onSuccess: (data) => {
      // 添加 Agent 回應到對話
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.result,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    },
    onError: (error: Error) => {
      // 添加錯誤訊息
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `錯誤: ${error.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    },
  });

  if (isLoading) {
    return <PageLoading />;
  }

  // Use mock data if API not available
  const ag = agent || generateMockAgent(id || 'agent-1');

  const handleTest = () => {
    if (testInput.trim()) {
      // 添加用戶訊息到對話
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: testInput,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);

      // 發送請求
      testMutation.mutate(testInput);
      setTestInput('');
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className="space-y-6">
      {/* Back button and header */}
      <div className="flex items-center gap-4">
        <Link to="/agents">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex items-center gap-4 flex-1">
          <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{ag.name}</h1>
              <StatusBadge status={ag.status} />
            </div>
            <p className="text-gray-500">{ag.description}</p>
          </div>
        </div>
        <Link to={`/agents/${id}/edit`}>
          <Button variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            編輯
          </Button>
        </Link>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">類別</p>
            <p className="text-lg font-semibold mt-1">{ag.category || '未分類'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">執行次數</p>
            <p className="text-lg font-semibold mt-1">
              {formatNumber(ag.execution_count ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">平均響應時間</p>
            <p className="text-lg font-semibold mt-1">
              {ag.avg_response_time_ms ?? 0}ms
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">模型</p>
            <p className="text-lg font-semibold mt-1">
              {ag.model_config_data?.model || ag.model_config?.model || 'gpt-4o'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tools */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">工具列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            {ag.tools.map((tool) => (
              <Badge key={tool} variant="outline" className="text-sm py-1 px-3">
                {tool}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Test interface - 對話視窗 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Play className="w-5 h-5" />
            測試對話
          </CardTitle>
          {messages.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearChat}>
              <Trash2 className="w-4 h-4 mr-1" />
              清除對話
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex flex-col h-[400px]">
            {/* 對話歷史區域 */}
            <div className="flex-1 overflow-y-auto mb-4 space-y-4 p-4 bg-gray-50 rounded-lg border">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <Bot className="w-12 h-12 mb-3 opacity-50" />
                  <p className="text-sm">開始與 {ag.name} 對話</p>
                  <p className="text-xs mt-1">輸入訊息來測試 Agent 的回應</p>
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-3 ${
                        msg.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <Bot className="w-4 h-4 text-primary" />
                        </div>
                      )}
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                          msg.role === 'user'
                            ? 'bg-primary text-white rounded-br-md'
                            : 'bg-white border border-gray-200 rounded-bl-md'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        <p
                          className={`text-xs mt-1 ${
                            msg.role === 'user' ? 'text-white/70' : 'text-gray-400'
                          }`}
                        >
                          {msg.timestamp.toLocaleTimeString('zh-TW', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                          <User className="w-4 h-4 text-gray-600" />
                        </div>
                      )}
                    </div>
                  ))}
                  {testMutation.isPending && (
                    <div className="flex gap-3 justify-start">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-primary" />
                      </div>
                      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* 輸入區域 */}
            <div className="flex gap-2">
              <input
                type="text"
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                placeholder="輸入訊息..."
                className="flex-1 px-4 py-3 border border-gray-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleTest()}
                disabled={testMutation.isPending}
              />
              <Button
                onClick={handleTest}
                disabled={testMutation.isPending || !testInput.trim()}
                className="rounded-full w-12 h-12"
              >
                {testMutation.isPending ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Generate mock data
function generateMockAgent(id: string): Agent {
  return {
    id,
    name: 'IT 支援 Agent',
    description: '處理 IT 支援請求，包括密碼重置、軟體問題排查等',
    category: 'IT Operations',
    instructions: 'You are an IT support agent...',
    tools: ['ServiceNow', 'Active Directory', 'Email', 'Knowledge Base'],
    model_config: { model: 'gpt-4o', temperature: 0.7, max_tokens: 2000 },
    status: 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    execution_count: 256,
    avg_response_time_ms: 1200,
  };
}
