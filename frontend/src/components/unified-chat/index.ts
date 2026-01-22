/**
 * Unified Chat Components
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * Sprint 65: S65-4 - UI Polish & Accessibility
 * Sprint 65: S65-5 - CustomUIRenderer Integration
 * Sprint 74: S74-1 - Chat History Panel
 * Phase 16: Unified Agentic Chat Interface
 * Phase 19: UI Enhancement
 *
 * Export all unified chat components for easy import.
 */

// S62-1: Base Architecture
export { ChatHeader } from './ChatHeader';
export { ChatInput } from './ChatInput';
export { StatusBar } from './StatusBar';

// S62-3: Chat Area
export { ChatArea } from './ChatArea';
export { MessageList } from './MessageList';
export type { MessageListProps } from './MessageList';
export { InlineApproval } from './InlineApproval';

// S62-4: Workflow Side Panel
export { WorkflowSidePanel } from './WorkflowSidePanel';
export { StepProgress } from './StepProgress';
export { ToolCallTracker } from './ToolCallTracker';
export { CheckpointList } from './CheckpointList';

// S69-2: Enhanced Step Progress with Sub-steps
export { StepProgressEnhanced, StatusIcon, SubStepItem } from './StepProgressEnhanced';
export type {
  SubStep as StepProgressSubStep,
  StepProgressEvent,
  SubStepStatusType,
} from './StepProgressEnhanced';

// S63-3: Mode Detection
export { ModeIndicator } from './ModeIndicator';
export type { ModeIndicatorProps } from './ModeIndicator';

// S64-1: Mode Switch Confirmation
export { ModeSwitchConfirmDialog } from './ModeSwitchConfirmDialog';
export type { ModeSwitchConfirmDialogProps } from './ModeSwitchConfirmDialog';

// S64-2: Approval Dialog
export { ApprovalDialog } from './ApprovalDialog';
export type { ApprovalDialogProps } from './ApprovalDialog';

// Sprint 99: Approval Message Card (inline approval as AI message)
export { ApprovalMessageCard } from './ApprovalMessageCard';
export type { ApprovalMessageCardProps } from './ApprovalMessageCard';

// S64-3: Risk Indicator
export { RiskIndicator } from './RiskIndicator';
export type { RiskIndicatorProps } from './RiskIndicator';

// S65-2: Restore Confirm Dialog
export { RestoreConfirmDialog } from './RestoreConfirmDialog';
export type { RestoreConfirmDialogProps } from './RestoreConfirmDialog';

// S65-3: Error Handling Components
export { ErrorBoundary, ErrorBoundaryWrapper } from './ErrorBoundary';
export type { ErrorBoundaryProps, ErrorBoundaryWrapperProps } from './ErrorBoundary';
export { ConnectionStatus } from './ConnectionStatus';
export type { ConnectionStatusProps } from './ConnectionStatus';

// S74-1: Chat History Panel
export { ChatHistoryPanel, ChatHistoryToggleButton } from './ChatHistoryPanel';
export type { ChatThread } from './ChatHistoryPanel';

// S75-2: File Upload
export { FileUpload, AttachButton, HiddenFileInput } from './FileUpload';
export type { FileUploadProps, AttachButtonProps, HiddenFileInputProps } from './FileUpload';

// S75-3: Attachment Preview
export { AttachmentPreview, CompactAttachmentPreview } from './AttachmentPreview';
export type { AttachmentPreviewProps, AttachmentItemProps, CompactAttachmentPreviewProps } from './AttachmentPreview';

// S76-2: FileMessage (for displaying generated files)
export { FileMessage, FileMessageList, CompactFileMessage } from './FileMessage';
export type { FileMessageProps, FileMessageListProps, CompactFileMessageProps, DownloadStatus } from './FileMessage';

// S76-3: FileRenderer (type-based file preview)
export { FileRenderer, getFileType } from './FileRenderer';
export type { FileRendererProps, FileType } from './FileRenderer';

// S76-3: Individual renderers
export { ImagePreview, CodePreview, TextPreview } from './renderers';
export type { ImagePreviewProps, CodePreviewProps, TextPreviewProps } from './renderers';

// Re-export types for convenience
export type {
  ChatHeaderProps,
  ChatInputProps,
  StatusBarProps,
  ChatAreaProps,
  InlineApprovalProps,
  WorkflowSidePanelProps,
  StepProgressProps,
  ToolCallTrackerProps,
  CheckpointListProps,
  ExecutionMode,
  ConnectionStatus as ConnectionStatusType,
} from '@/types/unified-chat';
