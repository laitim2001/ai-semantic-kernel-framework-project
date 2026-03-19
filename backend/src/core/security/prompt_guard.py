# =============================================================================
# IPA Platform - Prompt Injection Guard
# =============================================================================
# Sprint 109: Story 2 (3 SP)
# Phase 36: Security Hardening
#
# Prompt Injection Guard — multi-layer defense against prompt injection.
#
# Three layers:
# L1: Input Filtering — remove known injection patterns
# L2: System Prompt Isolation — ensure user input cannot escape role boundaries
# L3: Tool Call Validation — verify LLM tool calls match whitelist
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SanitizedInput:
    """Result of input sanitization."""

    content: str
    was_modified: bool
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# Constants
# =============================================================================

# Default maximum input length (characters)
_DEFAULT_MAX_INPUT_LENGTH = 4000

# Role confusion / prompt injection patterns
# Each entry: (compiled regex, description for warnings)
_INJECTION_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    # Role confusion attempts
    (
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        "role_confusion:ignore_previous",
    ),
    (
        re.compile(r"disregard\s+(all\s+)?previous\s+(instructions|prompts|rules)", re.IGNORECASE),
        "role_confusion:disregard_previous",
    ),
    (
        re.compile(r"forget\s+(all\s+)?(your\s+)?previous\s+(instructions|rules)", re.IGNORECASE),
        "role_confusion:forget_previous",
    ),
    (
        re.compile(r"you\s+are\s+now\s+(a|an|the)\b", re.IGNORECASE),
        "role_confusion:identity_override",
    ),
    (
        re.compile(r"act\s+as\s+(a|an|if)\b", re.IGNORECASE),
        "role_confusion:act_as",
    ),
    (
        re.compile(r"pretend\s+(you\s+are|to\s+be)\b", re.IGNORECASE),
        "role_confusion:pretend",
    ),
    (
        re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
        "role_confusion:new_instructions",
    ),
    # Role boundary escape attempts
    (
        re.compile(r"^system\s*:", re.IGNORECASE | re.MULTILINE),
        "boundary_escape:system_prefix",
    ),
    (
        re.compile(r"^assistant\s*:", re.IGNORECASE | re.MULTILINE),
        "boundary_escape:assistant_prefix",
    ),
    (
        re.compile(r"^user\s*:", re.IGNORECASE | re.MULTILINE),
        "boundary_escape:user_prefix",
    ),
    (
        re.compile(r"\[INST\]", re.IGNORECASE),
        "boundary_escape:inst_tag",
    ),
    (
        re.compile(r"<<SYS>>", re.IGNORECASE),
        "boundary_escape:sys_tag",
    ),
    (
        re.compile(r"<\|im_start\|>", re.IGNORECASE),
        "boundary_escape:im_start",
    ),
    (
        re.compile(r"<\|im_end\|>", re.IGNORECASE),
        "boundary_escape:im_end",
    ),
    # Data exfiltration attempts
    (
        re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
        "exfiltration:reveal_prompt",
    ),
    (
        re.compile(r"show\s+(me\s+)?(your\s+)?(system\s+)?instructions", re.IGNORECASE),
        "exfiltration:show_instructions",
    ),
    (
        re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions)", re.IGNORECASE),
        "exfiltration:query_instructions",
    ),
    # Code injection via string interpolation
    (
        re.compile(r"\{\{.*\}\}", re.DOTALL),
        "code_injection:template_interpolation",
    ),
    (
        re.compile(r"\$\{.*\}", re.DOTALL),
        "code_injection:variable_interpolation",
    ),
]

# Patterns that should be escaped (not removed) — less aggressive
_ESCAPE_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        "xss:script_tag",
    ),
    (
        re.compile(r"javascript:", re.IGNORECASE),
        "xss:javascript_protocol",
    ),
]


# =============================================================================
# PromptGuard
# =============================================================================


