import os

from hatch.env.utils import add_verbosity_flag
from hatch.utils.env import PythonInfo


class UVVirtualEnv:
    IGNORED_ENV_VARS = ("__PYVENV_LAUNCHER__", "PYTHONHOME")

    def __init__(self, directory, platform, verbosity=0):
        self.directory = directory
        self.platform = platform
        self.verbosity = verbosity
        self.python_info = PythonInfo(platform)

        self._env_vars_to_restore = {}
        self._executables_directory = None

    def activate(self):
        self._env_vars_to_restore["VIRTUAL_ENV"] = os.environ.pop("VIRTUAL_ENV", None)
        os.environ["VIRTUAL_ENV"] = str(self.directory)

        old_path = os.environ.pop("PATH", None)
        self._env_vars_to_restore["PATH"] = old_path
        if old_path is None:
            os.environ["PATH"] = f"{self.executables_directory}{os.pathsep}{os.defpath}"
        else:
            os.environ["PATH"] = f"{self.executables_directory}{os.pathsep}{old_path}"

        for env_var in self.IGNORED_ENV_VARS:
            self._env_vars_to_restore[env_var] = os.environ.pop(env_var, None)

    def deactivate(self):
        for env_var, value in self._env_vars_to_restore.items():
            if value is None:
                os.environ.pop(env_var, None)
            else:
                os.environ[env_var] = value

        self._env_vars_to_restore.clear()

    def create(self, python, *, allow_system_packages=False):
        command = [
            os.environ.get("HATCH_UV", "uv"),
            "venv",
            str(self.directory),
            "--seed",  # seed virtual env with pip for compatibility `hatch.cli:ensure_environment_plugin_dependencies`
            "--python",
            python,
        ]
        if allow_system_packages:
            command.append("--system-site-packages")

        add_verbosity_flag(command, self.verbosity, adjustment=-1)
        self.platform.run_command(command)

    def remove(self):
        self.directory.remove()

    def exists(self):
        return self.directory.is_dir()

    @property
    def executables_directory(self):
        if self._executables_directory is None:
            exe_dir = self.directory / ("Scripts" if self.platform.windows else "bin")
            if exe_dir.is_dir():
                self._executables_directory = exe_dir
            # PyPy
            elif self.platform.windows:
                exe_dir = self.directory / "bin"
                if exe_dir.is_dir():
                    self._executables_directory = exe_dir
                else:
                    msg = f"Unable to locate executables directory within: {self.directory}"
                    raise OSError(msg)
            # Debian
            elif (self.directory / "local").is_dir():  # no cov
                exe_dir = self.directory / "local" / "bin"
                if exe_dir.is_dir():
                    self._executables_directory = exe_dir
                else:
                    msg = f"Unable to locate executables directory within: {self.directory}"
                    raise OSError(msg)
            else:
                msg = f"Unable to locate executables directory within: {self.directory}"
                raise OSError(msg)

        return self._executables_directory

    @property
    def environment(self):
        return self.python_info.environment

    @property
    def sys_path(self):
        return self.python_info.sys_path

    def __enter__(self):
        self.activate()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.deactivate()
