"""Claude SDK Hooks API routes.

Sprint 51: S51-2 Hooks API Routes (5 pts)
Provides REST API endpoints for hook management.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.claude_sdk.hooks import (
    Hook,
    HookChain,
    ApprovalHook,
    AuditHook,
    RateLimitHook,
    SandboxHook,
)


# --- Enums ---


class HookType(str, Enum):
    """Available hook types."""

    APPROVAL = "approval"
    AUDIT = "audit"
    RATE_LIMIT = "rate_limit"
    SANDBOX = "sandbox"
    CUSTOM = "custom"


class HookPriority(str, Enum):
    """Hook priority levels."""

    LOW = "low"  # 25
    NORMAL = "normal"  # 50
    HIGH = "high"  # 75
    CRITICAL = "critical"  # 100


# --- Schemas ---


class HookConfig(BaseModel):
    """Configuration for hook creation."""

    # Approval hook config
    tools: Optional[List[str]] = Field(None, description="Tools requiring approval")

    # Audit hook config
    redact_patterns: Optional[List[str]] = Field(None, description="Patterns to redact")

    # Rate limit hook config
    max_calls_per_minute: Optional[int] = Field(None, description="Max calls per minute")
    max_concurrent: Optional[int] = Field(None, description="Max concurrent operations")

    # Sandbox hook config
    allowed_paths: Optional[List[str]] = Field(None, description="Allowed file paths")
    strict_mode: Optional[bool] = Field(False, description="Use strict sandbox mode")


class HookInfo(BaseModel):
    """Schema for hook information."""

    id: str = Field(..., description="Hook ID")
    name: str = Field(..., description="Hook name")
    type: HookType = Field(..., description="Hook type")
    priority: int = Field(..., description="Hook priority (0-100)")
    enabled: bool = Field(True, description="Whether hook is enabled")
    config: Optional[HookConfig] = Field(None, description="Hook configuration")


class HookListResponse(BaseModel):
    """Response schema for listing hooks."""

    hooks: List[HookInfo]
    total: int


class HookRegisterRequest(BaseModel):
    """Request schema for registering a hook."""

    type: HookType = Field(..., description="Type of hook to register")
    name: Optional[str] = Field(None, description="Custom hook name")
    priority: HookPriority = Field(HookPriority.NORMAL, description="Hook priority")
    config: Optional[HookConfig] = Field(None, description="Hook configuration")


class HookRegisterResponse(BaseModel):
    """Response schema for hook registration."""

    id: str
    name: str
    type: HookType
    priority: int
    status: str = "registered"


# --- Global Hook Manager ---


class HookManager:
    """Manages hook registration and lifecycle."""

    def __init__(self):
        self._hooks: Dict[str, HookInfo] = {}
        self._hook_instances: Dict[str, Hook] = {}
        self._chain = HookChain()

    def list_hooks(
        self,
        hook_type: Optional[HookType] = None,
        enabled_only: bool = False,
    ) -> List[HookInfo]:
        """List all registered hooks."""
        hooks = list(self._hooks.values())

        if hook_type:
            hooks = [h for h in hooks if h.type == hook_type]

        if enabled_only:
            hooks = [h for h in hooks if h.enabled]

        return sorted(hooks, key=lambda h: h.priority, reverse=True)

    def get_hook(self, hook_id: str) -> Optional[HookInfo]:
        """Get hook by ID."""
        return self._hooks.get(hook_id)

    def register_hook(
        self,
        hook_type: HookType,
        name: Optional[str] = None,
        priority: HookPriority = HookPriority.NORMAL,
        config: Optional[HookConfig] = None,
    ) -> HookInfo:
        """Register a new hook."""
        hook_id = str(uuid4())
        priority_value = _priority_to_int(priority)

        # Create hook instance based on type
        hook_instance = _create_hook_instance(hook_type, priority_value, config)
        hook_name = name or f"{hook_type.value}_{hook_id[:8]}"
        hook_instance.name = hook_name

        # Store hook info
        hook_info = HookInfo(
            id=hook_id,
            name=hook_name,
            type=hook_type,
            priority=priority_value,
            enabled=True,
            config=config,
        )

        self._hooks[hook_id] = hook_info
        self._hook_instances[hook_id] = hook_instance
        self._chain.add(hook_instance)

        return hook_info

    def remove_hook(self, hook_id: str) -> bool:
        """Remove a hook."""
        if hook_id not in self._hooks:
            return False

        hook_instance = self._hook_instances.get(hook_id)
        if hook_instance:
            self._chain.remove(hook_instance)
            del self._hook_instances[hook_id]

        del self._hooks[hook_id]
        return True

    def enable_hook(self, hook_id: str) -> Optional[HookInfo]:
        """Enable a hook."""
        if hook_id not in self._hooks:
            return None

        self._hooks[hook_id].enabled = True
        if hook_id in self._hook_instances:
            self._hook_instances[hook_id].enabled = True

        return self._hooks[hook_id]

    def disable_hook(self, hook_id: str) -> Optional[HookInfo]:
        """Disable a hook."""
        if hook_id not in self._hooks:
            return None

        self._hooks[hook_id].enabled = False
        if hook_id in self._hook_instances:
            self._hook_instances[hook_id].enabled = False

        return self._hooks[hook_id]

    @property
    def chain(self) -> HookChain:
        """Get the hook chain for execution."""
        return self._chain


# Global hook manager instance
_hook_manager = HookManager()


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance."""
    return _hook_manager


