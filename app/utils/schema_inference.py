"""
Schema inference utilities for dataset generation.
Infers JSON Schema from data samples.
"""
from typing import List, Dict, Any


def infer_schema(data: List[Dict[str, Any]]) -> Dict:
    """
    Infer JSON Schema from data sample.

    Args:
        data: List of dictionaries representing records

    Returns:
        JSON Schema dict with type, properties, and required fields
    """
    if not data:
        return {"type": "object", "properties": {}, "required": []}

    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    # Analyze all records to build schema
    for record in data:
        for key, value in record.items():
            if key not in schema["properties"]:
                schema["properties"][key] = infer_field_type(value)

    # Determine required fields (present in ALL records)
    if data:
        all_keys = set()
        for record in data:
            all_keys.update(record.keys())

        for key in all_keys:
            if all(key in record for record in data):
                schema["required"].append(key)

    return schema


def infer_field_type(value: Any) -> Dict:
    """
    Infer JSON Schema type from Python value.

    Args:
        value: Python value to analyze

    Returns:
        JSON Schema type definition
    """
    if isinstance(value, bool):
        return {"type": "boolean"}
    elif isinstance(value, int):
        return {"type": "integer"}
    elif isinstance(value, float):
        return {"type": "number"}
    elif isinstance(value, str):
        return {"type": "string"}
    elif isinstance(value, list):
        if len(value) > 0:
            # Infer array item type from first element
            item_type = infer_field_type(value[0])
            return {"type": "array", "items": item_type}
        else:
            return {"type": "array"}
    elif isinstance(value, dict):
        # For nested objects, recursively infer schema
        nested_schema = infer_schema([value])
        return {"type": "object", "properties": nested_schema.get("properties", {})}
    else:
        # Default to string for unknown types
        return {"type": "string"}
