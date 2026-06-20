from hatch_uvenv.hooks import hatch_register_environment
from hatch_uvenv.plugin import UVVirtualEnvironmentPlugin


def test_register_returns_plugin():
    assert hatch_register_environment() is UVVirtualEnvironmentPlugin


def test_plugin_name():
    assert UVVirtualEnvironmentPlugin.PLUGIN_NAME == "uvenv"
