"""
Versioning utilities for artifacts.
Implements semantic versioning based on schema changes.
"""
from typing import Dict, Tuple, Optional
from app.models import Artifact


def compute_next_version(
    latest_artifact: Optional[Artifact],
    new_schema: Dict
) -> Tuple[int, int, int]:
    """
    Compare schemas and determine next version.

    Implements semantic versioning:
    - MAJOR: Breaking changes (field removed, type changed)
    - MINOR: Backward-compatible changes (field added)
    - PATCH: No schema changes (only data updated)

    Args:
        latest_artifact: Previous artifact (None if first version)
        new_schema: New schema to compare

    Returns:
        Tuple of (major, minor, patch) version numbers
    """
    if not latest_artifact:
        return (1, 0, 0)

    old_schema = latest_artifact.schema_json
    diff = compute_schema_diff(old_schema, new_schema)

    if diff["breaking_changes"]:
        # Field removed or type changed → MAJOR
        return (latest_artifact.major_version + 1, 0, 0)
    elif diff["added_fields"]:
        # Field added → MINOR
        return (latest_artifact.major_version, latest_artifact.minor_version + 1, 0)
    else:
        # Only data changed → PATCH
        return (
            latest_artifact.major_version,
            latest_artifact.minor_version,
            latest_artifact.patch_version + 1
        )


def compute_schema_diff(old_schema: Dict, new_schema: Dict) -> Dict:
    """
    Compare two schemas and return diff.

    Args:
        old_schema: Previous JSON Schema
        new_schema: New JSON Schema

    Returns:
        Dict with:
        - added_fields: List of new fields
        - removed_fields: List of removed fields
        - type_changes: List of fields with type changes
        - breaking_changes: Boolean indicating if breaking changes exist
    """
    old_props = set(old_schema.get("properties", {}).keys())
    new_props = set(new_schema.get("properties", {}).keys())

    added = new_props - old_props
    removed = old_props - new_props
    common = old_props & new_props

    # Check for type changes in common fields
    type_changes = []
    for field in common:
        old_type = old_schema["properties"][field].get("type")
        new_type = new_schema["properties"][field].get("type")
        if old_type != new_type:
            type_changes.append(field)

    return {
        "added_fields": list(added),
        "removed_fields": list(removed),
        "type_changes": type_changes,
        "breaking_changes": len(removed) > 0 or len(type_changes) > 0
    }
