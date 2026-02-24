"""
AD Scenario E2E Test Fixtures — Sprint 118.

Provides realistic RITM payloads and expected outcomes for each
AD scenario tested in the E2E suite.

Fixtures:
    - Account Unlock RITM payload
    - Password Reset RITM payload
    - Group Membership Change RITM payload
    - Unknown Catalog Item RITM payload
    - Duplicate RITM payload (idempotency)
"""

from typing import Any, Dict


# =============================================================================
# RITM Payloads
# =============================================================================


def account_unlock_ritm() -> Dict[str, Any]:
    """RITM payload for AD Account Unlock scenario.

    Maps to intent: ad.account.unlock
    Expected LDAP action: unlock user "john.doe"
    """
    return {
        "sys_id": "ritm-unlock-001",
        "number": "RITM0012345",
        "state": "1",
        "cat_item": "cat-ad-unlock",
        "cat_item_name": "AD Account Unlock",
        "requested_for": "john.doe",
        "requested_by": "manager.smith",
        "short_description": "Unlock AD account for john.doe",
        "description": (
            "User john.doe has been locked out of their AD account "
            "after multiple failed login attempts. Please unlock."
        ),
        "variables": {
            "affected_user": "john.doe",
            "reason": "Multiple failed login attempts",
        },
        "priority": "3",
        "assignment_group": "IT-AD-Support",
        "sys_created_on": "2026-02-24 09:00:00",
    }


def password_reset_ritm() -> Dict[str, Any]:
    """RITM payload for AD Password Reset scenario.

    Maps to intent: ad.password.reset
    Expected LDAP action: reset password for "jane.doe"
    """
    return {
        "sys_id": "ritm-reset-002",
        "number": "RITM0012346",
        "state": "1",
        "cat_item": "cat-ad-pwreset",
        "cat_item_name": "AD Password Reset",
        "requested_for": "jane.doe",
        "requested_by": "jane.doe",
        "short_description": "Reset AD password for jane.doe",
        "description": "User forgot their password and needs a reset.",
        "variables": {
            "affected_user": "jane.doe",
            "temp_password": "TempPass2026!",
        },
        "priority": "3",
        "assignment_group": "IT-AD-Support",
        "sys_created_on": "2026-02-24 09:15:00",
    }


def group_membership_change_ritm() -> Dict[str, Any]:
    """RITM payload for AD Group Membership Change scenario.

    Maps to intent: ad.group.modify
    Expected LDAP action: add "bob.chen" to "admin-group"
    Requires approval (high risk).
    """
    return {
        "sys_id": "ritm-group-003",
        "number": "RITM0012347",
        "state": "1",
        "cat_item": "cat-ad-group",
        "cat_item_name": "AD Group Membership Change",
        "requested_for": "bob.chen",
        "requested_by": "manager.lee",
        "short_description": "Add bob.chen to admin-group",
        "description": (
            "Bob Chen has been promoted and needs admin-group "
            "membership for elevated privileges."
        ),
        "variables": {
            "affected_user": "bob.chen",
            "group_name": "admin-group",
            "action_type": "add",
        },
        "priority": "2",
        "assignment_group": "IT-AD-Support",
        "sys_created_on": "2026-02-24 09:30:00",
    }


def unknown_catalog_item_ritm() -> Dict[str, Any]:
    """RITM payload for an Unknown Catalog Item.

    This should trigger the SemanticRouter fallback path
    since no mapping exists for this catalog item name.
    """
    return {
        "sys_id": "ritm-unknown-004",
        "number": "RITM0012348",
        "state": "1",
        "cat_item": "cat-unknown",
        "cat_item_name": "Office 365 License Assignment",
        "requested_for": "alice.wang",
        "requested_by": "alice.wang",
        "short_description": "Assign Office 365 E3 license to alice.wang",
        "description": "New hire needs Office 365 E3 license.",
        "variables": {
            "affected_user": "alice.wang",
            "license_type": "E3",
        },
        "priority": "4",
        "assignment_group": "IT-License-Mgmt",
        "sys_created_on": "2026-02-24 10:00:00",
    }


def duplicate_ritm() -> Dict[str, Any]:
    """RITM payload that duplicates account_unlock_ritm's sys_id.

    Used for testing idempotency — sending the same event twice
    should result in a 409 Conflict on the second attempt.
    """
    return account_unlock_ritm()


# =============================================================================
# Expected Outcomes
# =============================================================================


EXPECTED_INTENTS = {
    "AD Account Unlock": "ad.account.unlock",
    "AD Password Reset": "ad.password.reset",
    "AD Group Membership Change": "ad.group.modify",
}

EXPECTED_VARIABLES = {
    "ad.account.unlock": {
        "target_user": "john.doe",
        "reason": "Unlock AD account for john.doe",
    },
    "ad.password.reset": {
        "target_user": "jane.doe",
        "temporary_password": "TempPass2026!",
    },
    "ad.group.modify": {
        "target_user": "bob.chen",
        "group_name": "admin-group",
        "action": "add",
    },
}

# LDAP operations expected for each intent
EXPECTED_LDAP_OPERATIONS = {
    "ad.account.unlock": {
        "tool": "modify_user_attributes",
        "target_user": "john.doe",
        "attributes": {"lockoutTime": "0"},
    },
    "ad.password.reset": {
        "tool": "modify_user_attributes",
        "target_user": "jane.doe",
        "attributes": {"unicodePwd": "TempPass2026!"},
    },
    "ad.group.modify": {
        "tool": "modify_user_attributes",
        "target_user": "bob.chen",
        "attributes": {"memberOf": "admin-group"},
    },
}
