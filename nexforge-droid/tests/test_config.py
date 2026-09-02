"""Unit tests for configuration management."""

import os
import unittest
from unittest.mock import patch

from app.config import Settings, get_settings, reset_settings


class TestConfiguration(unittest.TestCase):

    def setUp(self) -> None:
        reset_settings()

    def tearDown(self) -> None:
        reset_settings()

    def test_default_settings(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.environment, "development")
        self.assertFalse(settings.is_production())
        self.assertEqual(settings.max_iterations, 25)
        self.assertEqual(settings.max_context_tokens, 32000)
        self.assertTrue(settings.auto_approve_safe_tools)

    @patch.dict(os.environ, {"ENVIRONMENT": "production", "MAX_ITERATIONS": "50"})
    def test_custom_environment_settings(self) -> None:
        reset_settings()
        settings = get_settings()
        self.assertEqual(settings.environment, "production")
        self.assertTrue(settings.is_production())
        self.assertEqual(settings.max_iterations, 50)


if __name__ == "__main__":
    unittest.main()