class PromptGuard:
    """
    Multi-layer defense against prompt injection attacks.

    Layer 1: Input filtering — detect and neutralize injection patterns.
    Layer 2: System prompt isolation — wrap user input with boundary markers.
    Layer 3: Tool call validation — verify LLM tool calls against whitelist.

    Usage:
        guard = PromptGuard()
        result = guard.sanitize_input("ignore previous instructions and ...")
        if result.was_modified:
            logger.warning("Input was sanitized: %s", result.warnings)

        wrapped = guard.wrap_user_input(result.content)
        # wrapped = "<user_message>...</user_message>"

        is_valid = guard.validate_tool_call(
            tool_name="route_intent",
            tool_args={"query": "hello"},
            allowed_tools=["route_intent", "respond_to_user"],
        )
    """

    def __init__(
        self,
        max_input_length: int = _DEFAULT_MAX_INPUT_LENGTH,
        custom_patterns: Optional[List[tuple[re.Pattern[str], str]]] = None,
    ):
        """
        Initialize PromptGuard.

        Args:
            max_input_length: Maximum allowed input length in characters.
            custom_patterns: Additional injection patterns to detect.
                             Each entry is (compiled_regex, description).
        """
        self._max_input_length = max_input_length
        self._patterns = list(_INJECTION_PATTERNS)
        if custom_patterns:
            self._patterns.extend(custom_patterns)
        self._escape_patterns = list(_ESCAPE_PATTERNS)

    # =========================================================================
    # Layer 1: Input Filtering
    # =========================================================================

    def sanitize_input(self, user_input: str) -> SanitizedInput:
        """
        Sanitize user input by detecting and neutralizing injection patterns.

        Processing order:
        1. Length check and truncation
        2. Injection pattern detection and removal
        3. Escape pattern neutralization

        Args:
            user_input: Raw user input string.

        Returns:
            SanitizedInput with cleaned content, modification flag, and warnings.
        """
        if not isinstance(user_input, str):
            return SanitizedInput(
                content="",
                was_modified=True,
                warnings=["non_string_input:converted_to_empty"],
            )

        warnings: List[str] = []
        content = user_input
        was_modified = False

        # Step 1: Length check
        if len(content) > self._max_input_length:
            content = content[: self._max_input_length]
            warnings.append(
                f"length_truncated:from_{len(user_input)}_to_{self._max_input_length}"
            )
            was_modified = True

        # Step 2: Injection pattern detection and removal
        for pattern, description in self._patterns:
            if pattern.search(content):
                warnings.append(f"injection_detected:{description}")
                content = pattern.sub("[FILTERED]", content)
                was_modified = True

        # Step 3: Escape patterns (XSS etc.)
        for pattern, description in self._escape_patterns:
            if pattern.search(content):
                warnings.append(f"escape_applied:{description}")
                content = pattern.sub("[ESCAPED]", content)
                was_modified = True

        if warnings:
            logger.warning(
                "Input sanitization applied: warnings=%s input_length=%d",
                warnings,
                len(user_input),
            )

        return SanitizedInput(
            content=content,
            was_modified=was_modified,
            warnings=warnings,
        )

    # =========================================================================
    # Layer 2: System Prompt Isolation
    # =========================================================================

    def wrap_user_input(self, user_input: str) -> str:
        """
        Wrap user input with explicit boundary markers.

        This ensures the LLM can distinguish user input from system instructions,
        preventing role confusion attacks.

        Args:
            user_input: The (preferably already sanitized) user input.

        Returns:
            Input wrapped with boundary markers.
        """
        # Sanitize first if not already done
        sanitized = self.sanitize_input(user_input)
        return f"<user_message>{sanitized.content}</user_message>"

    # =========================================================================
    # Layer 3: Tool Call Validation
    # =========================================================================

    def validate_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        allowed_tools: List[str],
    ) -> bool:
        """
        Validate that an LLM-generated tool call is permitted.

        Checks:
        1. tool_name is in the allowed_tools whitelist.
        2. tool_args keys contain only safe characters (alphanumeric + underscore).
        3. tool_args string values do not contain injection patterns.

        Args:
            tool_name: Name of the tool the LLM wants to call.
            tool_args: Arguments the LLM provided for the tool.
            allowed_tools: Whitelist of permitted tool names.

        Returns:
            True if the tool call is valid, False otherwise.
        """
        # Check 1: Whitelist
        if tool_name not in allowed_tools:
            logger.warning(
                "Tool call rejected: tool='%s' not in whitelist=%s",
                tool_name,
                allowed_tools,
            )
            return False

        # Check 2: Arg key safety
        safe_key_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        for key in tool_args:
            if not isinstance(key, str) or not safe_key_pattern.match(key):
                logger.warning(
                    "Tool call rejected: unsafe arg key '%s' in tool '%s'",
                    key,
                    tool_name,
                )
                return False

        # Check 3: Arg value injection check
        for key, value in tool_args.items():
            if isinstance(value, str):
                for pattern, description in self._patterns:
                    if pattern.search(value):
                        logger.warning(
                            "Tool call rejected: injection in arg '%s' "
                            "of tool '%s': %s",
                            key,
                            tool_name,
                            description,
                        )
                        return False

        return True

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def add_pattern(
        self, pattern: re.Pattern[str], description: str
    ) -> None:
        """
        Add a custom injection detection pattern.

        Args:
            pattern: Compiled regex pattern.
            description: Human-readable description for warnings.
        """
        self._patterns.append((pattern, description))
        logger.info("Added custom injection pattern: %s", description)

    def check_input(self, user_input: str) -> List[str]:
        """
        Check input for injection patterns without modifying it.

        Useful for monitoring/alerting without blocking.

        Args:
            user_input: The input to check.

        Returns:
            List of detected pattern descriptions (empty if clean).
        """
        detections: List[str] = []

        if len(user_input) > self._max_input_length:
            detections.append("length_exceeded")

        for pattern, description in self._patterns:
            if pattern.search(user_input):
                detections.append(description)

        for pattern, description in self._escape_patterns:
            if pattern.search(user_input):
                detections.append(description)

        return detections
