from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from hatch.utils.fs import Path

from hatch_uvenv.venv import UVVirtualEnv


class FakePlatform:
    """Minimal stand-in for ``hatch.utils.platform.Platform``.

    Records commands instead of executing them and lets each test pick whether it
    is emulating Windows.
    """

    def __init__(self, *, windows=False):
        self.windows = windows
        self.run_commands: list[list[str]] = []

    def run_command(self, command):
        self.run_commands.append(command)


@pytest.fixture
def venv_dir(tmp_path) -> Path:
    return Path(str(tmp_path)) / "venv"


class TestCreate:
    def test_default_command(self, venv_dir, monkeypatch):
        monkeypatch.delenv("HATCH_UV", raising=False)
        platform = FakePlatform()
        venv = UVVirtualEnv(venv_dir, platform)

        venv.create("/usr/bin/python3.12")

        assert platform.run_commands == [
            ["uv", "venv", str(venv_dir), "--seed", "--python", "/usr/bin/python3.12", "-q"]
        ]

    def test_uses_hatch_uv_env_var(self, venv_dir, monkeypatch):
        monkeypatch.setenv("HATCH_UV", "/custom/uv")
        platform = FakePlatform()
        venv = UVVirtualEnv(venv_dir, platform)

        venv.create("python")

        assert platform.run_commands[0][0] == "/custom/uv"

    def test_allow_system_packages(self, venv_dir, monkeypatch):
        monkeypatch.delenv("HATCH_UV", raising=False)
        platform = FakePlatform()
        venv = UVVirtualEnv(venv_dir, platform)

        venv.create("python", allow_system_packages=True)

        assert "--system-site-packages" in platform.run_commands[0]

    def test_no_system_packages_by_default(self, venv_dir, monkeypatch):
        monkeypatch.delenv("HATCH_UV", raising=False)
        platform = FakePlatform()
        venv = UVVirtualEnv(venv_dir, platform)

        venv.create("python")

        assert "--system-site-packages" not in platform.run_commands[0]

    def test_verbosity_flag(self, venv_dir, monkeypatch):
        monkeypatch.delenv("HATCH_UV", raising=False)
        platform = FakePlatform()
        venv = UVVirtualEnv(venv_dir, platform, verbosity=2)

        venv.create("python")

        # Verbosity is adjusted down by one, so verbosity 2 yields a single -v.
        assert platform.run_commands[0][-1] == "-v"


class TestActivateDeactivate:
    @pytest.mark.usefixtures("preserve_env")
    def test_activate_sets_virtual_env_and_path(self, venv_dir):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        venv.activate()

        assert os.environ["VIRTUAL_ENV"] == str(venv_dir)
        assert os.environ["PATH"].startswith(f"{venv_dir / 'bin'}{os.pathsep}")

    @pytest.mark.usefixtures("preserve_env")
    def test_deactivate_restores_previous_values(self, venv_dir, monkeypatch):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        monkeypatch.setenv("VIRTUAL_ENV", "/previous/env")
        monkeypatch.setenv("PATH", "/original/path")
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        venv.activate()
        venv.deactivate()

        assert os.environ["VIRTUAL_ENV"] == "/previous/env"
        assert os.environ["PATH"] == "/original/path"

    @pytest.mark.usefixtures("preserve_env")
    def test_deactivate_removes_vars_that_were_absent(self, venv_dir, monkeypatch):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        venv.activate()
        venv.deactivate()

        assert "VIRTUAL_ENV" not in os.environ

    @pytest.mark.usefixtures("preserve_env")
    def test_activate_clears_ignored_env_vars(self, venv_dir, monkeypatch):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        monkeypatch.setenv("PYTHONHOME", "/somewhere")
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        venv.activate()
        assert "PYTHONHOME" not in os.environ

        venv.deactivate()
        assert os.environ["PYTHONHOME"] == "/somewhere"

    @pytest.mark.usefixtures("preserve_env")
    def test_context_manager(self, venv_dir):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        with venv as entered:
            assert entered is venv
            assert os.environ["VIRTUAL_ENV"] == str(venv_dir)

        assert os.environ.get("VIRTUAL_ENV") != str(venv_dir)


class TestExistsAndRemove:
    def test_exists_false_when_missing(self, venv_dir):
        assert UVVirtualEnv(venv_dir, FakePlatform()).exists() is False

    def test_exists_true_when_present(self, venv_dir):
        venv_dir.mkdir()
        assert UVVirtualEnv(venv_dir, FakePlatform()).exists() is True

    def test_remove(self, venv_dir):
        venv_dir.mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        venv.remove()

        assert not venv_dir.is_dir()


class TestExecutablesDirectory:
    def test_posix_bin(self, venv_dir):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        assert venv.executables_directory == venv_dir / "bin"

    def test_windows_scripts(self, venv_dir):
        venv_dir.mkdir()
        (venv_dir / "Scripts").mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform(windows=True))

        assert venv.executables_directory == venv_dir / "Scripts"

    def test_missing_raises(self, venv_dir):
        venv_dir.mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        with pytest.raises(OSError, match="Unable to locate executables directory"):
            _ = venv.executables_directory

    def test_result_is_cached(self, venv_dir):
        venv_dir.mkdir()
        (venv_dir / "bin").mkdir()
        venv = UVVirtualEnv(venv_dir, FakePlatform())

        first = venv.executables_directory
        # Remove the directory; the cached value must still be returned.
        (venv_dir / "bin").rmdir()
        assert venv.executables_directory is first


class TestPythonInfoDelegation:
    def test_environment_and_sys_path_delegate(self, venv_dir):
        venv = UVVirtualEnv(venv_dir, FakePlatform())
        venv.python_info = SimpleNamespace(
            environment={"platform_system": "Linux"},
            sys_path=["/a", "/b"],
        )

        assert venv.environment == {"platform_system": "Linux"}
        assert venv.sys_path == ["/a", "/b"]
