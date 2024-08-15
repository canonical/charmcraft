# Copyright 2020-2023 Canonical Ltd.
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

import sys

import pydantic
import pytest

from charmcraft import parts

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
# -- tests for part config processing


@pytest.mark.usefixtures("new_path")
@pytest.mark.parametrize(
    "binary_packages",
    [
        {},
        {"charm-binary-python-packages": ["pydantic-core"]},
    ],
)
@pytest.mark.parametrize("packages", [{}, {"charm-python-packages": ["pytest"]}])
@pytest.mark.parametrize("reqs", [{}, {"charm-requirements": ["requirements.lock"]}])
@pytest.mark.parametrize("strict_deps", [{}, {"charm-strict-dependencies": False}])
@pytest.mark.parametrize("entrypoint", [{}, {"charm-entrypoint": "my_charm.py"}])
def test_partconfig_happy_validation_and_completion(
    binary_packages: dict[str, str],
    packages: dict[str, str],
    reqs: dict[str, str],
    strict_deps: dict[str, bool],
    entrypoint: dict[str, str],
):
    data: dict[str, str | bool] = {
        "plugin": "charm",
        "source": ".",
    }
    data.update(binary_packages)
    data.update(packages)
    data.update(strict_deps)
    data.update(entrypoint)

    completed = parts.process_part_config(data)
    assert completed == data


def test_partconfig_no_plugin():
    data = {
        "source": ".",
    }
    with pytest.raises(ValueError) as raised:
        parts.process_part_config(data)
    assert str(raised.value) == "'plugin' not defined"


def test_partconfig_bad_property():
    data = {
        "plugin": "charm",
        "source": ".",
        "color": "purple",
    }
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.process_part_config(data)
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("color",)
    assert err[0]["msg"] == "Extra inputs are not permitted"


def test_partconfig_bad_plugin_property():
    data = {
        "plugin": "charm",
        "charm-timeout": "never",
        "source": ".",
    }
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.process_part_config(data)
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("charm-timeout",)
    assert err[0]["msg"] == "Extra inputs are not permitted"
