"""
Generic JSON serialization utilities.

**Single Responsibility**: Provide generic JSON serialization for dataclasses.
This module is changed only when JSON format or serialization logic changes.

**Responsibility**: JSON serialization and deserialization
**Reason to Change**: When JSON format or serialization behavior changes
"""

import json
from typing import Any, Dict, Type, TypeVar
from dataclasses import asdict

T = TypeVar('T')


def serialize_to_json(obj: Any, indent: int = 2) -> str:
    """
    Serialize a dataclass to JSON string.
    
    Args:
        obj: Object to serialize (typically a dataclass)
        indent: JSON indentation level
    
    Returns:
        JSON string
    """
    if hasattr(obj, '__dataclass_fields__'):
        return json.dumps(asdict(obj), indent=indent, default=str)
    else:
        return json.dumps(obj, indent=indent, default=str)


def deserialize_from_json(data: str, model_type: Type[T]) -> T:
    """
    Deserialize JSON string to a dataclass instance.
    
    Args:
        data: JSON string to deserialize
        model_type: Target dataclass type
    
    Returns:
        Instance of model_type
    """
    json_data = json.loads(data)
    return model_type(**json_data)


__all__ = [
    "serialize_to_json",
    "deserialize_from_json",
]
