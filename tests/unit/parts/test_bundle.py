import sys

import pydantic
import pytest

import charmcraft.parts


def test_bundleplugin_get_build_package(bundle_plugin):
    assert bundle_plugin.get_build_packages() == set()


def test_bundleplugin_get_build_snaps(bundle_plugin):
    assert bundle_plugin.get_build_snaps() == set()


def test_bundleplugin_get_build_environment(bundle_plugin):
    assert bundle_plugin.get_build_environment() == {}


def test_bundleplugin_get_build_commands(bundle_plugin, tmp_path):
    if sys.platform == "linux":
        assert bundle_plugin.get_build_commands() == [
            f'mkdir -p "{str(tmp_path)}/parts/foo/install"',
            f'cp --archive --link --no-dereference * "{str(tmp_path)}/parts/foo/install"',
        ]
    else:
        assert bundle_plugin.get_build_commands() == [
            f'mkdir -p "{str(tmp_path)}/parts/foo/install"',
            f'cp -R -p -P * "{str(tmp_path)}/parts/foo/install"',
        ]


def test_bundleplugin_invalid_properties():
    with pytest.raises(pydantic.ValidationError) as raised:
        charmcraft.parts.bundle.BundlePlugin.properties_class.unmarshal(
            {"source": ".", "bundle-invalid": True}
        )
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("bundle-invalid",)
    assert err[0]["type"] == "value_error.extra"
