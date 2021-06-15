# Copyright 2020-2021 Canonical Ltd.
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

import pytest
import yaml

from charmcraft import __version__, config
from charmcraft.commands.build import DEFAULT_BASES_CONFIGURATION
from charmcraft.manifest import create_manifest
from charmcraft.cmdbase import CommandError
from charmcraft.utils import (
    get_host_architecture,
)


def test_manifest_simple_ok(tmp_path):
    """Simple construct."""
    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    result_filepath = create_manifest(tmp_path, tstamp, DEFAULT_BASES_CONFIGURATION)

    assert result_filepath == tmp_path / "manifest.yaml"
    saved = yaml.safe_load(result_filepath.read_text())
    expected = {
        "charmcraft-started-at": "2020-02-01T15:40:33Z",
        "charmcraft-version": __version__,
        "bases": [
            {
                "name": "ubuntu",
                "channel": "20.04",
                "architectures": [get_host_architecture()],
            }
        ],
    }
    assert saved == expected


def test_manifest_dont_overwrite(tmp_path):
    """Don't overwrite the already-existing file."""
    (tmp_path / "manifest.yaml").touch()
    with pytest.raises(CommandError) as cm:
        create_manifest(tmp_path, datetime.datetime.now(), DEFAULT_BASES_CONFIGURATION)
    assert str(cm.value) == (
        "Cannot write the manifest as there is already a 'manifest.yaml' in disk."
    )


def test_manifest_using_bases_configuration(tmp_path):
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

    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    result_filepath = create_manifest(tmp_path, tstamp, bases_config)

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
    }
    assert saved == expected
