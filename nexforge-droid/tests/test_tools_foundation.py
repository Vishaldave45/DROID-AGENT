"""Unit tests for tool contracts and tool registry."""

import unittest
from typing import Any
from app.tools.base import Tool, ToolRegistry, ToolResult


class DummyEchoTool(Tool):
    name = "dummy_echo"
    description = "Echoes a given message."
    input_schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        message = kwargs.get("message", "")
        return ToolResult(success=True, data={"echo": message})


class TestToolRegistry(unittest.TestCase):

    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.tool = DummyEchoTool()

    def test_tool_registration_and_lookup(self) -> None:
        self.registry.register(self.tool)
        retrieved = self.registry.get("dummy_echo")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "dummy_echo")

    def test_duplicate_registration_raises_error(self) -> None:
        self.registry.register(self.tool)
        with self.assertRaises(ValueError):
            self.registry.register(self.tool)

    def test_tool_execution(self) -> None:
        result = self.tool.execute(message="Hello NexForge")
        self.assertTrue(result.success)
        self.assertEqual(result.data["echo"], "Hello NexForge")

    def test_schema_generation(self) -> None:
        self.registry.register(self.tool)
        schemas = self.registry.get_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["name"], "dummy_echo")
        self.assertIn("properties", schemas[0]["parameters"])


if __name__ == "__main__":
    unittest.main()
