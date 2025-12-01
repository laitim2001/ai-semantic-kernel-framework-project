# Technical Architecture Design (Part 2)
# 核心模塊設計、集成架構、安全與監控

**接續主文檔**: [technical-architecture.md](./technical-architecture.md)

---

## 5. 核心模塊設計

### 5.1 API Gateway

#### 職責

- **請求路由**: 根據 URL 路徑路由到對應服務
- **認證授權**: OAuth 2.0 + JWT token 驗證
- **限流控制**: 防止 API 濫用
- **負載均衡**: 分發流量到多個服務實例
- **協議轉換**: HTTP → gRPC, REST → GraphQL
- **監控埋點**: 記錄請求指標

#### 技術選型: Kong API Gateway

**配置示例**:
```yaml
services:
  - name: workflow-service
    url: http://workflow-service:3000
    routes:
      - name: workflows-api
        paths: ["/api/v1/workflows"]
        methods: ["GET", "POST", "PUT", "DELETE"]
    plugins:
      - name: jwt
        config:
          secret_is_base64: false
      - name: rate-limiting
        config:
          minute: 100
          policy: local
      - name: cors
        config:
          origins: ["*"]
          methods: ["GET", "POST", "PUT", "DELETE"]

  - name: execution-service
    url: http://execution-service:5000
    routes:
      - name: executions-api
        paths: ["/api/v1/executions"]
    plugins:
      - name: request-transformer
        config:
          add:
            headers: ["X-Trace-Id:$(uuid)"]
```

#### 限流策略

```typescript
// Rate Limiting Configuration
const rateLimits = {
  anonymous: {
    minute: 20,
    hour: 100
  },
  authenticated: {
    minute: 100,
    hour: 1000
  },
  premium: {
    minute: 500,
    hour: 10000
  }
};

// Token Bucket Algorithm
class RateLimiter {
  async isAllowed(userId: string, tier: string): Promise<boolean> {
    const key = `rate_limit:${userId}:${tier}`;
    const limit = rateLimits[tier].minute;
    
    const current = await redis.get(key);
    if (!current || parseInt(current) < limit) {
      await redis.incr(key);
      await redis.expire(key, 60);
      return true;
    }
    return false;
  }
}
```

---

### 5.2 Workflow Service

#### 職責

- **工作流 CRUD**: 創建、查詢、更新、刪除工作流
- **版本管理**: 工作流配置版本控制
- **驗證邏輯**: 工作流配置合法性驗證
- **模板管理**: 工作流模板庫

#### API 設計

**REST API**:
```typescript
// POST /api/v1/workflows
interface CreateWorkflowRequest {
  name: string;
  description?: string;
  category: string;
  triggerConfig: {
    type: 'n8n_webhook' | 'api_call' | 'scheduled' | 'manual';
    config: {
      webhookUrl?: string;
      hmacSecret?: string;
      schedule?: string; // cron expression
    };
  };
  agentChain: AgentConfig[];
  retryConfig?: RetryConfig;
  notificationConfig?: NotificationConfig;
}

interface AgentConfig {
  agentId: string;
  sequenceOrder: number;
  inputMapping?: Record<string, string>;
  timeout?: number;
  maxRetries?: number;
}

interface RetryConfig {
  maxRetries: number;
  backoffStrategy: 'fixed' | 'exponential' | 'linear';
  initialDelay: number;
  maxDelay: number;
  multiplier?: number;
}
```

**GraphQL Schema**:
```graphql
type Workflow {
  id: ID!
  name: String!
  description: String
  category: String!
  triggerConfig: TriggerConfig!
  agentChain: [AgentConfig!]!
  retryConfig: RetryConfig
  notificationConfig: NotificationConfig
  status: WorkflowStatus!
  version: Int!
  createdAt: DateTime!
  updatedAt: DateTime!
  createdBy: User!
  
  # Relationships
  executions(
    limit: Int = 10
    offset: Int = 0
    status: ExecutionStatus
  ): ExecutionConnection!
  
  # Aggregations
  totalExecutions: Int!
  successRate: Float!
  avgExecutionTime: Int!
}

type Query {
  workflow(id: ID!): Workflow
  workflows(
    filter: WorkflowFilter
    sort: WorkflowSort
    limit: Int = 20
    offset: Int = 0
  ): WorkflowConnection!
}

type Mutation {
  createWorkflow(input: CreateWorkflowInput!): Workflow!
  updateWorkflow(id: ID!, input: UpdateWorkflowInput!): Workflow!
  deleteWorkflow(id: ID!): Boolean!
  cloneWorkflow(id: ID!, name: String!): Workflow!
}
```

