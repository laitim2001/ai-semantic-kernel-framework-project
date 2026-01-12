# =============================================================================
# IPA Platform - Memory API Routes
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# FastAPI routes for memory operations.
#
# Endpoints:
#   POST   /api/v1/memory/add           - Add new memory
#   POST   /api/v1/memory/search        - Search memories
#   GET    /api/v1/memory/user/{id}     - Get user memories
#   GET    /api/v1/memory/{id}          - Get memory by ID
#   DELETE /api/v1/memory/{id}          - Delete memory
#   POST   /api/v1/memory/promote       - Promote memory to higher layer
#   POST   /api/v1/memory/context       - Get context memories
#   GET    /api/v1/memory/health        - Health check
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.integrations.memory import (
    UnifiedMemoryManager,
    MemoryLayer,
    MemoryMetadata,
    MemoryType,
)

from .schemas import (
    AddMemoryRequest,
    AddMemoryResponse,
    ContextRequest,
    DeleteMemoryResponse,
    MemoryHealthResponse,
    MemoryListResponse,
    MemoryMetadataSchema,
    MemoryResponse,
    MemorySearchResultSchema,
    PromoteMemoryRequest,
    SearchMemoryRequest,
    SearchMemoryResponse,
)


router = APIRouter(prefix="/memory", tags=["Memory"])


# --- Memory Manager Instance ---

_memory_manager: Optional[UnifiedMemoryManager] = None


