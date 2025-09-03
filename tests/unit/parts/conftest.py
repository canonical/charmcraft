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
import pathlib

import pytest


@pytest.fixture
def build_path(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "parts" / "foo" / "build"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def install_path(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "parts" / "foo" / "install"
    path.mkdir(parents=True)
    return path
