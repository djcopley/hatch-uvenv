from __future__ import annotations

import sys

from hatch.utils.fs import Path


class TestOptionTypes:
    def test_get_option_types(self, make_environment):
        assert make_environment().get_option_types() == {
            "system-packages": bool,
            "path": str,
            "python-sources": list,
            "uv-path": str,
        }


class TestUvSyncCommand:
    def test_defaults(self, make_environment):
        env = make_environment(uv_path="/bin/uv")
        assert env.construct_uv_sync_command() == ["/bin/uv", "sync", "--active", "--locked", "-q"]

    def test_locked_disabled(self, make_environment):
        env = make_environment(
            env_config={"locked": False},
            uv_path="/bin/uv",
        )
        command = env.construct_uv_sync_command()
        assert "--locked" not in command

    def test_groups(self, make_environment):
        env = make_environment(env_config={"groups": ["dev", "docs"]}, uv_path="/bin/uv")
        command = env.construct_uv_sync_command()
        assert "--group=dev" in command
        assert "--group=docs" in command

    def test_features_become_extras(self, make_environment):
        config = {
            "project": {
                "name": "my-app",
                "version": "0.1.0",
                "optional-dependencies": {"cli": ["click"], "web": ["flask"]},
            },
        }
        env = make_environment(config=config, env_config={"features": ["cli", "web"]}, uv_path="/bin/uv")
        command = env.construct_uv_sync_command()
        assert "--extra=cli" in command
        assert "--extra=web" in command

    def test_extra_uv_flags(self, make_environment):
        env = make_environment(env_config={"uv-flags": ["--no-cache"]}, uv_path="/bin/uv")
        assert env.construct_uv_sync_command()[-1] == "--no-cache"

    def test_verbosity(self, make_environment):
        env = make_environment(verbosity=2, uv_path="/bin/uv")
        # Verbosity is adjusted down by one, so verbosity 2 yields a single -v.
        assert "-v" in env.construct_uv_sync_command()


class TestPipInstallCommand:
    def test_basic(self, make_environment):
        env = make_environment(uv_path="/bin/uv")
        assert env.construct_pip_install_command(["flask", "click"]) == [
            "/bin/uv",
            "pip",
            "install",
            "-q",
            "flask",
            "click",
        ]


class TestFlagHelpers:
    def test_add_group_flags(self, make_environment):
        env = make_environment(env_config={"groups": ["dev"]})
        command = ["uv"]
        env.add_group_flags(command)
        assert command == ["uv", "--group=dev"]

    def test_add_uv_flags(self, make_environment):
        env = make_environment(env_config={"uv-flags": ["--frozen"]})
        command = ["uv"]
        env.add_uv_flags(command)
        assert command == ["uv", "--frozen"]


class TestExposeUv:
    def test_sets_hatch_uv(self, make_environment):
        env = make_environment(uv_path="/some/uv")
        assert env.expose_uv()["HATCH_UV"] == "/some/uv"


class TestDependencyState:
    def test_dependencies_never_in_sync(self, make_environment):
        # Syncing is delegated to uv, so the plugin always reports out of sync.
        assert make_environment().dependencies_in_sync() is False

    def test_dependency_hash_is_unstable(self, make_environment):
        env = make_environment()
        assert isinstance(env.dependency_hash(), str)


class TestPythonSources:
    def test_default(self, make_environment):
        assert make_environment()._python_sources == ["external", "internal"]  # noqa: SLF001

    def test_override(self, make_environment):
        env = make_environment(env_config={"python-sources": ["internal"]})
        assert env._python_sources == ["internal"]  # noqa: SLF001

    def test_resolvers(self, make_environment):
        assert set(make_environment()._python_resolvers()) == {"external", "internal"}  # noqa: SLF001


class TestPaths:
    def test_default_env_layout(self, make_environment, data_dir, project_dir):
        env = make_environment()
        project_id = project_dir.id
        # data / <project-name> / <project-id> / <venv-name>
        assert env.storage_path == data_dir / "my-app" / project_id
        assert env.virtual_env_path == env.storage_path / "my-app"
        assert env.find() == env.virtual_env_path

    def test_named_env_uses_env_name(self, make_environment):
        config = {
            "project": {"name": "my-app", "version": "0.1.0"},
            "tool": {"hatch": {"envs": {"test": {"type": "uvenv"}}}},
        }
        env = make_environment(config=config, name="test")
        assert env.virtual_env_path.name == "test"

    def test_unmanaged_project(self, make_environment):
        # No [project] table means the project is "unmanaged".
        config = {"tool": {"hatch": {"envs": {"default": {}}}}}
        env = make_environment(config=config)
        assert env.virtual_env_path.name.endswith("-unmanaged")

    def test_explicit_relative_path(self, make_environment, project_dir):
        env = make_environment(env_config={"path": "myenv"})
        assert env.virtual_env_path == (project_dir / "myenv").resolve()

    def test_explicit_absolute_path(self, make_environment, tmp_path):
        absolute = str(Path(str(tmp_path)) / "explicit-env")
        env = make_environment(env_config={"path": absolute})
        assert str(env.virtual_env_path) == absolute


class TestExists:
    def test_false_before_creation(self, make_environment):
        assert make_environment().exists() is False


class TestCreate:
    def test_writes_gitignore_when_storage_under_root(self, make_environment, project_dir):
        # Place the data directory inside the project root so the plugin uses the
        # flat layout and drops a .gitignore beside the environments.
        inner_data = project_dir / ".hatch-data"
        inner_data.mkdir()
        env = make_environment(data_directory=inner_data)
        env.virtual_env.create = lambda *_args, **_kwargs: None

        env.create()

        gitignore = env.storage_path / ".gitignore"
        assert gitignore.is_file()
        assert gitignore.read_text().splitlines()[0] == "# This file was automatically created by Hatch"

    def test_create_forwards_system_packages_option(self, make_environment, project_dir):
        inner_data = project_dir / ".hatch-data"
        inner_data.mkdir()
        env = make_environment(data_directory=inner_data, env_config={"system-packages": True})
        captured = {}
        env.virtual_env.create = lambda python, *, allow_system_packages=False: captured.update(
            python=python, allow_system_packages=allow_system_packages
        )

        env.create()

        assert captured == {"python": sys.executable, "allow_system_packages": True}


class TestRemove:
    def test_removes_storage_when_only_gitignore_remains(self, make_environment, project_dir):
        inner_data = project_dir / ".hatch-data"
        inner_data.mkdir()
        env = make_environment(data_directory=inner_data)
        env.virtual_env.create = lambda *_args, **_kwargs: None
        env.create()
        assert env.storage_path.is_dir()

        env.virtual_env.remove = lambda: None
        env.build_virtual_env.remove = lambda: None
        env.remove()

        assert not env.storage_path.is_dir()
