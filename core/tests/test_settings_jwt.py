"""Tests for JWT signing key resolution across settings modules.

giraf-core issues the tokens that giraf-ai and weekplanner validate locally
with a shared JWT_SECRET. Every environment must therefore sign with
JWT_SECRET when it is set, or cross-service calls fail with an invalid
signature.
"""

import importlib
import os
from unittest.mock import patch

import pytest

from config.settings import base

SHARED_SECRET = "shared-secret-with-app-backends-at-least-32-bytes"


@pytest.fixture(autouse=True)
def restore_base_jwt_config():
    """dev and prod mutate base's NINJA_JWT in place; undo that after reloading."""
    original = dict(base.NINJA_JWT)
    yield
    base.NINJA_JWT.clear()
    base.NINJA_JWT.update(original)


def signing_key_for(module_name: str, env: dict[str, str]) -> str:
    with patch.dict(os.environ, env, clear=False):
        module = importlib.reload(importlib.import_module(module_name))
        return str(module.NINJA_JWT["SIGNING_KEY"])


class TestSigningKey:
    @pytest.mark.parametrize(
        ("module_name", "env"),
        [
            ("config.settings.dev", {"JWT_SECRET": SHARED_SECRET}),
            (
                "config.settings.prod",
                {"JWT_SECRET": SHARED_SECRET, "DJANGO_SECRET_KEY": "prod-secret-key-32-bytes-minimum!"},
            ),
        ],
    )
    def test_jwt_secret_is_used_when_set(self, module_name, env):
        assert signing_key_for(module_name, env) == SHARED_SECRET

    def test_dev_falls_back_to_secret_key_without_jwt_secret(self):
        env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET"}
        with patch.dict(os.environ, env, clear=True):
            module = importlib.reload(importlib.import_module("config.settings.dev"))
            assert module.NINJA_JWT["SIGNING_KEY"] == module.SECRET_KEY

    def test_dev_does_not_sign_with_the_insecure_dev_key(self):
        """Regression: dev.py overwrote SIGNING_KEY with the hardcoded dev SECRET_KEY."""
        key = signing_key_for("config.settings.dev", {"JWT_SECRET": SHARED_SECRET})
        assert "django-insecure" not in key
