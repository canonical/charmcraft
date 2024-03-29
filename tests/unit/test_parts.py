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

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from charmcraft import parts

FULLY_DEFINED_STRICT_CHARM = {
    "source": ".",
    "plugin": "charm",
    "charm-strict-dependencies": True,
    "charm-binary-python-packages": [],
    "charm-python-packages": [],
    "charm-requirements": [],
    "charm-entrypoint": "src/charm.py",
}
MINIMAL_STRICT_CHARM = {
    "source": ".",
    "plugin": "charm",
    "charm-strict-dependencies": True,
}


@pytest.mark.parametrize(
    ("part_config", "expected"),
    [
        ({}, {"charm-requirements": ["requirements.txt"]}),
        (
            {"charm-requirements": ["requirements.txt"]},
            {"charm-requirements": ["requirements.txt"]},
        ),
        (
            {"charm-requirements": ["requirements.txt"], "charm-binary-python-packages": ["ops"]},
            {"charm-requirements": ["requirements.txt"], "charm-binary-python-packages": ["ops"]},
        ),
    ],
)
def test_partconfig_strict_dependencies_success(fs: FakeFilesystem, part_config, expected):
    """Test various success scenarios for a charm part with strict dependencies."""
    for file in part_config.get("charm-requirements", ["requirements.txt"]):
        fs.create_file(file, contents="ops~=2.5")

    part_config.update(MINIMAL_STRICT_CHARM)
    real_expected = FULLY_DEFINED_STRICT_CHARM.copy()
    real_expected.update(expected)

    actual = parts.process_part_config(part_config)

    assert actual == real_expected


@pytest.mark.parametrize(
    ("part_config", "message"),
    [
        (
            {"charm-requirements": ["req.txt"], "charm-python-packages": ["ops"]},
            "'charm-python-packages' must not be set if 'charm-strict-dependencies' is enabled",
        ),
        (
            {"charm-requirements": ["req.txt"], "charm-binary-python-packages": ["not-here"]},
            "All dependencies must be specified in requirements files for strict dependencies.",
        ),
        (
            {"charm-requirements": ["req.txt"], "charm-binary-python-packages": ["ops>=2.6"]},
            "'charm-binary-python-packages' may contain only package names allowed to be "
            "installed from binary if 'charm-strict-dependencies' is enabled. Invalid "
            "package names: ['ops>=2.6']",
        ),
        ({}, "'charm-strict-dependencies' requires at least one requirements file."),
    ],
)
def test_partconfig_strict_dependencies_failure(fs: FakeFilesystem, part_config, message):
    """Test failure scenarios for a charm part with strict dependencies."""
    for file in part_config.get("charm-requirements", []):
        fs.create_file(file, contents="ops==2.5.1\n")

    part_config.update(MINIMAL_STRICT_CHARM)

    with pytest.raises(Exception) as exc_info:
        parts.process_part_config(part_config)

    assert message in {e["msg"] for e in exc_info.value.errors()}
