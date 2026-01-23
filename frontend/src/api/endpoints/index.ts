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
