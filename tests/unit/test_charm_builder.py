# Copyright 2023-2024 Canonical Ltd.
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
"""Unit tests for CharmBuilder."""
import pathlib

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_subprocess import FakeProcess

from charmcraft import charm_builder, const, errors, utils

pytestmark = [
    # Always use pyfakefs and pytest-subprocess
    pytest.mark.usefixtures("fs", "fake_process")
]

REQUIREMENTS_FILES = [pytest.param("", id="empty"), "ops~=2.5", "requests\nops"]


@pytest.fixture
def builder(fs: FakeFilesystem) -> charm_builder.CharmBuilder:
    fs.cwd = "/root"
    fs.makedirs(const.BUILD_DIRNAME)
    fs.makedirs("install")
    charm_file = fs.create_file("src/charm.py")

    return charm_builder.CharmBuilder(
        builddir=pathlib.Path(const.BUILD_DIRNAME),
        installdir=pathlib.Path("install"),
        entrypoint=charm_file.path,
        requirements=[pathlib.Path("requirements.txt")],
    )


@pytest.mark.usefixtures("fake_process")
@pytest.mark.parametrize(
    ("requirements", "python_packages", "binary_python_packages"),
    [
        pytest.param("", ["yolo"], [], id="empty-requirements"),
    ],
)
def test_install_strict_dependencies_validation_error(
    fs: FakeFilesystem, builder, requirements, python_packages, binary_python_packages
):
    fs.create_file("requirements.txt", contents=requirements)
    builder.strict_dependencies = True
    builder.python_packages = python_packages
    builder.binary_python_packages = binary_python_packages

    with pytest.raises(errors.DependencyError):
        builder._install_strict_dependencies("pip")


@pytest.mark.usefixtures("fake_process")
def test_install_strict_dependencies_no_requirement_paths(builder):
    builder.requirement_paths = []

    with pytest.raises(errors.DependencyError):
        builder._install_strict_dependencies("pip")


@pytest.mark.parametrize("requirements", REQUIREMENTS_FILES)
def test_install_strict_dependencies_pip_failure(
    fs, fake_process: FakeProcess, builder, requirements
):
    fs.create_file("requirements.txt", contents=requirements)
    no_binary_packages = utils.get_package_names(requirements.splitlines(keepends=False))
    no_binary_packages_str = ",".join(sorted(no_binary_packages))
    fake_process.register(
        [
            "/pip",
            "install",
            *([f"--no-binary={no_binary_packages_str}"] if no_binary_packages else []),
            "--requirement=requirements.txt",
        ],
        returncode=1,
    )

    with pytest.raises(RuntimeError):
        builder._install_strict_dependencies("/pip")


@pytest.mark.parametrize("requirements", REQUIREMENTS_FILES)
def test_install_strict_dependencies_success(
    fs: FakeFilesystem, fake_process: FakeProcess, builder, requirements
):
    fs.create_file("requirements.txt", contents=requirements)
    expected_command = [
        "/pip",
        "install",
        "--no-deps",
        "--no-binary=:all:",
        "--requirement=requirements.txt",
    ]
    install_cmd = fake_process.register(expected_command, returncode=0)
    check_cmd = fake_process.register(["/pip", "check"], returncode=0)

    builder._install_strict_dependencies("/pip")

    assert install_cmd.call_count() == 1
    assert check_cmd.call_count() == 1
