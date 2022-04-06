# Copyright 2020-2022 Canonical Ltd.
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

import datetime
import json
from unittest.mock import patch

import pytest
import yaml
from craft_cli import CraftError

from charmcraft import __version__, config, linters
from charmcraft.manifest import create_manifest, IMAGE_INFO_ENV_VAR
from charmcraft.utils import OSPlatform


def test_manifest_simple_ok(tmp_path):
    """Simple construct."""
    bases_config = config.BasesConfiguration(
        **{
            "build-on": [
                config.Base(
                    name="test-name",
                    channel="test-channel",
                ),
            ],
            "run-on": [
                config.Base(
                    name="test-name",
                    channel="test-channel",
                    architectures=["arch1"],
                ),
                config.Base(
                    name="test-name2",
                    channel="test-channel2",
                    architectures=["arch1", "arch2"],
                ),
            ],
        }
    )

    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="check-result",
        ),
    ]

    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    os_platform = OSPlatform(system="SuperUbuntu", release="40.10", machine="SomeRISC")
    with patch("charmcraft.utils.get_os_platform", return_value=os_platform):
        result_filepath = create_manifest(tmp_path, tstamp, bases_config, linting_results)

    assert result_filepath == tmp_path / "manifest.yaml"
    saved = yaml.safe_load(result_filepath.read_text())
    expected = {
        "charmcraft-started-at": "2020-02-01T15:40:33Z",
        "charmcraft-version": __version__,
        "bases": [
            {
                "name": "test-name",
                "channel": "test-channel",
                "architectures": ["arch1"],
            },
            {
                "name": "test-name2",
                "channel": "test-channel2",
                "architectures": ["arch1", "arch2"],
            },
        ],
        "analysis": {
            "attributes": [
                {
                    "name": "check-name",
                    "result": "check-result",
                },
            ],
        },
    }
    assert saved == expected


def test_manifest_no_bases(tmp_path):
    """Manifest without bases (used for bundles)."""
    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    os_platform = OSPlatform(system="SuperUbuntu", release="40.10", machine="SomeRISC")
    with patch("charmcraft.utils.get_os_platform", return_value=os_platform):
        result_filepath = create_manifest(tmp_path, tstamp, None, [])

    saved = yaml.safe_load(result_filepath.read_text())

    assert result_filepath == tmp_path / "manifest.yaml"
    assert saved == {
        "charmcraft-started-at": "2020-02-01T15:40:33Z",
        "charmcraft-version": __version__,
        "analysis": {"attributes": []},
    }


def test_manifest_checkers_multiple(tmp_path):
    """Multiple checkers, attributes and a linter."""
    linting_results = [
        linters.CheckResult(
            name="attrib-name-1",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="result-1",
        ),
        linters.CheckResult(
            name="attrib-name-2",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="result-2",
        ),
        linters.CheckResult(
            name="warning-name",
            check_type=linters.CheckType.lint,
            url="url",
            text="text",
            result="result",
        ),
    ]

    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    os_platform = OSPlatform(system="SuperUbuntu", release="40.10", machine="SomeRISC")
    with patch("charmcraft.utils.get_os_platform", return_value=os_platform):
        result_filepath = create_manifest(tmp_path, tstamp, None, linting_results)

    assert result_filepath == tmp_path / "manifest.yaml"
    saved = yaml.safe_load(result_filepath.read_text())
    expected = [
        {
            "name": "attrib-name-1",
            "result": "result-1",
        },
        {
            "name": "attrib-name-2",
            "result": "result-2",
        },
    ]
    assert saved["analysis"]["attributes"] == expected


def test_manifest_image_info_ok(tmp_path, monkeypatch):
    """Include the image info in the manifest."""
    test_image_content = {"some info": ["whatever", 123]}
    monkeypatch.setenv(IMAGE_INFO_ENV_VAR, json.dumps(test_image_content))

    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    os_platform = OSPlatform(system="SuperUbuntu", release="40.10", machine="SomeRISC")
    with patch("charmcraft.utils.get_os_platform", return_value=os_platform):
        result_filepath = create_manifest(tmp_path, tstamp, None, [])

    saved = yaml.safe_load(result_filepath.read_text())
    assert saved["image-info"] == test_image_content


def test_manifest_image_info_bad(tmp_path, monkeypatch):
    """The format of the image info environment variable is wrong."""
    monkeypatch.setenv(IMAGE_INFO_ENV_VAR, "this is not a json")
    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    with pytest.raises(CraftError) as cm:
        create_manifest(tmp_path, tstamp, None, [])
    exc = cm.value
    assert str(exc) == "Failed to parse the content of CHARMCRAFT_IMAGE_INFO environment variable"
    assert isinstance(exc.__cause__, json.JSONDecodeError)
