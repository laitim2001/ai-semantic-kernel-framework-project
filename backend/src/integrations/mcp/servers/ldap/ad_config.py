"""
Active Directory Configuration for LDAP MCP Server.

Sprint 114: AD 場景基礎建設 (Phase 32)
Provides AD-specific configuration on top of base LDAPConfig.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .client import LDAPConfig

logger = logging.getLogger(__name__)


@dataclass
class ADConfig(LDAPConfig):
    """Active Directory-specific LDAP configuration.

    Extends LDAPConfig with AD-specific settings:
    - Separate search bases for users and groups
    - Connection pool sizing
    - Operation timeouts
    - AD-specific attribute mappings

    Attributes:
        user_search_base: OU for user searches (e.g., OU=Users,DC=company,DC=com)
        group_search_base: OU for group searches (e.g., OU=Groups,DC=company,DC=com)
        pool_size: Maximum number of pooled connections
        operation_timeout: Timeout for individual LDAP operations (seconds)
        user_object_class: Object class filter for user searches
        group_object_class: Object class filter for group searches
        user_attributes: Default attributes to return for user searches
        group_attributes: Default attributes to return for group searches
    """

    user_search_base: str = ""
    group_search_base: str = ""
    pool_size: int = 5
    operation_timeout: int = 30
    user_object_class: str = "user"
    group_object_class: str = "group"
    user_attributes: List[str] = field(
        default_factory=lambda: [
            "sAMAccountName",
            "cn",
            "displayName",
            "mail",
            "memberOf",
            "userAccountControl",
            "lockoutTime",
            "pwdLastSet",
            "whenCreated",
            "department",
            "title",
            "manager",
        ]
    )
    group_attributes: List[str] = field(
        default_factory=lambda: [
            "cn",
            "description",
            "member",
            "managedBy",
            "groupType",
            "whenCreated",
        ]
    )

    @classmethod
    def from_env(cls) -> "ADConfig":
        """Create AD config from environment variables.

        Environment variables:
            LDAP_SERVER: LDAP server hostname
            LDAP_PORT: LDAP port (default: 389)
            LDAP_USE_SSL: Use SSL (default: false)
            LDAP_USE_TLS: Use STARTTLS (default: false)
            LDAP_BASE_DN: Base DN (e.g., DC=company,DC=com)
            LDAP_BIND_DN: Service account DN
            LDAP_BIND_PASSWORD: Service account password
            LDAP_USER_SEARCH_BASE: User OU (default: base_dn)
            LDAP_GROUP_SEARCH_BASE: Group OU (default: base_dn)
            LDAP_POOL_SIZE: Connection pool size (default: 5)
            LDAP_OPERATION_TIMEOUT: Operation timeout seconds (default: 30)
            LDAP_READ_ONLY: Read-only mode (default: true)
            LDAP_ALLOWED_OPS: Allowed operations (default: search,bind)

        Returns:
            Configured ADConfig instance
        """
        base_dn = os.environ.get("LDAP_BASE_DN", "")
        ops_str = os.environ.get("LDAP_ALLOWED_OPS", "search,bind")
        allowed_ops = [op.strip() for op in ops_str.split(",") if op.strip()]

        config = cls(
            server=os.environ.get("LDAP_SERVER", "localhost"),
            port=int(os.environ.get("LDAP_PORT", "389")),
            use_ssl=os.environ.get("LDAP_USE_SSL", "false").lower() == "true",
            use_tls=os.environ.get("LDAP_USE_TLS", "false").lower() == "true",
            base_dn=base_dn,
            bind_dn=os.environ.get("LDAP_BIND_DN"),
            bind_password=os.environ.get("LDAP_BIND_PASSWORD"),
            allowed_operations=allowed_ops,
            read_only=os.environ.get("LDAP_READ_ONLY", "true").lower() == "true",
            timeout=int(os.environ.get("LDAP_TIMEOUT", "30")),
            user_search_base=os.environ.get("LDAP_USER_SEARCH_BASE", base_dn),
            group_search_base=os.environ.get("LDAP_GROUP_SEARCH_BASE", base_dn),
            pool_size=int(os.environ.get("LDAP_POOL_SIZE", "5")),
            operation_timeout=int(os.environ.get("LDAP_OPERATION_TIMEOUT", "30")),
        )

        logger.info(
            f"ADConfig loaded: server={config.server}:{config.port}, "
            f"ssl={config.use_ssl}, base_dn={config.base_dn}, "
            f"pool_size={config.pool_size}"
        )
        return config

    def validate(self) -> List[str]:
        """Validate configuration completeness.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: List[str] = []

        if not self.server or self.server == "localhost":
            errors.append("LDAP_SERVER should be set to a real AD server")

        if not self.base_dn:
            errors.append("LDAP_BASE_DN is required")

        if not self.bind_dn:
            errors.append("LDAP_BIND_DN is required for authenticated operations")

        if not self.bind_password:
            errors.append("LDAP_BIND_PASSWORD is required for authenticated operations")

        if self.pool_size < 1 or self.pool_size > 50:
            errors.append("LDAP_POOL_SIZE should be between 1 and 50")

        if self.operation_timeout < 5 or self.operation_timeout > 120:
            errors.append("LDAP_OPERATION_TIMEOUT should be between 5 and 120 seconds")

        return errors
