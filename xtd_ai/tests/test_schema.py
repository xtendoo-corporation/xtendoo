from odoo.tests import TransactionCase, tagged

from ..tools.decorator import xtd_ai_tool
from ..tools.schema import check_tool_schema, validate

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 2, "maxLength": 5},
        "qty": {"type": "integer", "minimum": 1, "maximum": 10},
        "price": {"type": "number"},
        "flag": {"type": "boolean"},
        "kind": {"type": "string", "enum": ["a", "b"]},
        "day": {"type": "string", "format": "date"},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
        "sub": {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
            "additionalProperties": False,
        },
    },
    "required": ["name"],
    "additionalProperties": False,
}


@tagged("post_install", "-at_install")
class TestSchema(TransactionCase):
    def ok(self, value):
        self.assertEqual(validate(SCHEMA, value), [], value)

    def bad(self, value, fragment=None):
        errors = validate(SCHEMA, value)
        self.assertTrue(errors, value)
        if fragment:
            self.assertTrue(any(fragment in e for e in errors), errors)

    def test_valid(self):
        self.ok({"name": "ab"})
        self.ok(
            {
                "name": "abc",
                "qty": 3,
                "price": 1.5,
                "flag": True,
                "kind": "a",
                "day": "2026-10-20",
                "tags": ["x"],
                "sub": {"x": 1},
            }
        )
        self.ok({"name": "abc", "price": 2})

    def test_required_and_additional(self):
        self.bad({}, "missing required")
        self.bad({"name": "abc", "other": 1}, "unexpected property")
        self.bad({"name": "abc", "sub": {"x": 1, "y": 2}}, "unexpected property")
        self.bad({"name": "abc", "sub": {}}, "missing required")

    def test_types(self):
        self.bad("text", "expected object")
        self.bad({"name": 1}, "expected string")
        self.bad({"name": "abc", "qty": "3"}, "expected integer")
        self.bad({"name": "abc", "qty": 3.5}, "expected integer")
        self.bad({"name": "abc", "qty": True}, "expected integer")
        self.bad({"name": "abc", "price": "1"}, "expected number")
        self.bad({"name": "abc", "price": False}, "expected number")
        self.bad({"name": "abc", "flag": 1}, "expected boolean")
        self.bad({"name": "abc", "tags": "x"}, "expected array")

    def test_constraints(self):
        self.bad({"name": "a"}, "shorter")
        self.bad({"name": "abcdef"}, "longer")
        self.bad({"name": "abc", "qty": 0}, ">=")
        self.bad({"name": "abc", "qty": 11}, "<=")
        self.bad({"name": "abc", "kind": "c"}, "one of")
        self.bad({"name": "abc", "tags": ["a", "b", "c"]}, "at most")
        self.bad({"name": "abc", "tags": [1]}, "expected string")

    def test_date_format(self):
        self.bad({"name": "abc", "day": "20-10-2026"}, "date")
        self.bad({"name": "abc", "day": "2026-13-01"}, "date")
        self.bad({"name": "abc", "day": "2026-02-30"}, "date")

    def test_type_list_and_pattern(self):
        schema = {"type": ["string", "null"], "pattern": "^a"}
        self.assertEqual(validate(schema, None), [])
        self.assertEqual(validate(schema, "abc"), [])
        self.assertTrue(validate(schema, "xbc"))
        self.assertTrue(validate(schema, 3))

    def test_check_tool_schema(self):
        check_tool_schema("t", SCHEMA)
        with self.assertRaises(ValueError):
            check_tool_schema("t", {"type": "object", "properties": {}, "required": []})
        with self.assertRaises(ValueError):
            check_tool_schema(
                "t", {"type": "object", "properties": {}, "additionalProperties": False}
            )
        with self.assertRaises(ValueError):
            check_tool_schema(
                "t",
                {
                    "type": "object",
                    "properties": {},
                    "required": ["x"],
                    "additionalProperties": False,
                },
            )

    def test_decorator_rules(self):
        schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        with self.assertRaises(ValueError):  # write tool without preview
            xtd_ai_tool(
                name="x", title="x", description="x", input_schema=schema, kind="draft"
            )
        with self.assertRaises(ValueError):
            xtd_ai_tool(
                name="x", title="x", description="x", input_schema=schema, kind="nope"
            )
