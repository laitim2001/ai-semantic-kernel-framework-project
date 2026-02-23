"""
Active Directory Operations for LDAP MCP Server.

Sprint 114: AD 場景基礎建設 (Phase 32)
Provides high-level AD account management operations built on LDAPClient.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .ad_config import ADConfig
from .client import LDAPClient, LDAPConnectionManager, LDAPSearchResult

logger = logging.getLogger(__name__)


@dataclass
class ADOperationResult:
    """Result of an AD operation.

    Attributes:
        success: Whether the operation succeeded
        operation: Name of the operation performed
        target_dn: Distinguished name of the target entry
        message: Human-readable result message
        details: Additional operation details
        timestamp: When the operation was performed
    """

    success: bool
    operation: str
    target_dn: str = ""
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = {}
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class ADOperations:
    """High-level Active Directory operations.

    Provides account management operations:
    - Account lookup by sAMAccountName
    - Account unlock (clear lockoutTime)
    - Password reset (modify unicodePwd)
    - Group membership queries
    - Group membership modifications
    - Account creation
    - Account disable/enable

    Requires an ADConfig with appropriate allowed_operations.
    """

    def __init__(
        self,
        connection_manager: LDAPConnectionManager,
        config: ADConfig,
    ) -> None:
        """Initialize AD operations.

        Args:
            connection_manager: LDAP connection manager for pooled access
            config: Active Directory configuration
        """
        self._conn_manager = connection_manager
        self._config = config

    async def _get_client(self) -> LDAPClient:
        """Get a connected LDAP client from the pool.

        Returns:
            Connected LDAPClient instance
        """
        return await self._conn_manager.get_connection()

    async def find_user(
        self,
        sam_account_name: str,
        attributes: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find a user by sAMAccountName.

        Args:
            sam_account_name: The user's sAMAccountName (login name)
            attributes: Attributes to return (default: config user_attributes)

        Returns:
            User entry dictionary or None if not found
        """
        client = await self._get_client()
        search_filter = (
            f"(&(objectClass={self._config.user_object_class})"
            f"(sAMAccountName={sam_account_name}))"
        )
        result = await client.search(
            search_filter=search_filter,
            search_base=self._config.user_search_base or self._config.base_dn,
            attributes=attributes or self._config.user_attributes,
            size_limit=1,
        )

        if result.entries:
            logger.info(f"Found user: {sam_account_name}")
            return result.entries[0]

        logger.warning(f"User not found: {sam_account_name}")
        return None

    async def unlock_account(
        self,
        sam_account_name: str,
    ) -> ADOperationResult:
        """Unlock a locked AD account.

        Clears the lockoutTime attribute to unlock the account.

        Args:
            sam_account_name: The user's sAMAccountName

        Returns:
            ADOperationResult indicating success or failure
        """
        user = await self.find_user(sam_account_name, ["dn", "lockoutTime"])
        if not user:
            return ADOperationResult(
                success=False,
                operation="unlock_account",
                message=f"User not found: {sam_account_name}",
            )

        user_dn = user["dn"]
        client = await self._get_client()

        try:
            success = await client.modify_entry(
                dn=user_dn,
                changes={"lockoutTime": ("replace", ["0"])},
            )

            if success:
                logger.info(f"Account unlocked: {sam_account_name} ({user_dn})")
                return ADOperationResult(
                    success=True,
                    operation="unlock_account",
                    target_dn=user_dn,
                    message=f"Account unlocked successfully: {sam_account_name}",
                )
            else:
                logger.warning(f"Failed to unlock account: {sam_account_name}")
                return ADOperationResult(
                    success=False,
                    operation="unlock_account",
                    target_dn=user_dn,
                    message=f"LDAP modify failed for: {sam_account_name}",
                )

        except PermissionError as e:
            logger.error(f"Permission denied for unlock: {e}")
            return ADOperationResult(
                success=False,
                operation="unlock_account",
                target_dn=user_dn,
                message=f"Permission denied: {e}",
            )
        except Exception as e:
            logger.error(f"Unlock failed: {e}", exc_info=True)
            return ADOperationResult(
                success=False,
                operation="unlock_account",
                target_dn=user_dn,
                message=f"Operation failed: {e}",
            )

    async def reset_password(
        self,
        sam_account_name: str,
        new_password: str,
    ) -> ADOperationResult:
        """Reset a user's AD password.

        Sets the unicodePwd attribute. Requires SSL/TLS connection.

        Args:
            sam_account_name: The user's sAMAccountName
            new_password: The new password to set

        Returns:
            ADOperationResult indicating success or failure
        """
        if not self._config.use_ssl and not self._config.use_tls:
            return ADOperationResult(
                success=False,
                operation="reset_password",
                message="Password reset requires SSL/TLS connection",
            )

        user = await self.find_user(sam_account_name, ["dn"])
        if not user:
            return ADOperationResult(
                success=False,
                operation="reset_password",
                message=f"User not found: {sam_account_name}",
            )

        user_dn = user["dn"]
        # AD requires unicodePwd in UTF-16LE with quotes
        encoded_password = f'"{new_password}"'.encode("utf-16-le")
        client = await self._get_client()

        try:
            success = await client.modify_entry(
                dn=user_dn,
                changes={"unicodePwd": ("replace", [encoded_password])},
            )

            if success:
                logger.info(f"Password reset: {sam_account_name}")
                return ADOperationResult(
                    success=True,
                    operation="reset_password",
                    target_dn=user_dn,
                    message=f"Password reset successfully: {sam_account_name}",
                )
            else:
                return ADOperationResult(
                    success=False,
                    operation="reset_password",
                    target_dn=user_dn,
                    message=f"Password reset failed for: {sam_account_name}",
                )

        except PermissionError as e:
            return ADOperationResult(
                success=False,
                operation="reset_password",
                target_dn=user_dn,
                message=f"Permission denied: {e}",
            )
        except Exception as e:
            logger.error(f"Password reset failed: {e}", exc_info=True)
            return ADOperationResult(
                success=False,
                operation="reset_password",
                target_dn=user_dn,
                message=f"Operation failed: {e}",
            )

    async def find_group(
        self,
        group_name: str,
        attributes: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find a group by CN.

        Args:
            group_name: The group's common name
            attributes: Attributes to return (default: config group_attributes)

        Returns:
            Group entry dictionary or None if not found
        """
        client = await self._get_client()
        search_filter = (
            f"(&(objectClass={self._config.group_object_class})"
            f"(cn={group_name}))"
        )
        result = await client.search(
            search_filter=search_filter,
            search_base=self._config.group_search_base or self._config.base_dn,
            attributes=attributes or self._config.group_attributes,
            size_limit=1,
        )

        if result.entries:
            logger.info(f"Found group: {group_name}")
            return result.entries[0]

        logger.warning(f"Group not found: {group_name}")
        return None

    async def modify_group_membership(
        self,
        group_name: str,
        user_dn: str,
        action: str = "add",
    ) -> ADOperationResult:
        """Add or remove a user from a group.

        Args:
            group_name: The group's common name
            user_dn: The user's distinguished name
            action: "add" or "remove"

        Returns:
            ADOperationResult indicating success or failure
        """
        if action not in ("add", "remove"):
            return ADOperationResult(
                success=False,
                operation="modify_group_membership",
                message=f"Invalid action: {action}. Use 'add' or 'remove'.",
            )

        group = await self.find_group(group_name, ["dn", "member"])
        if not group:
            return ADOperationResult(
                success=False,
                operation="modify_group_membership",
                message=f"Group not found: {group_name}",
            )

        group_dn = group["dn"]
        ldap_action = "add" if action == "add" else "delete"
        client = await self._get_client()

        try:
            success = await client.modify_entry(
                dn=group_dn,
                changes={"member": (ldap_action, [user_dn])},
            )

            verb = "added to" if action == "add" else "removed from"
            if success:
                logger.info(f"User {user_dn} {verb} group {group_name}")
                return ADOperationResult(
                    success=True,
                    operation="modify_group_membership",
                    target_dn=group_dn,
                    message=f"User {verb} group {group_name}",
                    details={"user_dn": user_dn, "action": action},
                )
            else:
                return ADOperationResult(
                    success=False,
                    operation="modify_group_membership",
                    target_dn=group_dn,
                    message=f"Failed to {action} user {verb} group",
                )

        except PermissionError as e:
            return ADOperationResult(
                success=False,
                operation="modify_group_membership",
                target_dn=group_dn,
                message=f"Permission denied: {e}",
            )
        except Exception as e:
            logger.error(f"Group membership modify failed: {e}", exc_info=True)
            return ADOperationResult(
                success=False,
                operation="modify_group_membership",
                target_dn=group_dn,
                message=f"Operation failed: {e}",
            )

    async def get_group_members(
        self,
        group_name: str,
    ) -> ADOperationResult:
        """Get all members of a group.

        Args:
            group_name: The group's common name

        Returns:
            ADOperationResult with member list in details
        """
        group = await self.find_group(group_name, ["dn", "member"])
        if not group:
            return ADOperationResult(
                success=False,
                operation="get_group_members",
                message=f"Group not found: {group_name}",
            )

        members = group.get("attributes", {}).get("member", [])
        if isinstance(members, str):
            members = [members]

        return ADOperationResult(
            success=True,
            operation="get_group_members",
            target_dn=group["dn"],
            message=f"Found {len(members)} members in group {group_name}",
            details={"members": members, "count": len(members)},
        )
