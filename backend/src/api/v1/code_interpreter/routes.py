"""
Code Interpreter API Routes

提供 Azure OpenAI Code Interpreter 功能的 REST API 端點。

Sprint 37: Phase 8 - Code Interpreter Integration
Sprint 38: File Storage Integration

Endpoints:
    POST /code-interpreter/execute     - 執行 Python 代碼
    POST /code-interpreter/analyze     - 分析任務
    POST /code-interpreter/sessions    - 創建會話
    DELETE /code-interpreter/sessions/{session_id} - 刪除會話
    GET /code-interpreter/health       - 健康檢查

    # Sprint 38: File Operations
    POST /code-interpreter/files/upload    - 上傳文件
    GET /code-interpreter/files            - 列出文件
    GET /code-interpreter/files/{file_id}  - 下載文件
    DELETE /code-interpreter/files/{file_id} - 刪除文件
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4
import logging
import io

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse

from src.core.config import get_settings
from src.integrations.agent_framework.builders.code_interpreter import (
    CodeInterpreterAdapter,
    CodeInterpreterConfig,
)
from src.integrations.agent_framework.assistant import (
    ConfigurationError,
    AssistantNotFoundError,
    FileStorageService,
    get_file_service,
)

from . import schemas

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/code-interpreter",
    tags=["Code Interpreter"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)

# Session storage (in-memory for MVP, Redis/DB for production)
_sessions: Dict[str, CodeInterpreterAdapter] = {}


def _get_session(session_id: str) -> Optional[CodeInterpreterAdapter]:
    """獲取會話。"""
    return _sessions.get(session_id)


def _create_session_id() -> str:
    """創建唯一的會話 ID。"""
    return f"sess_{uuid4().hex[:12]}"


@router.get(
    "/health",
    response_model=schemas.HealthCheckResponse,
    summary="健康檢查",
    description="檢查 Code Interpreter 服務的健康狀態",
)
async def health_check() -> schemas.HealthCheckResponse:
    """
    檢查 Code Interpreter 服務狀態。

    Returns:
        HealthCheckResponse: 包含服務狀態信息
    """
    settings = get_settings()
    # Check Azure OpenAI configuration
    azure_configured = all([
        getattr(settings, 'azure_openai_endpoint', None),
        getattr(settings, 'azure_openai_api_key', None),
        getattr(settings, 'azure_openai_deployment_name', None),
    ])

    if azure_configured:
        return schemas.HealthCheckResponse(
            status="healthy",
            azure_openai_configured=True,
            message="Code Interpreter service is ready"
        )
    else:
        return schemas.HealthCheckResponse(
            status="degraded",
            azure_openai_configured=False,
            message="Azure OpenAI not configured. Set AZURE_OPENAI_* environment variables."
        )


@router.post(
    "/execute",
    response_model=schemas.CodeExecuteResponse,
    summary="執行 Python 代碼",
    description="使用 Azure OpenAI Code Interpreter 執行 Python 代碼",
)
async def execute_code(
    request: schemas.CodeExecuteRequest,
) -> schemas.CodeExecuteResponse:
    """
    執行 Python 代碼。

    Args:
        request: 包含要執行的代碼和配置

    Returns:
        CodeExecuteResponse: 執行結果

    Raises:
        HTTPException: 當執行失敗時
    """
    try:
        # Get or create adapter
        adapter = None
        if request.session_id:
            adapter = _get_session(request.session_id)
            if not adapter:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session not found: {request.session_id}"
                )

        # Create new adapter if no session
        if adapter is None:
            config = CodeInterpreterConfig(timeout=request.timeout or 60)
            adapter = CodeInterpreterAdapter(config=config)

        # Execute code
        logger.info(f"Executing code: {request.code[:100]}...")
        result = adapter.execute(
            code=request.code,
            timeout=request.timeout,
        )

        # Cleanup if no session was used
        if not request.session_id:
            adapter.cleanup()

        # Convert files to response format (handle None)
        files = []
        container_id = result.metadata.get("container_id") if result.metadata else None
        if result.files:
            files = [
                schemas.FileOutput(
                    type=f.get("type", "file"),
                    file_id=f.get("file_id", ""),
                    filename=f.get("filename"),
                    container_id=f.get("container_id") or container_id,
                )
                for f in result.files
            ]

        return schemas.CodeExecuteResponse(
            success=result.success,
            output=result.output,
            execution_time=result.execution_time,
            files=files,
            error=result.error,
            metadata=schemas.ExecutionMetadata(
                status=result.metadata.get("status", "unknown"),
                code_outputs=result.metadata.get("code_outputs", []),
                api_mode=result.metadata.get("api_mode"),
                response_id=result.metadata.get("response_id"),
                container_id=container_id,
            ) if result.metadata else None,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}"
        )


@router.post(
    "/analyze",
    response_model=schemas.TaskAnalyzeResponse,
    summary="分析任務",
    description="讓 AI 分析並執行任務，自動生成並執行代碼",
)
async def analyze_task(
    request: schemas.TaskAnalyzeRequest,
) -> schemas.TaskAnalyzeResponse:
    """
    分析並執行任務。

    Args:
        request: 包含任務描述和上下文

    Returns:
        TaskAnalyzeResponse: 分析結果

    Raises:
        HTTPException: 當分析失敗時
    """
    try:
        # Get or create adapter
        adapter = None
        if request.session_id:
            adapter = _get_session(request.session_id)
            if not adapter:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session not found: {request.session_id}"
                )

        # Create new adapter if no session
        if adapter is None:
            config = CodeInterpreterConfig(timeout=request.timeout or 60)
            adapter = CodeInterpreterAdapter(config=config)

        # Analyze task
        logger.info(f"Analyzing task: {request.task[:100]}...")
        result = adapter.analyze_task(
            task=request.task,
            context=request.context,
        )

        # Cleanup if no session was used
        if not request.session_id:
            adapter.cleanup()

        # Convert files to response format (handle None)
        files = []
        container_id = result.metadata.get("container_id") if result.metadata else None
        if result.files:
            files = [
                schemas.FileOutput(
                    type=f.get("type", "file"),
                    file_id=f.get("file_id", ""),
                    filename=f.get("filename"),
                    container_id=f.get("container_id") or container_id,
                )
                for f in result.files
            ]

        return schemas.TaskAnalyzeResponse(
            success=result.success,
            output=result.output,
            execution_time=result.execution_time,
            files=files,
            error=result.error,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post(
    "/sessions",
    response_model=schemas.SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="創建會話",
    description="創建一個新的 Code Interpreter 會話，可重複使用",
)
async def create_session(
    request: schemas.SessionCreateRequest,
) -> schemas.SessionCreateResponse:
    """
    創建新的會話。

    Args:
        request: 會話配置

    Returns:
        SessionCreateResponse: 包含會話信息

    Raises:
        HTTPException: 當創建失敗時
    """
    try:
        # Create session ID
        session_id = _create_session_id()

        # Create config
        config = CodeInterpreterConfig(
            assistant_name=request.name or "IPA-CodeInterpreter",
            instructions=request.instructions or CodeInterpreterConfig.instructions,
            timeout=request.timeout or 60,
            auto_cleanup=False,  # Don't auto-cleanup for sessions
        )

        # Create adapter
        adapter = CodeInterpreterAdapter(config=config)

        # Initialize the assistant (lazy init will be triggered on first use)
        # We don't initialize here to save resources

        # Store session
        _sessions[session_id] = adapter

        logger.info(f"Created session: {session_id}")

        return schemas.SessionCreateResponse(
            session=schemas.SessionInfo(
                session_id=session_id,
                assistant_id="pending",  # Will be set on first use
                name=request.name or "IPA-CodeInterpreter",
                created_at=datetime.utcnow(),
                is_active=True,
            ),
            message="Session created successfully",
        )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Session creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {str(e)}"
        )


@router.delete(
    "/sessions/{session_id}",
    response_model=schemas.SessionDeleteResponse,
    summary="刪除會話",
    description="刪除指定的 Code Interpreter 會話並釋放資源",
)
async def delete_session(session_id: str) -> schemas.SessionDeleteResponse:
    """
    刪除會話。

    Args:
        session_id: 會話 ID

    Returns:
        SessionDeleteResponse: 刪除結果

    Raises:
        HTTPException: 當會話不存在時
    """
    adapter = _sessions.pop(session_id, None)

    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )

    try:
        # Cleanup the adapter (delete Assistant from Azure)
        success = adapter.cleanup()

        logger.info(f"Deleted session: {session_id}")

        return schemas.SessionDeleteResponse(
            success=success,
            message=f"Session {session_id} deleted successfully" if success
                    else f"Session {session_id} deleted but cleanup may have failed"
        )

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}", exc_info=True)
        return schemas.SessionDeleteResponse(
            success=False,
            message=f"Session removed but cleanup failed: {str(e)}"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=schemas.SessionInfo,
    summary="獲取會話信息",
    description="獲取指定會話的詳細信息",
)
async def get_session(session_id: str) -> schemas.SessionInfo:
    """
    獲取會話信息。

    Args:
        session_id: 會話 ID

    Returns:
        SessionInfo: 會話詳細信息

    Raises:
        HTTPException: 當會話不存在時
    """
    adapter = _get_session(session_id)

    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )

    return schemas.SessionInfo(
        session_id=session_id,
        assistant_id=adapter.assistant_id or "pending",
        name=adapter.config.assistant_name,
        created_at=datetime.utcnow(),  # Would need actual tracking
        is_active=adapter.is_initialized or not adapter.is_initialized,
    )


# =============================================================================
# File Storage Endpoints (Sprint 38)
# =============================================================================

@router.post(
    "/files/upload",
    response_model=schemas.FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上傳文件",
    description="上傳文件到 Azure OpenAI，可用於 Code Interpreter 分析",
)
async def upload_file(
    file: UploadFile = File(..., description="要上傳的文件"),
    purpose: str = Query("assistants", description="文件用途 (assistants/fine-tune)"),
) -> schemas.FileUploadResponse:
    """
    上傳文件到 Azure OpenAI。

    支援的文件類型: .csv, .xlsx, .json, .txt, .py, .md, .pdf, .png, .jpg, etc.

    Args:
        file: 要上傳的文件
        purpose: 文件用途

    Returns:
        FileUploadResponse: 上傳結果

    Raises:
        HTTPException: 當上傳失敗時
    """
    try:
        file_service = get_file_service()

        # Read file content
        content = await file.read()

        # Upload to Azure OpenAI
        file_info = file_service.upload(
            file=io.BytesIO(content),
            filename=file.filename or "unnamed_file",
            purpose=purpose,
        )

        logger.info(f"Uploaded file: {file_info.filename} ({file_info.file_id})")

        return schemas.FileUploadResponse(
            file_id=file_info.file_id,
            filename=file_info.filename,
            bytes=file_info.bytes,
            purpose=file_info.purpose,
            created_at=file_info.created_at,
            message="File uploaded successfully",
        )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get(
    "/files",
    response_model=schemas.FileListResponse,
    summary="列出文件",
    description="列出所有已上傳的文件",
)
async def list_files(
    purpose: Optional[str] = Query(None, description="按用途過濾"),
) -> schemas.FileListResponse:
    """
    列出已上傳的文件。

    Args:
        purpose: 可選的用途過濾

    Returns:
        FileListResponse: 文件列表

    Raises:
        HTTPException: 當查詢失敗時
    """
    try:
        file_service = get_file_service()
        files = file_service.list_files(purpose=purpose)

        return schemas.FileListResponse(
            files=[
                schemas.StoredFileInfo(
                    file_id=f.file_id,
                    filename=f.filename,
                    bytes=f.bytes,
                    purpose=f.purpose,
                    created_at=f.created_at,
                )
                for f in files
            ],
            total=len(files),
        )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"List files failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"List files failed: {str(e)}"
        )


@router.get(
    "/files/{file_id}",
    summary="下載文件",
    description="下載指定的文件內容",
)
async def download_file(file_id: str) -> StreamingResponse:
    """
    下載文件。

    Args:
        file_id: 文件 ID

    Returns:
        StreamingResponse: 文件內容

    Raises:
        HTTPException: 當下載失敗時
    """
    try:
        file_service = get_file_service()

        # Get file content
        content = file_service.download(file_id)

        # Determine content type (simplified)
        content_type = "application/octet-stream"

        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_id}"
            }
        )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "no such file" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        logger.error(f"File download failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File download failed: {str(e)}"
        )


@router.delete(
    "/files/{file_id}",
    response_model=schemas.FileDeleteResponse,
    summary="刪除文件",
    description="從 Azure OpenAI 刪除文件",
)
async def delete_file(file_id: str) -> schemas.FileDeleteResponse:
    """
    刪除文件。

    Args:
        file_id: 文件 ID

    Returns:
        FileDeleteResponse: 刪除結果

    Raises:
        HTTPException: 當刪除失敗時
    """
    try:
        file_service = get_file_service()
        success = file_service.delete(file_id)

        if success:
            logger.info(f"Deleted file: {file_id}")
            return schemas.FileDeleteResponse(
                success=True,
                file_id=file_id,
                message="File deleted successfully",
            )
        else:
            return schemas.FileDeleteResponse(
                success=False,
                file_id=file_id,
                message="File deletion may have failed",
            )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "no such file" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        logger.error(f"File deletion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File deletion failed: {str(e)}"
        )


# =============================================================================
# Code Interpreter Sandbox File Download (Sprint 38)
# =============================================================================

@router.get(
    "/sandbox/containers/{container_id}/files/{file_id}",
    summary="下載沙盒生成的檔案",
    description="從 Code Interpreter 沙盒下載生成的檔案（如圖表、報告等）",
)
async def download_sandbox_file(
    container_id: str,
    file_id: str,
    session_id: Optional[str] = Query(None, description="可選的會話 ID"),
) -> StreamingResponse:
    """
    下載 Code Interpreter 沙盒中生成的檔案。

    使用 Azure OpenAI Container Files API 端點:
    {AOAI_ENDPOINT}/openai/v1/containers/{container_id}/files/{file_id}/content

    Args:
        container_id: 容器 ID (從執行結果的 metadata.container_id 獲取)
        file_id: 檔案 ID (從執行結果的 files[].file_id 獲取)
        session_id: 可選的會話 ID

    Returns:
        StreamingResponse: 檔案內容

    Raises:
        HTTPException: 當下載失敗時
    """
    try:
        # Get or create adapter
        adapter = None
        if session_id:
            adapter = _get_session(session_id)

        # Create new adapter if no session
        if adapter is None:
            config = CodeInterpreterConfig(timeout=60)
            adapter = CodeInterpreterAdapter(config=config)

        # Download file from sandbox
        logger.info(f"Downloading sandbox file: container={container_id}, file={file_id}")
        content = adapter.download_file(container_id, file_id)

        # Determine content type based on file extension or default to binary
        content_type = "application/octet-stream"
        filename = file_id

        # Try to infer content type from common patterns
        if "png" in file_id.lower() or file_id.endswith(".png"):
            content_type = "image/png"
            if not filename.endswith(".png"):
                filename = f"{file_id}.png"
        elif "jpg" in file_id.lower() or "jpeg" in file_id.lower():
            content_type = "image/jpeg"
        elif "csv" in file_id.lower():
            content_type = "text/csv"
        elif "json" in file_id.lower():
            content_type = "application/json"
        elif "pdf" in file_id.lower():
            content_type = "application/pdf"

        # Cleanup if no session was used
        if not session_id:
            adapter.cleanup()

        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(content)),
            }
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "404" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: container_id={container_id}, file_id={file_id}"
            )
        logger.error(f"Sandbox file download failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox file download failed: {str(e)}"
        )
