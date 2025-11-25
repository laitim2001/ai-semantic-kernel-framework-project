"""
Version Differ - Tool for comparing workflow versions
"""
from typing import Dict, Any, Set


class VersionDiffer:
    """Utility class for comparing workflow version definitions"""

    @staticmethod
    def compare(version1_def: Dict[str, Any], version2_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two workflow version definitions and identify differences

        Args:
            version1_def: First version definition (typically older)
            version2_def: Second version definition (typically newer)

        Returns:
            Dictionary containing:
            - added: Fields present in version2 but not in version1
            - removed: Fields present in version1 but not in version2
            - modified: Fields present in both but with different values
            - unchanged: Fields present in both with same values
        """
        added = {}
        removed = {}
        modified = {}
        unchanged = {}

        # Get all keys from both versions
        keys1 = set(version1_def.keys())
        keys2 = set(version2_def.keys())

        # Find added keys (in v2 but not in v1)
        added_keys = keys2 - keys1
        for key in added_keys:
            added[key] = version2_def[key]

        # Find removed keys (in v1 but not in v2)
        removed_keys = keys1 - keys2
        for key in removed_keys:
            removed[key] = version1_def[key]

        # Find modified and unchanged keys (in both)
        common_keys = keys1 & keys2
        for key in common_keys:
            val1 = version1_def[key]
            val2 = version2_def[key]

            if val1 == val2:
                unchanged[key] = val1
            else:
                # Check if values are nested dicts/lists
                if isinstance(val1, dict) and isinstance(val2, dict):
                    # Recursively compare nested dicts
                    nested_diff = VersionDiffer._compare_nested_dict(val1, val2)
                    if nested_diff["has_changes"]:
                        modified[key] = {
                            "old": val1,
                            "new": val2,
                            "details": nested_diff
                        }
                    else:
                        unchanged[key] = val1

                elif isinstance(val1, list) and isinstance(val2, list):
                    # Compare lists
                    if VersionDiffer._lists_equal(val1, val2):
                        unchanged[key] = val1
                    else:
                        modified[key] = {
                            "old": val1,
                            "new": val2
                        }

                else:
                    # Simple value comparison
                    modified[key] = {
                        "old": val1,
                        "new": val2
                    }

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged
        }

    @staticmethod
    def _compare_nested_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare nested dictionaries

        Args:
            dict1: First dictionary
            dict2: Second dictionary

        Returns:
            Dictionary with change information
        """
        added = {}
        removed = {}
        modified = {}

        keys1 = set(dict1.keys())
        keys2 = set(dict2.keys())

        # Added keys
        for key in keys2 - keys1:
            added[key] = dict2[key]

        # Removed keys
        for key in keys1 - keys2:
            removed[key] = dict1[key]

        # Modified keys
        for key in keys1 & keys2:
            if dict1[key] != dict2[key]:
                modified[key] = {
                    "old": dict1[key],
                    "new": dict2[key]
                }

        has_changes = bool(added or removed or modified)

        return {
            "has_changes": has_changes,
            "added": added,
            "removed": removed,
            "modified": modified
        }

    @staticmethod
    def _lists_equal(list1: list, list2: list) -> bool:
        """
        Check if two lists are equal (order-sensitive)

        Args:
            list1: First list
            list2: Second list

        Returns:
            True if lists are equal, False otherwise
        """
        if len(list1) != len(list2):
            return False

        return all(item1 == item2 for item1, item2 in zip(list1, list2))

    @staticmethod
    def get_summary(differences: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of differences

        Args:
            differences: Dictionary from compare() method

        Returns:
            Human-readable summary string
        """
        summary_parts = []

        if differences["added"]:
            added_keys = ", ".join(differences["added"].keys())
            summary_parts.append(f"Added fields: {added_keys}")

        if differences["removed"]:
            removed_keys = ", ".join(differences["removed"].keys())
            summary_parts.append(f"Removed fields: {removed_keys}")

        if differences["modified"]:
            modified_keys = ", ".join(differences["modified"].keys())
            summary_parts.append(f"Modified fields: {modified_keys}")

        if not summary_parts:
            return "No changes detected"

        return "; ".join(summary_parts)
