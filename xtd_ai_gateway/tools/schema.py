"""Minimal JSON Schema validator (``jsonschema`` is not available in the image).

Supported keywords: type (string or list; object, string, integer, number,
boolean, array, null), properties, required, additionalProperties (bool),
enum, minimum, maximum, minLength, maxLength, pattern, items, minItems,
maxItems and ``format: date`` (ISO ``YYYY-MM-DD``). Unknown keywords are
ignored. ``validate`` returns a list of human readable error strings
(empty list means valid).
"""

import re
from datetime import date

_TYPES = {"object", "string", "integer", "number", "boolean", "array", "null"}


def _type_ok(expected, value):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "null":
        return value is None
    return False


def validate(schema, value, path="$"):
    errors = []
    _validate(schema, value, path, errors)
    return errors


def _validate(schema, value, path, errors):  # noqa: C901  one flat JSON-schema dispatcher
    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(t, value) for t in types):
            errors.append(f"{path}: expected {'/'.join(types)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: must be >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: must be <= {schema['maximum']}")
    elif isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match the required pattern")
        if schema.get("format") == "date":
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError
                date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: must be a date YYYY-MM-DD")
    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: at most {schema['maxItems']} items")
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                _validate(items, item, f"{path}[{index}]", errors)
    elif isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required property '{key}'")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected property '{key}'")
        for key, sub in properties.items():
            if key in value:
                _validate(sub, value[key], f"{path}.{key}", errors)


def check_tool_schema(name, schema):
    """Raise ``ValueError`` if ``schema`` does not respect the tool schema contract."""
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError(f"Tool {name}: input_schema must have type 'object'")
    if schema.get("additionalProperties") is not False:
        raise ValueError(f"Tool {name}: input_schema needs additionalProperties: false")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise ValueError(
            f"Tool {name}: input_schema needs explicit 'properties' and 'required'"
        )
    unknown = [key for key in required if key not in properties]
    if unknown:
        raise ValueError(f"Tool {name}: required keys not in properties: {unknown}")
    _check_types(name, schema)


def _check_types(name, schema):
    expected = schema.get("type")
    for t in (
        expected if isinstance(expected, list) else ([expected] if expected else [])
    ):
        if t not in _TYPES:
            raise ValueError(f"Tool {name}: unsupported type {t!r}")
    for sub in schema.get("properties", {}).values():
        _check_types(name, sub)
    if isinstance(schema.get("items"), dict):
        _check_types(name, schema["items"])
