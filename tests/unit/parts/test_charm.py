# Copyright 2023 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft
"""Unit tests for charm plugin."""
import pathlib
import sys
from unittest.mock import patch

import pydantic
import pytest
from craft_parts import Step

from charmcraft import charm_builder, env, parts

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows not supported")


def test_charmplugin_get_build_package_deb_based(charm_plugin):
    with patch("craft_parts.utils.os_utils.OsRelease.id") as mock_id:
        mock_id.return_value = "ubuntu"

        assert charm_plugin.get_build_packages() == {
            "python3-pip",
            "python3-setuptools",
            "python3-wheel",
            "python3-venv",
            "python3-dev",
            "libyaml-dev",
        }


def test_charmplugin_get_build_package_yum_based(charm_plugin):
    with patch("craft_parts.utils.os_utils.OsRelease.id") as mock_id:
        mock_id.return_value = "centos"

        assert charm_plugin.get_build_packages() == {
            "autoconf",
            "automake",
            "gcc",
            "gcc-c++",
            "git",
            "make",
            "patch",
            "python3-devel",
            "python3-pip",
            "python3-setuptools",
            "python3-wheel",
        }


def test_charmplugin_get_build_package_centos7(charm_plugin):
    with patch("craft_parts.utils.os_utils.OsRelease.id") as mock_id:
        with patch("craft_parts.utils.os_utils.OsRelease.version_id") as mock_version:
            mock_id.return_value = "centos"
            mock_version.return_value = "7"

            assert charm_plugin.get_build_packages() == {
                "autoconf",
                "automake",
                "gcc",
                "gcc-c++",
                "git",
                "make",
                "patch",
                "rh-python38-python-devel",
                "rh-python38-python-pip",
                "rh-python38-python-setuptools",
                "rh-python38-python-wheel",
            }


def test_charmplugin_get_build_snaps(charm_plugin):
    assert charm_plugin.get_build_snaps() == set()


def test_charmplugin_get_build_environment_ubuntu(charm_plugin, mocker):
    mock_id = mocker.patch("craft_parts.utils.os_utils.OsRelease.id")
    mock_version = mocker.patch("craft_parts.utils.os_utils.OsRelease.version_id")
    mock_id.return_value = "ubuntu"
    mock_version.return_value = "22.04"
    assert charm_plugin.get_build_environment() == {"CRYPTOGRAPHY_OPENSSL_NO_LEGACY": "true"}


def test_charmplugin_get_build_environment_centos_7(charm_plugin, mocker, monkeypatch):
    monkeypatch.setenv("PATH", "/some/path")
    mock_id = mocker.patch("craft_parts.utils.os_utils.OsRelease.id")
    mock_version = mocker.patch("craft_parts.utils.os_utils.OsRelease.version_id")
    mock_id.return_value = "centos"
    mock_version.return_value = "7"
    assert charm_plugin.get_build_environment() == {
        "CRYPTOGRAPHY_OPENSSL_NO_LEGACY": "true",
        "PATH": "/opt/rh/rh-python38/root/usr/bin:${PATH}",
    }


def test_charmplugin_get_build_commands_ubuntu(charm_plugin, tmp_path, mocker, monkeypatch):
    monkeypatch.setenv("PATH", "/some/path")
    monkeypatch.setenv("SNAP", "snap_value")
    monkeypatch.setenv("SNAP_ARCH", "snap_arch_value")
    monkeypatch.setenv("SNAP_NAME", "snap_name_value")
    monkeypatch.setenv("SNAP_VERSION", "snap_version_value")
    monkeypatch.setenv("http_proxy", "http_proxy_value")
    monkeypatch.setenv("https_proxy", "https_proxy_value")
    monkeypatch.setenv("no_proxy", "no_proxy_value")

    mock_id = mocker.patch("craft_parts.utils.os_utils.OsRelease.id")
    mock_version = mocker.patch("craft_parts.utils.os_utils.OsRelease.version_id")
    mock_register = mocker.patch("craft_parts.callbacks.register_post_step")

    mock_id.return_value = "ubuntu"
    mock_version.return_value = "22.04"

    assert charm_plugin.get_build_commands() == [
        "env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 "
        "CRYPTOGRAPHY_OPENSSL_NO_LEGACY=true "
        "PATH=/some/path SNAP=snap_value "
        "SNAP_ARCH=snap_arch_value SNAP_NAME=snap_name_value "
        "SNAP_VERSION=snap_version_value http_proxy=http_proxy_value "
        "https_proxy=https_proxy_value no_proxy=no_proxy_value "
        f"{sys.executable} -u -I "
        f"{charm_builder.__file__} "
        f"--builddir {str(tmp_path)}/parts/foo/build "
        f"--installdir {str(tmp_path)}/parts/foo/install "
        f"--entrypoint {str(tmp_path)}/parts/foo/build/entrypoint "
        "-p pip "
        "-p setuptools "
        "-p wheel "
        "-b pkg1 "
        "-b pkg2 "
        "-p pkg3 "
        "-p pkg4 "
        "-r reqs1.txt "
        "-r reqs2.txt"
    ]

    # check the callback is properly registered for running own method after build
    mock_register.assert_called_with(charm_plugin.post_build_callback, step_list=[Step.BUILD])


