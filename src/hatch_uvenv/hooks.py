from hatchling.plugin import hookimpl

from hatch_uvenv.plugin import UVVirtualEnvironmentPlugin


@hookimpl
def hatch_register_environment():
    return UVVirtualEnvironmentPlugin