# --- Router ---


router = APIRouter(prefix="/hooks", tags=["Claude SDK Hooks"])


# --- Endpoints ---


@router.get("", response_model=HookListResponse)
async def list_hooks(
    type: Optional[HookType] = None,
    enabled_only: bool = False,
):
    """
    List all registered hooks.

    Returns a list of all hooks with their configuration.
    Optionally filter by type or enabled status.
    """
    manager = get_hook_manager()
    hooks = manager.list_hooks(hook_type=type, enabled_only=enabled_only)
    return HookListResponse(hooks=hooks, total=len(hooks))


@router.get("/{hook_id}", response_model=HookInfo)
async def get_hook(hook_id: str):
    """
    Get detailed information about a specific hook.

    Returns hook metadata, configuration, and status.
    """
    manager = get_hook_manager()
    hook = manager.get_hook(hook_id)

    if hook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hook '{hook_id}' not found",
        )

    return hook


@router.post("/register", response_model=HookRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_hook(request: HookRegisterRequest):
    """
    Register a new hook.

    Creates a hook of the specified type with the given configuration.
    Returns the hook ID for future operations.
    """
    manager = get_hook_manager()
    hook_info = manager.register_hook(
        hook_type=request.type,
        name=request.name,
        priority=request.priority,
        config=request.config,
    )

    return HookRegisterResponse(
        id=hook_info.id,
        name=hook_info.name,
        type=hook_info.type,
        priority=hook_info.priority,
    )


@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_hook(hook_id: str):
    """
    Remove a registered hook.

    Removes the hook from the chain and cleans up resources.
    """
    manager = get_hook_manager()
    success = manager.remove_hook(hook_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hook '{hook_id}' not found",
        )


@router.put("/{hook_id}/enable", response_model=HookInfo)
async def enable_hook(hook_id: str):
    """
    Enable a disabled hook.

    Re-activates the hook for execution in the chain.
    """
    manager = get_hook_manager()
    hook = manager.enable_hook(hook_id)

    if hook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hook '{hook_id}' not found",
        )

    return hook


@router.put("/{hook_id}/disable", response_model=HookInfo)
async def disable_hook(hook_id: str):
    """
    Disable an active hook.

    Temporarily disables the hook without removing it.
    """
    manager = get_hook_manager()
    hook = manager.disable_hook(hook_id)

    if hook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hook '{hook_id}' not found",
        )

    return hook


# --- Helper Functions ---


def _priority_to_int(priority: HookPriority) -> int:
    """Convert priority enum to integer value."""
    mapping = {
        HookPriority.LOW: 25,
        HookPriority.NORMAL: 50,
        HookPriority.HIGH: 75,
        HookPriority.CRITICAL: 100,
    }
    return mapping.get(priority, 50)


def _create_hook_instance(
    hook_type: HookType,
    priority: int,
    config: Optional[HookConfig],
) -> Hook:
    """Create a hook instance based on type and configuration."""
    if hook_type == HookType.APPROVAL:
        approval_tools = config.tools if config else None
        hook = ApprovalHook(approval_tools=approval_tools)
        hook.priority = priority
        return hook

    elif hook_type == HookType.AUDIT:
        redact_patterns = config.redact_patterns if config else None
        hook = AuditHook(redact_patterns=redact_patterns)
        hook.priority = priority
        return hook

    elif hook_type == HookType.RATE_LIMIT:
        from src.integrations.claude_sdk.hooks.rate_limit import RateLimitConfig

        rate_config = RateLimitConfig(
            max_calls_per_minute=config.max_calls_per_minute or 60,
            max_concurrent=config.max_concurrent or 5,
        ) if config else RateLimitConfig()

        hook = RateLimitHook(config=rate_config)
        hook.priority = priority
        return hook

    elif hook_type == HookType.SANDBOX:
        allowed_paths = config.allowed_paths if config else None
        strict_mode = config.strict_mode if config else False

        if strict_mode:
            from src.integrations.claude_sdk.hooks.sandbox import StrictSandboxHook
            hook = StrictSandboxHook(allowed_paths=allowed_paths)
        else:
            hook = SandboxHook(allowed_paths=allowed_paths)

        hook.priority = priority
        return hook

    else:
        # Custom hook - create base hook
        class CustomHook(Hook):
            pass

        hook = CustomHook()
        hook.priority = priority
        return hook