def test_charmplugin_get_build_commands_centos_7(charm_plugin, tmp_path, mocker, monkeypatch):
    monkeypatch.setenv("PATH", "/some/path")
    monkeypatch.setenv("SNAP", "snap_value")
    monkeypatch.setenv("SNAP_ARCH", "snap_arch_value")
    monkeypatch.setenv("SNAP_NAME", "snap_name_value")
    monkeypatch.setenv("SNAP_VERSION", "snap_version_value")
    monkeypatch.setenv("http_proxy", "http_proxy_value")
    monkeypatch.setenv("https_proxy", "https_proxy_value")
    monkeypatch.setenv("no_proxy", "no_proxy_value")

    mock_id = mocker.patch("craft_parts.utils.os_utils.OsRelease.id")
    mock_version = mocker.patch("craft_parts.utils.os_utils.OsRelease.version_id")
    mock_register = mocker.patch("craft_parts.callbacks.register_post_step")

    mock_id.return_value = "centos"
    mock_version.return_value = "7"

    assert charm_plugin.get_build_commands() == [
        "env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 "
        "CRYPTOGRAPHY_OPENSSL_NO_LEGACY=true "
        "PATH=/opt/rh/rh-python38/root/usr/bin:/some/path "
        "SNAP=snap_value SNAP_ARCH=snap_arch_value SNAP_NAME=snap_name_value "
        "SNAP_VERSION=snap_version_value http_proxy=http_proxy_value "
        "https_proxy=https_proxy_value no_proxy=no_proxy_value "
        f"{sys.executable} -u -I "
        f"{charm_builder.__file__} "
        f"--builddir {str(tmp_path)}/parts/foo/build "
        f"--installdir {str(tmp_path)}/parts/foo/install "
        f"--entrypoint {str(tmp_path)}/parts/foo/build/entrypoint "
        "-b pip "
        "-b setuptools "
        "-b wheel "
        "-p pip "
        "-p setuptools "
        "-p wheel "
        "-b pkg1 "
        "-b pkg2 "
        "-p pkg3 "
        "-p pkg4 "
        "-r reqs1.txt "
        "-r reqs2.txt"
    ]

    # check the callback is properly registered for running own method after build
    mock_register.assert_called_with(charm_plugin.post_build_callback, step_list=[Step.BUILD])


def test_charmplugin_post_build_metric_collection(charm_plugin):
    with patch("charmcraft.instrum.merge_from") as mock_collection:
        charm_plugin.post_build_callback("test step info")
    mock_collection.assert_called_with(env.get_charm_builder_metrics_path())


def test_charmpluginproperties_invalid_properties():
    content = {"source": ".", "charm-invalid": True}
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.CharmPlugin.properties_class.unmarshal(content)
    err = raised.value.errors()

    assert len(err) == 1
    assert err[0]["loc"] == ("charm-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_charmpluginproperties_entrypoint_ok():
    """Simple valid entrypoint."""
    content = {"source": ".", "charm-entrypoint": "myep.py"}
    properties = parts.CharmPlugin.properties_class.unmarshal(content)
    assert properties.charm_entrypoint == "myep.py"


def test_charmpluginproperties_entrypoint_default():
    """Specific default if not configured."""
    content = {"source": "."}
    properties = parts.CharmPlugin.properties_class.unmarshal(content)
    assert properties.charm_entrypoint == "src/charm.py"


def test_charmpluginproperties_entrypoint_relative(tmp_path):
    """The configuration is stored relative no matter what."""
    absolute_path = tmp_path / "myep.py"
    content = {"source": str(tmp_path), "charm-entrypoint": str(absolute_path)}
    properties = parts.CharmPlugin.properties_class.unmarshal(content)
    assert properties.charm_entrypoint == "myep.py"


def test_charmpluginproperties_entrypoint_outside_project_absolute(tmp_path):
    """The entrypoint must be inside the project."""
    outside_path = tmp_path.parent / "charm.py"
    content = {"source": str(tmp_path), "charm-entrypoint": str(outside_path)}
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.CharmPlugin.properties_class.unmarshal(content)
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("charm-entrypoint",)
    assert (
        err[0]["msg"]
        == f"Value error, charm entry point must be inside the project: {str(outside_path)!r}"
    )


def test_charmpluginproperties_entrypoint_outside_project_relative(tmp_path):
    """The entrypoint must be inside the project."""
    outside_path = tmp_path.parent / "charm.py"
    content = {"source": str(tmp_path), "charm-entrypoint": "../charm.py"}
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.CharmPlugin.properties_class.unmarshal(content)
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("charm-entrypoint",)
    assert (
        err[0]["msg"]
        == f"Value error, charm entry point must be inside the project: {str(outside_path)!r}"
    )


def test_charmpluginproperties_requirements_default(tmp_path):
    """The configuration is empty by default."""
    content = {"source": str(tmp_path)}
    properties = parts.CharmPlugin.properties_class.unmarshal(content)
    assert properties.charm_requirements == []


def test_charmpluginproperties_requirements_filepresent_ok(tmp_path: pathlib.Path):
    """If a specific file is present in disk it's used."""
    (tmp_path / "requirements.txt").write_text("somedep")
    content = {"source": str(tmp_path)}
    properties = parts.CharmPluginProperties.unmarshal(content)
    assert properties.charm_requirements == ["requirements.txt"]


def test_charmpluginproperties_requirements_filepresent_but_configured(tmp_path):
    """The specific file is present in disk but configuration takes priority."""
    (tmp_path / "requirements.txt").write_text("somedep")
    (tmp_path / "alternative.txt").write_text("somedep")
    content = {"source": str(tmp_path), "charm-requirements": ["alternative.txt"]}
    properties = parts.CharmPlugin.properties_class.unmarshal(content)
    assert properties.charm_requirements == ["alternative.txt"]
