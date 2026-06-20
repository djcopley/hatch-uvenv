from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest
from hatch.cli.application import Application
from hatch.project.core import Project
from hatch.utils.fs import Path
from hatch.utils.platform import Platform

from hatch_uvenv.plugin import UVVirtualEnvironmentPlugin

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(scope="session")
def platform() -> Platform:
    return Platform()


@pytest.fixture(scope="session")
def application() -> Application:
    # Only the EnvironmentInterface constructor requires this; the parts exercised
    # by these tests never touch the live application.
    return Application(sys.exit, verbosity=0, enable_color=False, interactive=False)


@pytest.fixture
def project_dir(tmp_path) -> Path:
    root = Path(str(tmp_path)) / "my-app"
    root.mkdir()
    return root


@pytest.fixture
def data_dir(tmp_path) -> Path:
    directory = Path(str(tmp_path)) / "data"
    directory.mkdir()
    return directory


@pytest.fixture
def preserve_env() -> Iterator[None]:
    """Snapshot ``os.environ`` and restore it after the test.

    ``UVVirtualEnv.activate`` mutates the real process environment, so tests that
    exercise it need the original environment put back regardless of outcome.
    """
    saved = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


@pytest.fixture
def make_environment(platform, application, project_dir, data_dir):
    """Factory that builds a fully constructed ``UVVirtualEnvironmentPlugin``.

    The ``uv_path`` and ``parent_python`` cached properties are pre-seeded by
    default so that command construction does not reach out to the real
    application or interpreter resolver. Pass ``uv_path=None`` /
    ``parent_python=None`` to exercise the real resolution logic.
    """
    default_config = {"project": {"name": "my-app", "version": "0.1.0"}}

    def factory(
        *,
        config=None,
        name="default",
        env_config=None,
        root=None,
        data_directory=None,
        isolated_data_directory=None,
        verbosity=0,
        matrix_variables=None,
        uv_path="/usr/bin/uv",
        parent_python=sys.executable,
    ) -> UVVirtualEnvironmentPlugin:
        config = default_config if config is None else config
        root = project_dir if root is None else root
        data_directory = data_dir if data_directory is None else data_directory
        isolated = data_directory if isolated_data_directory is None else isolated_data_directory

        project = Project(root, config=config)
        cfg = project.config.envs[name] if env_config is None else env_config

        environment = UVVirtualEnvironmentPlugin(
            root,
            project.metadata,
            name,
            cfg,
            matrix_variables or {},
            data_directory,
            isolated,
            platform,
            verbosity,
            application,
        )
        if uv_path is not None:
            environment.__dict__["uv_path"] = uv_path
        if parent_python is not None:
            environment.__dict__["parent_python"] = parent_python
        return environment

    return factory