#### 核心邏輯實現

**工作流驗證器**:
```typescript
class WorkflowValidator {
  validate(workflow: CreateWorkflowRequest): ValidationResult {
    const errors: ValidationError[] = [];
    
    // 1. 基本信息驗證
    if (!workflow.name || workflow.name.length < 3) {
      errors.push({
        field: 'name',
        message: 'Workflow name must be at least 3 characters'
      });
    }
    
    // 2. Trigger 配置驗證
    if (workflow.triggerConfig.type === 'n8n_webhook') {
      if (!workflow.triggerConfig.config.webhookUrl) {
        errors.push({
          field: 'triggerConfig.config.webhookUrl',
          message: 'Webhook URL is required for n8n trigger'
        });
      }
    }
    
    // 3. Agent Chain 驗證
    if (workflow.agentChain.length === 0) {
      errors.push({
        field: 'agentChain',
        message: 'At least one agent is required'
      });
    }
    
    // 檢查 sequenceOrder 連續性
    const orders = workflow.agentChain.map(a => a.sequenceOrder).sort();
    for (let i = 0; i < orders.length; i++) {
      if (orders[i] !== i + 1) {
        errors.push({
          field: 'agentChain',
          message: `Agent sequence order must be continuous, missing order ${i + 1}`
        });
        break;
      }
    }
    
    // 4. 重試配置驗證
    if (workflow.retryConfig) {
      if (workflow.retryConfig.maxRetries < 0 || workflow.retryConfig.maxRetries > 10) {
        errors.push({
          field: 'retryConfig.maxRetries',
          message: 'Max retries must be between 0 and 10'
        });
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }
}
```

---

### 5.3 Execution Service

#### 職責

- **執行調度**: 從消息隊列消費執行請求
- **狀態管理**: 管理執行生命週期狀態
- **重試邏輯**: 實現指數退避重試
- **DLQ 處理**: 失敗執行進入死信隊列
- **執行編排**: 協調 Agent 順序執行

#### 狀態機設計

```typescript
enum ExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  DLQ = 'dlq'
}

class ExecutionStateMachine {
  private transitions: Map<ExecutionStatus, ExecutionStatus[]> = new Map([
    [ExecutionStatus.PENDING, [ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED]],
    [ExecutionStatus.RUNNING, [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]],
    [ExecutionStatus.FAILED, [ExecutionStatus.PENDING, ExecutionStatus.DLQ]], // Retry or DLQ
    [ExecutionStatus.COMPLETED, []],
    [ExecutionStatus.CANCELLED, []],
    [ExecutionStatus.DLQ, [ExecutionStatus.PENDING]] // Manual retry from DLQ
  ]);
  
  canTransition(from: ExecutionStatus, to: ExecutionStatus): boolean {
    const allowed = this.transitions.get(from);
    return allowed?.includes(to) ?? false;
  }
  
  async transition(executionId: string, to: ExecutionStatus): Promise<void> {
    const execution = await this.getExecution(executionId);
    
    if (!this.canTransition(execution.status, to)) {
      throw new Error(
        `Invalid state transition from ${execution.status} to ${to}`
      );
    }
    
    await this.updateExecutionStatus(executionId, to);
    await this.emitStatusChangeEvent(executionId, execution.status, to);
  }
}
```

#### 重試策略實現

```csharp
// C# .NET Implementation
public class RetryStrategy
{
    public enum BackoffType
    {
        Fixed,
        Exponential,
        Linear
    }
    
    public class RetryConfig
    {
        public int MaxRetries { get; set; } = 3;
        public BackoffType BackoffStrategy { get; set; } = BackoffType.Exponential;
        public int InitialDelayMs { get; set; } = 1000;
        public int MaxDelayMs { get; set; } = 60000;
        public double Multiplier { get; set; } = 2.0;
    }
    
    public static int CalculateDelay(RetryConfig config, int retryCount)
    {
        int delay = config.BackoffStrategy switch
        {
            BackoffType.Fixed => config.InitialDelayMs,
            BackoffType.Linear => config.InitialDelayMs * (retryCount + 1),
            BackoffType.Exponential => (int)(config.InitialDelayMs * Math.Pow(config.Multiplier, retryCount)),
            _ => config.InitialDelayMs
        };
        
        return Math.Min(delay, config.MaxDelayMs);
    }
    
    public static async Task<T> ExecuteWithRetry<T>(
        Func<Task<T>> operation,
        RetryConfig config,
        CancellationToken cancellationToken = default)
    {
        int retryCount = 0;
        Exception lastException = null;
        
        while (retryCount <= config.MaxRetries)
        {
            try
            {
                return await operation();
            }
            catch (Exception ex)
            {
                lastException = ex;
                retryCount++;
                
                if (retryCount > config.MaxRetries)
                {
                    break;
                }
                
                int delay = CalculateDelay(config, retryCount);
                await Task.Delay(delay, cancellationToken);
            }
        }
        
        throw new Exception($"Operation failed after {config.MaxRetries} retries", lastException);
    }
}
```