async def get_memory_manager() -> UnifiedMemoryManager:
    """Get or create the memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = UnifiedMemoryManager()
        await _memory_manager.initialize()
    return _memory_manager


def _memory_type_from_str(type_str: str) -> MemoryType:
    """Convert string to MemoryType enum."""
    try:
        return MemoryType(type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory type: {type_str}. "
            f"Valid types: {[t.value for t in MemoryType]}",
        )


def _memory_layer_from_str(layer_str: str) -> MemoryLayer:
    """Convert string to MemoryLayer enum."""
    try:
        return MemoryLayer(layer_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory layer: {layer_str}. "
            f"Valid layers: {[l.value for l in MemoryLayer]}",
        )


def _metadata_schema_to_obj(schema: Optional[MemoryMetadataSchema]) -> Optional[MemoryMetadata]:
    """Convert schema to MemoryMetadata object."""
    if schema is None:
        return None
    return MemoryMetadata(
        source=schema.source,
        event_id=schema.event_id,
        session_id=schema.session_id,
        confidence=schema.confidence,
        importance=schema.importance,
        tags=schema.tags,
        custom=schema.custom,
    )


def _metadata_obj_to_schema(obj: MemoryMetadata) -> MemoryMetadataSchema:
    """Convert MemoryMetadata object to schema."""
    return MemoryMetadataSchema(
        source=obj.source,
        event_id=obj.event_id,
        session_id=obj.session_id,
        confidence=obj.confidence,
        importance=obj.importance,
        tags=obj.tags,
        custom=obj.custom,
    )


# --- Endpoints ---


@router.post("/add", response_model=AddMemoryResponse, status_code=status.HTTP_201_CREATED)
async def add_memory(
    request: AddMemoryRequest,
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Add a new memory.

    The memory will be stored in the appropriate layer based on type and importance,
    or in the explicitly specified layer.
    """
    try:
        memory_type = _memory_type_from_str(request.memory_type)
        layer = _memory_layer_from_str(request.layer) if request.layer else None
        metadata = _metadata_schema_to_obj(request.metadata)

        record = await manager.add(
            content=request.content,
            user_id=request.user_id,
            memory_type=memory_type,
            metadata=metadata,
            layer=layer,
        )

        return AddMemoryResponse(
            id=record.id,
            user_id=record.user_id,
            content=record.content,
            memory_type=record.memory_type.value,
            layer=record.layer.value,
            created_at=record.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add memory: {str(e)}",
        )


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memory(
    request: SearchMemoryRequest,
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Search memories using semantic similarity.

    Returns memories ranked by relevance score.
    """
    try:
        memory_types = None
        if request.memory_types:
            memory_types = [_memory_type_from_str(t) for t in request.memory_types]

        layers = None
        if request.layers:
            layers = [_memory_layer_from_str(l) for l in request.layers]

        results = await manager.search(
            query=request.query,
            user_id=request.user_id or "",
            memory_types=memory_types,
            layers=layers,
            min_importance=request.min_importance,
            limit=request.limit,
        )

        search_results = [
            MemorySearchResultSchema(
                id=r.memory.id,
                content=r.memory.content,
                memory_type=r.memory.memory_type.value,
                layer=r.memory.layer.value,
                score=r.score,
                metadata=_metadata_obj_to_schema(r.memory.metadata),
                created_at=r.memory.created_at,
            )
            for r in results
        ]

        return SearchMemoryResponse(
            results=search_results,
            total=len(search_results),
            query=request.query,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}",
        )


@router.get("/user/{user_id}", response_model=MemoryListResponse)
async def get_user_memories(
    user_id: str,
    memory_types: Optional[str] = Query(None, description="Comma-separated memory types"),
    layers: Optional[str] = Query(None, description="Comma-separated layers"),
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Get all memories for a user.

    Optionally filter by memory types and layers.
    """
    try:
        type_list = None
        if memory_types:
            type_list = [_memory_type_from_str(t.strip()) for t in memory_types.split(",")]

        layer_list = None
        if layers:
            layer_list = [_memory_layer_from_str(l.strip()) for l in layers.split(",")]

        records = await manager.get_user_memories(
            user_id=user_id,
            memory_types=type_list,
            layers=layer_list,
        )

        memories = [
            MemoryResponse(
                id=r.id,
                user_id=r.user_id,
                content=r.content,
                memory_type=r.memory_type.value,
                layer=r.layer.value,
                metadata=_metadata_obj_to_schema(r.metadata),
                created_at=r.created_at,
                updated_at=r.updated_at,
                accessed_at=r.accessed_at,
                access_count=r.access_count,
            )
            for r in records
        ]

        return MemoryListResponse(
            memories=memories,
            total=len(memories),
            user_id=user_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user memories: {str(e)}",
        )


@router.delete("/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory(
    memory_id: str,
    user_id: str = Query(..., description="User ID"),
    layer: Optional[str] = Query(None, description="Specific layer to delete from"),
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Delete a memory.

    If layer is not specified, attempts to delete from all layers.
    """
    try:
        target_layer = _memory_layer_from_str(layer) if layer else None

        success = await manager.delete(
            memory_id=memory_id,
            user_id=user_id,
            layer=target_layer,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found",
            )

        return DeleteMemoryResponse(
            success=True,
            memory_id=memory_id,
            message="Memory deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}",
        )


@router.post("/promote", response_model=MemoryResponse)
async def promote_memory(
    request: PromoteMemoryRequest,
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Promote a memory to a higher layer.

    Typically used to move important memories from working/session to long-term.
    """
    try:
        from_layer = _memory_layer_from_str(request.from_layer)
        to_layer = _memory_layer_from_str(request.to_layer)

        record = await manager.promote(
            memory_id=request.memory_id,
            user_id=request.user_id,
            from_layer=from_layer,
            to_layer=to_layer,
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {request.memory_id} not found in {request.from_layer}",
            )

        return MemoryResponse(
            id=record.id,
            user_id=record.user_id,
            content=record.content,
            memory_type=record.memory_type.value,
            layer=record.layer.value,
            metadata=_metadata_obj_to_schema(record.metadata),
            created_at=record.created_at,
            updated_at=record.updated_at,
            accessed_at=record.accessed_at,
            access_count=record.access_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote memory: {str(e)}",
        )


@router.post("/context", response_model=MemoryListResponse)
async def get_context_memories(
    request: ContextRequest,
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Get relevant memories for the current context.

    Combines recent working memories with semantically relevant long-term memories.
    """
    try:
        records = await manager.get_context(
            user_id=request.user_id,
            session_id=request.session_id,
            query=request.query,
            limit=request.limit,
        )

        memories = [
            MemoryResponse(
                id=r.id,
                user_id=r.user_id,
                content=r.content,
                memory_type=r.memory_type.value,
                layer=r.layer.value,
                metadata=_metadata_obj_to_schema(r.metadata),
                created_at=r.created_at,
                updated_at=r.updated_at,
                accessed_at=r.accessed_at,
                access_count=r.access_count,
            )
            for r in records
        ]

        return MemoryListResponse(
            memories=memories,
            total=len(memories),
            user_id=request.user_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context memories: {str(e)}",
        )


@router.get("/health", response_model=MemoryHealthResponse)
async def health_check(
    manager: UnifiedMemoryManager = Depends(get_memory_manager),
):
    """
    Check the health of the memory system.

    Returns status of all components: mem0, Redis, embedding service.
    """
    try:
        # Check mem0 client
        mem0_ok = manager._mem0_client._initialized

        # Check Redis
        redis_ok = False
        if manager._redis:
            try:
                await manager._redis.ping()
                redis_ok = True
            except Exception:
                pass

        # Check embedding service
        embedding_ok = manager._embedding_service._initialized

        # Overall status
        all_ok = mem0_ok and embedding_ok

        return MemoryHealthResponse(
            status="healthy" if all_ok else "degraded",
            mem0_initialized=mem0_ok,
            redis_connected=redis_ok,
            embedding_service=embedding_ok,
            details={
                "qdrant_path": manager.config.qdrant_path,
                "embedding_model": manager.config.embedding_model,
                "working_memory_enabled": redis_ok,
            },
        )

    except Exception as e:
        return MemoryHealthResponse(
            status="unhealthy",
            mem0_initialized=False,
            redis_connected=False,
            embedding_service=False,
            details={"error": str(e)},
        )
