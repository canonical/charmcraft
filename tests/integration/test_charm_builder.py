# Copyright 2024 Canonical Ltd.
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
"""Integration tests for CharmBuilder."""


import pathlib
import sys

import pytest

from charmcraft import charm_builder

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="The charm builder only runs in managed mode."
)


@pytest.mark.parametrize(
    "requirements",
    [
        ["ops==2.15.0"],  # Requires pyyaml and websocket-client
    ],
)
def test_install_strict_dependencies_pip_check_error(
    monkeypatch, new_path: pathlib.Path, requirements: list[str]
):
    build_dir = new_path / "build"
    install_dir = new_path / "install"
    entrypoint = build_dir / "entrypoint.py"

    build_dir.mkdir()
    install_dir.mkdir()
    monkeypatch.chdir(build_dir)

    requirements_file = build_dir / "requirements.txt"
    requirements_file.write_text("\n".join(requirements))

    builder = charm_builder.CharmBuilder(
        builddir=build_dir,
        installdir=install_dir,
        entrypoint=entrypoint,
        requirements=[requirements_file],
        strict_dependencies=True,
    )

    with pytest.raises(RuntimeError, match="failed with retcode 1"):
        builder.handle_dependencies()


@pytest.mark.parametrize(
    "requirements",
    [
        ["distro==1.9.0"],  # No dependencies
    ],
)
def test_install_strict_dependencies_pip_check_success(
    monkeypatch, new_path: pathlib.Path, requirements: list[str]
):
    build_dir = new_path / "build"
    install_dir = new_path / "install"
    entrypoint = build_dir / "entrypoint.py"

    build_dir.mkdir()
    install_dir.mkdir()
    monkeypatch.chdir(build_dir)

    requirements_file = build_dir / "requirements.txt"
    requirements_file.write_text("\n".join(requirements))

    builder = charm_builder.CharmBuilder(
        builddir=build_dir,
        installdir=install_dir,
        entrypoint=entrypoint,
        requirements=[requirements_file],
        strict_dependencies=True,
    )

    builder.handle_dependencies()