#### 執行編排器

```csharp
public class ExecutionOrchestrator
{
    private readonly IAgentService _agentService;
    private readonly IExecutionRepository _executionRepo;
    private readonly IMessagePublisher _messagePublisher;
    
    public async Task<ExecutionResult> ExecuteWorkflow(
        Guid executionId,
        Workflow workflow,
        Dictionary<string, object> inputData,
        CancellationToken cancellationToken)
    {
        await UpdateExecutionStatus(executionId, ExecutionStatus.Running);
        
        var context = new ExecutionContext
        {
            ExecutionId = executionId,
            WorkflowId = workflow.Id,
            Variables = new Dictionary<string, object>(inputData),
            StartTime = DateTime.UtcNow
        };
        
        try
        {
            // 按順序執行 Agent Chain
            foreach (var agentConfig in workflow.AgentChain.OrderBy(a => a.SequenceOrder))
            {
                var agentResult = await ExecuteAgent(
                    agentConfig,
                    context,
                    cancellationToken
                );
                
                // 保存 Agent 執行結果
                await SaveAgentExecution(executionId, agentConfig, agentResult);
                
                // 將輸出合併到上下文
                context.Variables[agentConfig.AgentId] = agentResult.Output;
                
                // 檢查是否失敗
                if (!agentResult.Success)
                {
                    if (ShouldRetry(agentConfig, agentResult))
                    {
                        await ScheduleRetry(executionId, agentConfig.SequenceOrder);
                        throw new AgentExecutionException(agentResult.ErrorMessage);
                    }
                    else
                    {
                        await MoveToDLQ(executionId, agentResult.ErrorMessage);
                        throw new AgentExecutionException("Moved to DLQ after max retries");
                    }
                }
            }
            
            // 所有 Agent 執行成功
            await UpdateExecutionStatus(executionId, ExecutionStatus.Completed);
            
            return new ExecutionResult
            {
                Success = true,
                Output = context.Variables,
                Duration = DateTime.UtcNow - context.StartTime
            };
        }
        catch (Exception ex)
        {
            await UpdateExecutionStatus(executionId, ExecutionStatus.Failed);
            await _messagePublisher.PublishNotification(
                new ExecutionFailedEvent(executionId, ex.Message)
            );
            
            return new ExecutionResult
            {
                Success = false,
                ErrorMessage = ex.Message,
                Duration = DateTime.UtcNow - context.StartTime
            };
        }
    }
    
    private async Task<AgentResult> ExecuteAgent(
        AgentConfig agentConfig,
        ExecutionContext context,
        CancellationToken cancellationToken)
    {
        var retryConfig = new RetryStrategy.RetryConfig
        {
            MaxRetries = agentConfig.MaxRetries ?? 3,
            BackoffStrategy = RetryStrategy.BackoffType.Exponential
        };
        
        return await RetryStrategy.ExecuteWithRetry(
            async () =>
            {
                // 準備輸入數據
                var agentInput = PrepareAgentInput(agentConfig, context);
                
                // 調用 Agent Service
                using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(agentConfig.Timeout ?? 300));
                return await _agentService.ExecuteAgent(
                    agentConfig.AgentId,
                    agentInput,
                    cts.Token
                );
            },
            retryConfig,
            cancellationToken
        );
    }
}
```

---

### 5.4 Agent Service

#### 職責

- **Agent 運行時**: 執行 Agent Framework Agent
- **Prompt 管理**: 加載和渲染 Prompt 模板
- **Tool 集成**: 管理和調用外部 Tool
- **結果緩存**: 緩存相同輸入的 Agent 結果

#### Agent Framework 集成

