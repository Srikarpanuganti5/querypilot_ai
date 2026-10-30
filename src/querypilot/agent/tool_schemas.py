"""Strict Responses function schemas derived from the registry's Pydantic contracts."""

from copy import deepcopy
from typing import Any


def _strict(schema: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(schema)
    value.pop("default", None)
    if "properties" in value:
        required = set(value.get("required", []))
        properties = {}
        for name, child in value["properties"].items():
            child = _strict(child)
            if (
                name not in required
                and not any(option.get("type") == "null" for option in child.get("anyOf", []))
                and child.get("type") != "null"
            ):
                child = {"anyOf": [child, {"type": "null"}]}
            properties[name] = child
        value.update(properties=properties, required=list(properties), additionalProperties=False)
    for keyword in ("anyOf", "oneOf", "allOf"):
        if keyword in value:
            value[keyword] = [_strict(child) for child in value[keyword]]
    if "$defs" in value:
        value["$defs"] = {name: _strict(child) for name, child in value["$defs"].items()}
    if isinstance(value.get("items"), dict):
        value["items"] = _strict(value["items"])
    return value


def function_schemas(definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": name,
            "description": definition["description"],
            "parameters": _strict(definition["input_schema"]),
            "strict": True,
        }
        for name, definition in definitions.items()
    ]


def normalize_arguments(name: str, arguments: dict, definitions: dict) -> dict:
    # The provider must submit optional fields as null in strict mode. For fields with
    # non-null Pydantic defaults, null means "use that default", not a relaxed validator.
    properties = definitions.get(name, {}).get("input_schema", {}).get("properties", {})
    return {
        key: value
        for key, value in arguments.items()
        if not (value is None and properties.get(key, {}).get("default") is not None)
    }
