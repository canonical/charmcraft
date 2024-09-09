# Copyright 2021 Canonical Ltd.
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

import pathlib

import pytest

from charmcraft import const, env


def test_get_managed_environment_home_path():
    dirpath = env.get_managed_environment_home_path()

    assert dirpath == pathlib.Path("/root")


def test_get_managed_environment_log_path():
    dirpath = env.get_managed_environment_log_path()

    assert dirpath == pathlib.Path("/tmp/charmcraft.log")


def test_get_managed_environment_project_path():
    dirpath = env.get_managed_environment_project_path()

    assert dirpath == pathlib.Path("/root/project")


@pytest.mark.parametrize(
    ("snap_name", "snap", "result"),
    [
        (None, None, False),
        (None, "/snap/charmcraft/x1", False),
        ("charmcraft", None, False),
        ("charmcraft", "/snap/charmcraft/x1", True),
    ],
)
def test_is_charmcraft_running_from_snap(monkeypatch, snap_name, snap, result):
    if snap_name is None:
        monkeypatch.delenv("SNAP_NAME", raising=False)
    else:
        monkeypatch.setenv("SNAP_NAME", snap_name)

    if snap is None:
        monkeypatch.delenv("SNAP", raising=False)
    else:
        monkeypatch.setenv("SNAP", snap)

    assert env.is_charmcraft_running_from_snap() == result


@pytest.mark.parametrize(
    ("managed", "result"),
    [
        (None, False),
        ("y", True),
        ("n", False),
        ("1", True),
        ("0", False),
    ],
)
def test_is_charmcraft_running_in_managed_mode(monkeypatch, managed, result):
    if managed is None:
        monkeypatch.delenv(const.MANAGED_MODE_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(const.MANAGED_MODE_ENV_VAR, managed)

    assert env.is_charmcraft_running_in_managed_mode() == result
