"""Real-path tests that exercise the live Hatch/virtualenv API surface.

Unlike test_plugin.py, these intentionally do NOT stub ``parent_python`` or
``uv_path``, so they fail if the plugin drifts from the interpreter-resolution
and uv APIs it depends on.
"""

from __future__ import annotations

import os
import shutil
import sys

import pytest


class TestInterpreterResolution:
    def test_find_existing_interpreter_returns_real_path(self, make_environment):
        env = make_environment(parent_python=None)
        current = f"{sys.version_info.major}.{sys.version_info.minor}"

        result = env._find_existing_interpreter(current)  # noqa: SLF001

        assert result is not None
        assert os.path.exists(result)

    def test_parent_python_resolves_to_existing_interpreter(self, make_environment):
        # Exercises the full resolution stack: parent_python -> resolvers ->
        # _find_existing_interpreter / _get_available_distribution.
        env = make_environment(parent_python=None)

        assert os.path.exists(env.parent_python)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
class TestRealCreate:
    def test_create_makes_a_usable_virtualenv(self, make_environment):
        # End-to-end: real interpreter resolution + a real `uv venv` invocation
        # through hatch.venv.core.UVVirtualEnv. Guards against drift in the
        # create()/UVVirtualEnv API and the uv command itself.
        env = make_environment(parent_python=None, uv_path=shutil.which("uv"))
        assert env.exists() is False

        env.create()

        assert env.exists() is True
        assert env.virtual_env_path.is_dir()