```csharp
public class AgentFrameworkService : IAgentService
{
    private readonly IKernel _kernel;
    private readonly IPromptTemplateEngine _templateEngine;
    private readonly IToolRegistry _toolRegistry;
    private readonly ILogger<AgentFrameworkService> _logger;
    
    public async Task<AgentResult> ExecuteAgent(
        Guid agentId,
        Dictionary<string, object> input,
        CancellationToken cancellationToken)
    {
        var agent = await LoadAgent(agentId);
        
        // 1. 加載 Prompt 模板
        var prompt = await _templateEngine.RenderPrompt(
            agent.PromptTemplate,
            input
        );
        
        // 2. 注冊 Tools
        var tools = await _toolRegistry.GetTools(agent.ToolConfigs);
        foreach (var tool in tools)
        {
            _kernel.ImportFunctions(tool, tool.Name);
        }
        
        // 3. 配置 Agent 類型
        var agentConfig = agent.Type switch
        {
            AgentType.ReAct => CreateReActAgent(prompt, tools),
            AgentType.PlanAndExecute => CreatePlanAndExecuteAgent(prompt, tools),
            AgentType.Custom => CreateCustomAgent(prompt, tools),
            _ => throw new ArgumentException($"Unknown agent type: {agent.Type}")
        };
        
        // 4. 執行 Agent
        var startTime = DateTime.UtcNow;
        try
        {
            var result = await agentConfig.RunAsync(prompt, cancellationToken);
            
            var duration = DateTime.UtcNow - startTime;
            
            // 5. 計算 Token 使用和成本
            var tokenUsage = CalculateTokenUsage(result);
            var cost = CalculateCost(tokenUsage);
            
            return new AgentResult
            {
                Success = true,
                Output = result.GetValue<object>(),
                TokensUsed = tokenUsage.Total,
                CostUsd = cost,
                Duration = duration
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Agent execution failed: {AgentId}", agentId);
            return new AgentResult
            {
                Success = false,
                ErrorMessage = ex.Message,
                Duration = DateTime.UtcNow - startTime
            };
        }
    }
    
    private IAgent CreateReActAgent(string prompt, IEnumerable<ITool> tools)
    {
        return _kernel.CreateAgent(new AgentConfig
        {
            Name = "ReActAgent",
            Instructions = prompt,
            Kernel = _kernel,
            Tools = tools
        });
    }
}
```

#### Tool 抽象與實現

```csharp
// Tool 接口
public interface ITool
{
    string Name { get; }
    string Description { get; }
    Task<object> ExecuteAsync(Dictionary<string, object> parameters, CancellationToken cancellationToken);
}

// HTTP API Tool
public class HttpApiTool : ITool
{
    public string Name { get; init; }
    public string Description { get; init; }
    
    private readonly HttpClient _httpClient;
    private readonly string _endpoint;
    private readonly HttpMethod _method;
    
    public async Task<object> ExecuteAsync(
        Dictionary<string, object> parameters,
        CancellationToken cancellationToken)
    {
        var request = new HttpRequestMessage(_method, _endpoint);
        
        if (_method == HttpMethod.Post || _method == HttpMethod.Put)
        {
            request.Content = JsonContent.Create(parameters);
        }
        
        var response = await _httpClient.SendAsync(request, cancellationToken);
        response.EnsureSuccessStatusCode();
        
        return await response.Content.ReadFromJsonAsync<object>(cancellationToken);
    }
}

// Database Query Tool
public class DatabaseQueryTool : ITool
{
    public string Name { get; init; }
    public string Description { get; init; }
    
    private readonly IDbConnection _dbConnection;
    private readonly string _queryTemplate;
    
    public async Task<object> ExecuteAsync(
        Dictionary<string, object> parameters,
        CancellationToken cancellationToken)
    {
        var query = RenderQuery(_queryTemplate, parameters);
        
        using var command = _dbConnection.CreateCommand();
        command.CommandText = query;
        
        foreach (var param in parameters)
        {
            var dbParam = command.CreateParameter();
            dbParam.ParameterName = $"@{param.Key}";
            dbParam.Value = param.Value;
            command.Parameters.Add(dbParam);
        }
        
        using var reader = await command.ExecuteReaderAsync(cancellationToken);
        var results = new List<Dictionary<string, object>>();
        
        while (await reader.ReadAsync(cancellationToken))
        {
            var row = new Dictionary<string, object>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.GetValue(i);
            }
            results.Add(row);
        }
        
        return results;
    }
}
```

---

## 6. 集成架構

### 6.1 n8n 平台集成

#### Webhook 接收

