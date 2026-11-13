"""Verify both explicit database URIs and environment-based configuration."""
import importlib
import os
from unittest import TestCase
from unittest.mock import patch
from service import config


class TestConfiguration(TestCase):
    """Configuration should behave consistently in CI and the lab."""

    def tearDown(self):
        """Restore module settings from the unchanged process environment."""
        importlib.reload(config)

    def test_explicit_database_uri(self):
        """An explicit URI should take precedence over individual fields."""
        uri = "postgresql://test:test@localhost:5432/config_test"
        with patch.dict(os.environ, {"DATABASE_URI": uri}):
            importlib.reload(config)
            self.assertEqual(config.SQLALCHEMY_DATABASE_URI, uri)

    def test_database_uri_from_fields(self):
        """Individual connection fields should produce a database URI."""
        values = {
            "DATABASE_URI": "",
            "DATABASE_USER": "sample",
            "DATABASE_PASSWORD": "test-only",
            "DATABASE_HOST": "db",
            "DATABASE_NAME": "accounts",
        }
        with patch.dict(os.environ, values):
            importlib.reload(config)
            self.assertEqual(
                config.SQLALCHEMY_DATABASE_URI,
                "postgresql://sample:test-only@db:5432/accounts",
            )
