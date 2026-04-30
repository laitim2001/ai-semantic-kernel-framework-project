/**
 * API Endpoints Index
 *
 * Central export for all API endpoint modules.
 */

// AG-UI API (Sprint 64-65)
export {
  aguiApi,
  type ApprovalResponse,
  type RejectRequest,
  type ThreadInfo,
  type CreateThreadRequest,
  type CreateThreadResponse,
  type RestoreCheckpointResponse,
} from './ag-ui';

// Files API (Sprint 75)
export {
  filesApi,
  uploadFile,
  listFiles,
  getFile,
  deleteFile,
  getFileContentUrl,
  formatFileSize,
  getFileCategory,
  isAllowedFileType,
  getMaxFileSize,
  type FileCategory,
  type FileStatus,
  type FileMetadata,
  type FileUploadResponse,
  type FileListResponse,
  type FileUploadProgress,
} from './files';

// Orchestrator Chat API (Sprint 138 - Phase 40)
export {
  orchestratorApi,
  type OrchestratorMessage,
  type OrchestratorMessageMetadata,
  type OrchestratorToolCall,
  type SendOrchestratorMessageRequest,
  type SendOrchestratorMessageResponse,
  type OrchestratorHealthResponse,
  type OrchestratorSSEEventType,
  type OrchestratorSSEEvent,
} from './orchestrator';

// Sessions API (Sprint 138 - Phase 40)
export {
  sessionsApi,
  type SessionStatus,
  type SessionSummary,
  type SessionDetail,
  type SessionMessage,
  type SessionListResponse,
  type SessionMessagesResponse,
  type SessionResumeResponse,
  type SessionFilters,
} from './sessions';

// Tasks API (Sprint 139 - Phase 40)
export {
  tasksApi,
  type TaskStatus,
  type TaskPriority,
  type TaskStepStatus,
  type TaskSummary,
  type TaskStep,
  type TaskDetail,
  type TaskListResponse,
  type TaskStepsResponse,
  type TaskFilters,
} from './tasks';

// Knowledge API (Sprint 140 - Phase 40)
export {
  knowledgeApi,
  type DocumentStatus,
  type KnowledgeDocument,
  type DocumentListResponse,
  type KnowledgeSearchResult,
  type KnowledgeSearchResponse,
  type KnowledgeSearchOptions,
  type AgentSkill,
  type SkillsResponse,
  type KnowledgeStatusResponse,
  type DocumentFilters,
} from './knowledge';

// Memory API (Sprint 140 - Phase 40)
export {
  memoryApi,
  type MemoryItem,
  type MemorySearchResponse,
  type UserMemoriesResponse,
  type MemoryStats,
  type UserMemoryOptions,
} from './memory';

// Orchestration API (Sprint 99 - Phase 28)
export {
  orchestrationApi,
  type ITIntentCategory,
  type RiskLevel,
  type WorkflowType,
  type CompletenessInfo,
  type RoutingDecision,
  type RiskFactor,
  type RiskAssessment,
  type IntentClassifyResponse,
  type IntentClassifyRequest,
  type DialogQuestion,
  type DialogStatusResponse,
  type StartDialogRequest,
  type RespondToDialogRequest,
  type ApprovalSummary,
  type ApprovalListResponse,
  type ApprovalDecisionRequest,
  type ApprovalDecisionResponse,
  type HybridExecuteRequest,
  type HybridExecuteResponse,
} from './orchestration';