```typescript
// Workflow Service - Webhook Handler
@Post('/api/v1/webhooks/:workflowId')
async handleN8nWebhook(
  @Param('workflowId') workflowId: string,
  @Headers('x-n8n-signature') signature: string,
  @Body() payload: any
): Promise<{ executionId: string }> {
  
  // 1. 驗證 HMAC 簽名
  const workflow = await this.workflowService.getWorkflow(workflowId);
  const isValid = this.verifyHmacSignature(
    payload,
    signature,
    workflow.triggerConfig.hmacSecret
  );
  
  if (!isValid) {
    throw new UnauthorizedException('Invalid HMAC signature');
  }
  
  // 2. 創建執行記錄
  const execution = await this.executionService.createExecution({
    workflowId,
    triggeredBy: 'n8n_webhook',
    inputData: payload,
    status: ExecutionStatus.PENDING
  });
  
  // 3. 發布到消息隊列
  await this.messageQueue.publish('execution.start', {
    executionId: execution.id,
    workflowId,
    inputData: payload
  });
  
  // 4. 返回執行 ID (n8n 可用於追蹤)
  return { executionId: execution.id };
}

private verifyHmacSignature(
  payload: any,
  signature: string,
  secret: string
): boolean {
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(JSON.stringify(payload));
  const expectedSignature = hmac.digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}
```

#### n8n Workflow 配置示例

```json
{
  "name": "Trigger IPA Workflow",
  "nodes": [
    {
      "name": "When Customer Registers",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "webhookId": "customer-register",
      "parameters": {
        "path": "customer-register",
        "responseMode": "onReceived",
        "httpMethod": "POST"
      }
    },
    {
      "name": "Call IPA Platform",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300],
      "parameters": {
        "url": "https://ipa.example.com/api/v1/webhooks/{{$node['Config'].json['workflowId']}}",
        "method": "POST",
        "body": "={{$json}}",
        "authentication": "genericCredentialType",
        "headers": {
          "x-n8n-signature": "={{$node['Generate HMAC'].json['signature']}}"
        }
      }
    },
    {
      "name": "Generate HMAC",
      "type": "n8n-nodes-base.function",
      "position": [350, 200],
      "parameters": {
        "functionCode": "const crypto = require('crypto');\nconst secret = '{{$node['Config'].json['hmacSecret']}}';\nconst hmac = crypto.createHmac('sha256', secret);\nhmac.update(JSON.stringify(items[0].json));\nreturn [{json: {signature: hmac.digest('hex')}}];"
      }
    }
  ]
}
```

---

### 6.2 Microsoft Teams 集成

#### Adaptive Card 通知

```typescript
// Notification Service
export class TeamsNotificationService {
  async sendExecutionFailedNotification(execution: Execution): Promise<void> {
    const workflow = await this.workflowService.getWorkflow(execution.workflowId);
    
    const card = {
      type: 'message',
      attachments: [{
        contentType: 'application/vnd.microsoft.card.adaptive',
        content: {
          $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
          type: 'AdaptiveCard',
          version: '1.4',
          body: [
            {
              type: 'TextBlock',
              text: '⚠️ Workflow Execution Failed',
              weight: 'Bolder',
              size: 'Large',
              color: 'Attention'
            },
            {
              type: 'FactSet',
              facts: [
                { title: 'Workflow', value: workflow.name },
                { title: 'Execution ID', value: execution.id },
                { title: 'Failed At', value: new Date(execution.completedAt).toLocaleString() },
                { title: 'Duration', value: `${execution.durationMs / 1000}s` },
                { title: 'Error', value: execution.errorDetails.message }
              ]
            },
            {
              type: 'TextBlock',
              text: execution.errorDetails.stackTrace,
              wrap: true,
              fontType: 'Monospace',
              size: 'Small'
            }
          ],
          actions: [
            {
              type: 'Action.OpenUrl',
              title: 'View Execution',
              url: `https://ipa.example.com/executions/${execution.id}`
            },
            {
              type: 'Action.Http',
              title: 'Retry',
              method: 'POST',
              url: `https://ipa.example.com/api/v1/executions/${execution.id}/retry`,
              headers: [
                { name: 'Authorization', value: 'Bearer {{token}}' }
              ]
            }
          ]
        }
      }]
    };
    
    await axios.post(workflow.notificationConfig.teamsWebhookUrl, card);
  }
}
```

---

**待續**: 下一部分將包含安全架構、監控日誌、部署架構等內容。

**文檔狀態**: 第 2 部分完成 (核心模塊設計、集成架構) ✅
