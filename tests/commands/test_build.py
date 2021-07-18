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

import logging
import os
import pathlib
import re
import subprocess
import sys
import zipfile
from collections import namedtuple
from textwrap import dedent
from typing import List
from unittest.mock import call, patch

import pytest
import yaml

from charmcraft import charm_builder, linters
from charmcraft.bases import get_host_as_base
from charmcraft.cmdbase import CommandError
from charmcraft.commands.build import (
    BUILD_DIRNAME,
    DISPATCH_CONTENT,
    Builder,
    Validator,
    format_charm_file_name,
    polite_exec,
    relativise,
)
from charmcraft.config import Base, BasesConfiguration, load
from charmcraft.logsetup import message_handler
from charmcraft.metadata import CHARM_METADATA


@pytest.fixture
def basic_project(tmp_path):
    """Create a basic Charmcraft project."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # the metadata
    metadata_data = {"name": "name-from-metadata"}
    metadata_file = tmp_path / "metadata.yaml"
    metadata_raw = yaml.dump(metadata_data).encode("ascii")
    metadata_file.write_bytes(metadata_raw)

    # a lib dir
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    ops_lib_dir = lib_dir / "ops"
    ops_lib_dir.mkdir()
    ops_stuff = ops_lib_dir / "stuff.txt"
    ops_stuff.write_bytes(b"ops stuff")

    # simple source code
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    charm_script = src_dir / "charm.py"
    charm_script.write_bytes(b"all the magic")

    yield tmp_path


@pytest.fixture
def basic_project_builder(basic_project):
    def _basic_project_builder(bases_configs: List[BasesConfiguration]):
        charmcraft_file = basic_project / "charmcraft.yaml"
        with charmcraft_file.open("w") as f:
            print("type: charm", file=f)
            print("bases:", file=f)
            for bases_config in bases_configs:
                print("- build-on:", file=f)
                for base in bases_config.build_on:
                    print(f"  - name: {base.name!r}", file=f)
                    print(f"    channel: {base.channel!r}", file=f)
                    print(f"    architectures: {base.architectures!r}", file=f)

                print("  run-on:", file=f)
                for base in bases_config.run_on:
                    print(f"  - name: {base.name!r}", file=f)
                    print(f"    channel: {base.channel!r}", file=f)
                    print(f"    architectures: {base.architectures!r}", file=f)

        config = load(basic_project)
        return Builder(
            {
                "from": basic_project,
                "entrypoint": basic_project / "src" / "charm.py",
                "requirement": [],
            },
            config,
        )

    return _basic_project_builder


@pytest.fixture
def mock_capture_logs_from_instance():
    with patch("charmcraft.commands.build.capture_logs_from_instance") as mock_capture:
        yield mock_capture


@pytest.fixture(autouse=True)
def mock_ensure_provider_is_available():
    with patch("charmcraft.commands.build.ensure_provider_is_available") as mock_ensure:
        yield mock_ensure


# --- Validator tests


def test_validator_process_simple(config):
    """Process the present options and store the result."""

    class TestValidator(Validator):
        _options = ["foo", "bar"]

        def validate_foo(self, arg):
            assert arg == 35
            return 70

        def validate_bar(self, arg):
            assert arg == 45
            return 80

    test_args = namedtuple("T", "foo bar")(35, 45)
    validator = TestValidator(config)
    result = validator.process(test_args)
    assert result == dict(foo=70, bar=80)


def test_validator_process_notpresent(config):
    """Process an option after not finding the value."""

    class TestValidator(Validator):
        _options = ["foo"]

        def validate_foo(self, arg):
            assert arg is None
            return 70

    test_args = namedtuple("T", "bar")(35)
    validator = TestValidator(config)
    result = validator.process(test_args)
    assert result == dict(foo=70)


def test_validator_from_simple(tmp_path, config):
    """'from' param: simple validation and setting in Validation."""
    validator = Validator(config)
    resp = validator.validate_from(tmp_path)
    assert resp == tmp_path
    assert validator.basedir == tmp_path


def test_validator_from_default(config):
    """'from' param: default value."""
    validator = Validator(config)
    resp = validator.validate_from(None)
    assert resp == pathlib.Path(".").absolute()


def test_validator_from_absolutized(tmp_path, monkeypatch, config):
    """'from' param: check it's made absolute."""
    # change dir to the temp one, where we will have the 'dir1/dir2' tree
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir2 = dir1 / "dir2"
    dir2.mkdir()
    monkeypatch.chdir(tmp_path)

    validator = Validator(config)
    resp = validator.validate_from(pathlib.Path("dir1/dir2"))
    assert resp == dir2


def test_validator_from_expanded(config):
    """'from' param: expands the user-home prefix."""
    validator = Validator(config)
    resp = validator.validate_from(pathlib.Path("~"))
    assert resp == pathlib.Path.home()


def test_validator_from_exist(config):
    """'from' param: checks that the directory exists."""
    validator = Validator(config)
    expected_msg = "Charm directory was not found: '/not_really_there'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_from(pathlib.Path("/not_really_there"))


def test_validator_from_isdir(tmp_path, config):
    """'from' param: checks that the directory is really that."""
    testfile = tmp_path / "testfile"
    testfile.touch()

    validator = Validator(config)
    expected_msg = "Charm directory is not really a directory: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_from(testfile)


@pytest.mark.parametrize("bases_indices", [[-1], [0, -1], [0, 1, -1]])
def test_validator_bases_index_invalid(bases_indices, config):
    """'entrypoint' param: checks that the file exists."""
    config.set(
        bases=[
            BasesConfiguration(
                **{"build-on": [get_host_as_base()], "run-on": [get_host_as_base()]}
            ),
            BasesConfiguration(
                **{"build-on": [get_host_as_base()], "run-on": [get_host_as_base()]}
            ),
        ]
    )
    validator = Validator(config)
    expected_msg = re.escape("Bases index '-1' is invalid (must be >= 0).")
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_bases_indices(bases_indices)


def test_validator_entrypoint_simple(tmp_path, config):
    """'entrypoint' param: simple validation."""
    testfile = tmp_path / "testfile"
    testfile.touch(mode=0o777)

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(testfile)
    assert resp == testfile


def test_validator_entrypoint_default(tmp_path, config):
    """'entrypoint' param: default value."""
    default_entrypoint = tmp_path / "src" / "charm.py"
    default_entrypoint.parent.mkdir()
    default_entrypoint.touch(mode=0o777)

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(None)
    assert resp == default_entrypoint


def test_validator_entrypoint_absolutized(tmp_path, monkeypatch, config):
    """'entrypoint' param: check it's made absolute."""
    # change dir to the temp one, where we will have the 'dirX/file.py' stuff
    dirx = tmp_path / "dirX"
    dirx.mkdir()
    testfile = dirx / "file.py"
    testfile.touch(mode=0o777)
    monkeypatch.chdir(tmp_path)

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(pathlib.Path("dirX/file.py"))
    assert resp == testfile


def test_validator_entrypoint_expanded(tmp_path, config):
    """'entrypoint' param: expands the user-home prefix."""
    fake_home = tmp_path / "homedir"
    fake_home.mkdir()

    testfile = fake_home / "testfile"
    testfile.touch(mode=0o777)

    validator = Validator(config)
    validator.basedir = tmp_path

    with patch.dict(os.environ, {"HOME": str(fake_home)}):
        resp = validator.validate_entrypoint(pathlib.Path("~/testfile"))
    assert resp == testfile


def test_validator_entrypoint_exist(config):
    """'entrypoint' param: checks that the file exists."""
    validator = Validator(config)
    expected_msg = "Charm entry point was not found: '/not_really_there.py'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(pathlib.Path("/not_really_there.py"))


def test_validator_entrypoint_inside_project(tmp_path, config):
    """'entrypoint' param: checks that it's part of the project."""
    project_dir = tmp_path / "test-project"
    testfile = tmp_path / "testfile"
    testfile.touch(mode=0o777)

    validator = Validator(config)
    validator.basedir = project_dir

    expected_msg = "Charm entry point must be inside the project: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(testfile)


def test_validator_entrypoint_exec(tmp_path, config):
    """'entrypoint' param: checks that the file is executable."""
    testfile = tmp_path / "testfile"
    testfile.touch(mode=0o444)

    validator = Validator(config)
    validator.basedir = tmp_path
    expected_msg = "Charm entry point must be executable: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(testfile)


def test_validator_requirement_simple(tmp_path, config):
    """'requirement' param: simple validation."""
    testfile = tmp_path / "testfile"
    testfile.touch()

    validator = Validator(config)
    resp = validator.validate_requirement([testfile])
    assert resp == [testfile]


def test_validator_requirement_multiple(tmp_path, config):
    """'requirement' param: multiple files."""
    testfile1 = tmp_path / "testfile1"
    testfile1.touch()
    testfile2 = tmp_path / "testfile2"
    testfile2.touch()

    validator = Validator(config)
    resp = validator.validate_requirement([testfile1, testfile2])
    assert resp == [testfile1, testfile2]


def test_validator_requirement_default_present_ok(tmp_path, config):
    """'requirement' param: default value when a requirements.txt is there and readable."""
    default_requirement = tmp_path / "requirements.txt"
    default_requirement.touch()

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == [default_requirement]


def test_validator_requirement_default_present_not_readable(tmp_path, config):
    """'requirement' param: default value when a requirements.txt is there but not readable."""
    default_requirement = tmp_path / "requirements.txt"
    default_requirement.touch(0o230)

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == []


def test_validator_requirement_default_missing(tmp_path, config):
    """'requirement' param: default value when no requirements.txt is there."""
    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == []


def test_validator_requirement_absolutized(tmp_path, monkeypatch, config):
    """'requirement' param: check it's made absolute."""
    # change dir to the temp one, where we will have the reqs file
    testfile = tmp_path / "reqs.txt"
    testfile.touch()
    monkeypatch.chdir(tmp_path)

    validator = Validator(config)
    resp = validator.validate_requirement([pathlib.Path("reqs.txt")])
    assert resp == [testfile]


def test_validator_requirement_expanded(tmp_path, config):
    """'requirement' param: expands the user-home prefix."""
    fake_home = tmp_path / "homedir"
    fake_home.mkdir()

    requirement = fake_home / "requirements.txt"
    requirement.touch(0o230)

    validator = Validator(config)

    with patch.dict(os.environ, {"HOME": str(fake_home)}):
        resp = validator.validate_requirement([pathlib.Path("~/requirements.txt")])
    assert resp == [requirement]


def test_validator_requirement_exist(config):
    """'requirement' param: checks that the file exists."""
    validator = Validator(config)
    expected_msg = "the requirements file was not found: '/not_really_there.txt'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_requirement([pathlib.Path("/not_really_there.txt")])


# --- Polite Executor tests


def test_politeexec_base(caplog):
    """Basic execution."""
    caplog.set_level(logging.ERROR, logger="charmcraft")

    cmd = ["echo", "HELO"]
    retcode = polite_exec(cmd)
    assert retcode == 0
    assert not caplog.records


def test_politeexec_stdout_logged(caplog):
    """The standard output is logged in debug."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    cmd = ["echo", "HELO"]
    polite_exec(cmd)
    expected = [
        "Running external command ['echo', 'HELO']",
        ":: HELO",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_politeexec_stderr_logged(caplog):
    """The standard error is logged in debug."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    cmd = [sys.executable, "-c", "import sys; print('weird, huh?', file=sys.stderr)"]
    polite_exec(cmd)
    expected = [
        "Running external command " + str(cmd),
        ":: weird, huh?",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_politeexec_failed(caplog):
    """It's logged in error if cmd fails."""
    caplog.set_level(logging.ERROR, logger="charmcraft")

    cmd = [sys.executable, "-c", "exit(3)"]
    retcode = polite_exec(cmd)
    assert retcode == 3
    expected_msg = "Executing {} failed with return code 3".format(cmd)
    assert any(expected_msg in rec.message for rec in caplog.records)


def test_politeexec_crashed(caplog, tmp_path):
    """It's logged in error if cmd fails."""
    caplog.set_level(logging.ERROR, logger="charmcraft")
    nonexistent = tmp_path / "whatever"

    cmd = [str(nonexistent)]
    retcode = polite_exec(cmd)
    assert retcode == 1
    expected_msg = "Executing {} crashed with FileNotFoundError".format(cmd)
    assert any(expected_msg in rec.message for rec in caplog.records)


# --- (real) build tests


def test_build_basic_complete_structure(basic_project, caplog, monkeypatch, config):
    """Integration test: a simple structure with custom lib and normal src dir."""
    caplog.set_level(logging.WARNING, logger="charmcraft")
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    monkeypatch.chdir(basic_project)  # so the zip file is left in the temp dir
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    # save original metadata and verify later
    metadata_file = basic_project / "metadata.yaml"
    metadata_raw = metadata_file.read_bytes()

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch(
        "charmcraft.commands.build.check_if_base_matches_host",
        return_value=(True, None),
    ):
        zipnames = builder.run()

    assert zipnames == [f"name-from-metadata_ubuntu-20.04-{host_arch}.charm"]

    # check all is properly inside the zip
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipnames[0])
    assert zf.read("metadata.yaml") == metadata_raw
    assert zf.read("src/charm.py") == b"all the magic"
    dispatch = DISPATCH_CONTENT.format(entrypoint_relative_path="src/charm.py").encode(
        "ascii"
    )
    assert zf.read("dispatch") == dispatch
    assert zf.read("hooks/install") == dispatch
    assert zf.read("hooks/start") == dispatch
    assert zf.read("hooks/upgrade-charm") == dispatch
    assert zf.read("lib/ops/stuff.txt") == b"ops stuff"

    # check the manifest is present and with particular values that depend on given info
    manifest = yaml.safe_load(zf.read("manifest.yaml"))
    assert (
        manifest["charmcraft-started-at"] == config.project.started_at.isoformat() + "Z"
    )
    assert caplog.records == []


def test_build_error_without_metadata_yaml(basic_project, monkeypatch):
    """Validate error if trying to build project without metadata.yaml."""
    metadata = basic_project / CHARM_METADATA
    metadata.unlink()

    config = load(basic_project)
    monkeypatch.chdir(basic_project)

    with pytest.raises(CommandError, match=r"Missing mandatory metadata.yaml."):
        Builder(
            {
                "from": basic_project,
                "entrypoint": basic_project / "src" / "charm.py",
                "requirement": [],
            },
            config,
        )


def test_build_with_charmcraft_yaml_destructive_mode(
    basic_project_builder, caplog, monkeypatch
):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})]
    )

    zipnames = builder.run(destructive_mode=True)

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm"
    ]

    records = [r.message for r in caplog.records]
    assert "Building for 'bases[0]' as host matches 'build-on[0]'." in records


def test_build_with_charmcraft_yaml_managed_mode(
    basic_project_builder, caplog, monkeypatch
):
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})]
    )

    zipnames = builder.run()

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm"
    ]

    records = [r.message for r in caplog.records]
    assert "Building for 'bases[0]' as host matches 'build-on[0]'." in records


def test_build_checks_provider(basic_project, mock_ensure_provider_is_available):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    with patch("charmcraft.commands.build.launched_environment"):
        builder.run()

    mock_ensure_provider_is_available.assert_called_once()


def test_build_checks_provider_error(basic_project, mock_ensure_provider_is_available):
    """Test cases for base-index parameter."""
    mock_ensure_provider_is_available.side_effect = RuntimeError("foo")
    config = load(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    with pytest.raises(RuntimeError, match="foo"):
        builder.run()

    mock_ensure_provider_is_available.assert_called_once()


def test_build_without_charmcraft_yaml_issues_dn02(basic_project, caplog, monkeypatch):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    with patch("charmcraft.commands.build.launched_environment"):
        builder.run()

    assert "DEPRECATED: A charmcraft.yaml configuration file is now required." in [
        r.message for r in caplog.records
    ]


def test_build_multiple_with_charmcraft_yaml_destructive_mode(
    basic_project_builder, monkeypatch, caplog
):
    """Build multiple charms for multiple matching bases, skipping one unmatched config."""
    caplog.set_level(logging.DEBUG)
    host_base = get_host_as_base()
    unmatched_base = Base(
        name="unmatched-name",
        channel="unmatched-channel",
        architectures=["unmatched-arch1"],
    )
    matched_cross_base = Base(
        name="cross-name",
        channel="cross-channel",
        architectures=["cross-arch1"],
    )
    builder = basic_project_builder(
        [
            BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]}),
            BasesConfiguration(
                **{"build-on": [unmatched_base], "run-on": [unmatched_base]}
            ),
            BasesConfiguration(
                **{"build-on": [host_base], "run-on": [matched_cross_base]}
            ),
        ]
    )

    zipnames = builder.run(destructive_mode=True)

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm",
        "name-from-metadata_cross-name-cross-channel-cross-arch1.charm",
    ]

    records = [r.message for r in caplog.records]

    assert "Building for 'bases[0]' as host matches 'build-on[0]'." in records
    assert (
        "No suitable 'build-on' environment found in 'bases[1]' configuration."
        in records
    )
    assert "Building for 'bases[2]' as host matches 'build-on[0]'." in records


def test_build_multiple_with_charmcraft_yaml_managed_mode(
    basic_project_builder, monkeypatch, caplog
):
    """Build multiple charms for multiple matching bases, skipping one unmatched config."""
    caplog.set_level(logging.DEBUG)
    host_base = get_host_as_base()
    unmatched_base = Base(
        name="unmatched-name",
        channel="unmatched-channel",
        architectures=["unmatched-arch1"],
    )
    matched_cross_base = Base(
        name="cross-name",
        channel="cross-channel",
        architectures=["cross-arch1"],
    )
    builder = basic_project_builder(
        [
            BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]}),
            BasesConfiguration(
                **{"build-on": [unmatched_base], "run-on": [unmatched_base]}
            ),
            BasesConfiguration(
                **{"build-on": [host_base], "run-on": [matched_cross_base]}
            ),
        ]
    )

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    zipnames = builder.run()

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm",
        "name-from-metadata_cross-name-cross-channel-cross-arch1.charm",
    ]

    records = [r.message for r in caplog.records]

    assert "Building for 'bases[0]' as host matches 'build-on[0]'." in records
    assert (
        "No suitable 'build-on' environment found in 'bases[1]' configuration."
        in records
    )
    assert "Building for 'bases[2]' as host matches 'build-on[0]'." in records


def test_build_project_is_cwd(
    basic_project,
    caplog,
    mock_capture_logs_from_instance,
    mock_ensure_provider_is_available,
    monkeypatch,
):
    """Test cases for base-index parameter."""
    mode = message_handler.NORMAL
    monkeypatch.setattr(message_handler, "mode", mode)
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - name: ubuntu
                    channel: "18.04"
                    architectures: {host_base.architectures!r}
                """
        )
    )
    config = load(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    monkeypatch.chdir(basic_project)
    with patch("charmcraft.commands.build.launched_environment") as mock_launch:
        zipnames = builder.run([0])

    assert zipnames == [
        f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
    ]
    assert mock_launch.mock_calls == [
        call(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
            bases_index=0,
            build_on_index=0,
        ),
        call().__enter__(),
        call()
        .__enter__()
        .execute_run(
            ["charmcraft", "pack", "--bases-index", "0"],
            check=True,
            cwd="/root/project",
        ),
        call().__exit__(None, None, None),
    ]


def test_build_project_is_not_cwd(
    basic_project,
    caplog,
    mock_capture_logs_from_instance,
    mock_ensure_provider_is_available,
    monkeypatch,
):
    """Test cases for base-index parameter."""
    mode = message_handler.NORMAL
    monkeypatch.setattr(message_handler, "mode", mode)
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - name: ubuntu
                    channel: "18.04"
                    architectures: {host_base.architectures!r}
                """
        )
    )
    config = load(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    with patch("charmcraft.commands.build.launched_environment") as mock_launch:
        zipnames = builder.run([0])

    assert zipnames == [
        f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
    ]
    assert mock_launch.mock_calls == [
        call(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
            bases_index=0,
            build_on_index=0,
        ),
        call().__enter__(),
        call()
        .__enter__()
        .execute_run(
            ["charmcraft", "pack", "--bases-index", "0"],
            check=True,
            cwd="/root",
        ),
        call()
        .__enter__()
        .pull_file(
            source=pathlib.Path("/root") / zipnames[0],
            destination=pathlib.Path.cwd() / zipnames[0],
        ),
        call().__exit__(None, None, None),
    ]


@pytest.mark.parametrize(
    "mode,cmd_flags",
    [
        (message_handler.VERBOSE, ["--verbose"]),
        (message_handler.QUIET, ["--quiet"]),
        (message_handler.NORMAL, []),
    ],
)
def test_build_bases_index_scenarios_provider(
    mode,
    cmd_flags,
    basic_project,
    caplog,
    mock_capture_logs_from_instance,
    mock_ensure_provider_is_available,
    monkeypatch,
):
    """Test cases for base-index parameter."""
    monkeypatch.setattr(message_handler, "mode", mode)
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - name: ubuntu
                    channel: "18.04"
                    architectures: {host_base.architectures!r}
                  - name: ubuntu
                    channel: "20.04"
                    architectures: {host_base.architectures!r}
                  - name: ubuntu
                    channel: "unsupported-channel"
                    architectures: {host_base.architectures!r}
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    with patch("charmcraft.commands.build.launched_environment") as mock_launch:
        zipnames = builder.run([0])
        assert zipnames == [
            f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
        ]

        assert mock_launch.mock_calls == [
            call(
                charm_name="name-from-metadata",
                project_path=basic_project,
                base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
                bases_index=0,
                build_on_index=0,
            ),
            call().__enter__(),
            call()
            .__enter__()
            .execute_run(
                ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
                check=True,
                cwd="/root/project",
            ),
            call().__exit__(None, None, None),
        ]
        assert (
            f"Packing charm 'name-from-metadata_ubuntu-18.04-{host_arch}.charm'..."
            in [r.message for r in caplog.records]
        )
        mock_ensure_provider_is_available.assert_called_once()
        mock_launch.reset_mock()

        zipnames = builder.run([1])
        assert zipnames == [
            f"name-from-metadata_ubuntu-20.04-{host_arch}.charm",
        ]
        assert mock_launch.mock_calls == [
            call(
                charm_name="name-from-metadata",
                project_path=basic_project,
                base=Base(name="ubuntu", channel="20.04", architectures=[host_arch]),
                bases_index=1,
                build_on_index=0,
            ),
            call().__enter__(),
            call()
            .__enter__()
            .execute_run(
                ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
                check=True,
                cwd="/root/project",
            ),
            call().__exit__(None, None, None),
        ]
        mock_launch.reset_mock()

        zipnames = builder.run([0, 1])
        assert zipnames == [
            f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
            f"name-from-metadata_ubuntu-20.04-{host_arch}.charm",
        ]
        assert mock_launch.mock_calls == [
            call(
                charm_name="name-from-metadata",
                project_path=basic_project,
                base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
                bases_index=0,
                build_on_index=0,
            ),
            call().__enter__(),
            call()
            .__enter__()
            .execute_run(
                ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
                check=True,
                cwd="/root/project",
            ),
            call().__exit__(None, None, None),
            call(
                charm_name="name-from-metadata",
                project_path=basic_project,
                base=Base(name="ubuntu", channel="20.04", architectures=[host_arch]),
                bases_index=1,
                build_on_index=0,
            ),
            call().__enter__(),
            call()
            .__enter__()
            .execute_run(
                ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
                check=True,
                cwd="/root/project",
            ),
            call().__exit__(None, None, None),
        ]

        with pytest.raises(
            CommandError,
            match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
        ):
            builder.run([3])

        mock_launch.reset_mock()

        expected_msg = re.escape("Failed to build charm for bases index '0'.")
        with pytest.raises(
            CommandError,
            match=expected_msg,
        ):
            mock_instance = mock_launch.return_value.__enter__.return_value
            mock_instance.execute_run.side_effect = subprocess.CalledProcessError(
                -1,
                ["charmcraft", "pack", "..."],
                "some output",
                "some error",
            )
            builder.run([0])

        assert mock_instance.mock_calls == [
            call.execute_run(
                ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
                check=True,
                cwd="/root/project",
            ),
        ]
        assert mock_capture_logs_from_instance.mock_calls == [call(mock_instance)]


def test_build_bases_index_scenarios_managed_mode(basic_project, monkeypatch, caplog):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                        architectures: {host_base.architectures!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                        architectures: {host_base.architectures!r}
                  - build-on:
                      - name: unmatched-name
                        channel: unmatched-channel
                        architectures: [unmatched-arch1]
                    run-on:
                      - name: unmatched-name
                        channel: unmatched-channel
                        architectures: [unmatched-arch1]
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                        architectures: {host_base.architectures!r}
                    run-on:
                      - name: cross-name
                        channel: cross-channel
                        architectures: [cross-arch1]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    zipnames = builder.run([0])
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm",
    ]

    with pytest.raises(
        CommandError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run([1])

    zipnames = builder.run([2])
    assert zipnames == [
        "name-from-metadata_cross-name-cross-channel-cross-arch1.charm",
    ]


@patch(
    "charmcraft.bases.get_host_as_base",
    return_value=Base(name="xname", channel="xchannel", architectures=["xarch"]),
)
def test_build_error_no_match_with_charmcraft_yaml(
    mock_host_base, basic_project, monkeypatch, caplog
):
    """Error when no charms are buildable with host base, verifying each mismatched reason."""
    caplog.set_level(logging.DEBUG)
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            """\
                type: charm
                bases:
                  - name: unmatched-name
                    channel: xchannel
                    architectures: [xarch]
                  - name: xname
                    channel: unmatched-channel
                    architectures: [xarch]
                  - name: xname
                    channel: xchannel
                    architectures: [unmatched-arch1, unmatched-arch2]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    # Managed bases build.
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with pytest.raises(
        CommandError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run()

    records = [r.message for r in caplog.records]

    assert (
        "Skipping 'bases[0].build-on[0]': "
        "name 'unmatched-name' does not match host 'xname'."
    ) in records
    assert (
        "No suitable 'build-on' environment found in 'bases[0]' configuration."
        in records
    )
    assert (
        "Skipping 'bases[1].build-on[0]': "
        "channel 'unmatched-channel' does not match host 'xchannel'."
    ) in records
    assert (
        "No suitable 'build-on' environment found in 'bases[1]' configuration."
        in records
    )
    assert (
        "Skipping 'bases[2].build-on[0]': "
        "host architecture 'xarch' not in base architectures "
        "['unmatched-arch1', 'unmatched-arch2']."
    ) in records
    assert (
        "No suitable 'build-on' environment found in 'bases[2]' configuration."
        in records
    )


def test_build_invoke_charm_builder(tmp_path, config, monkeypatch):
    """Check transferred metadata and simple entrypoint, also return proper linked entrypoint."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")

    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = Builder(
        {
            "from": tmp_path,
            "entrypoint": entrypoint,
            "requirement": [tmp_path / "req1.txt", tmp_path / "req2.txt"],
        },
        config,
    )

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.commands.build.polite_exec") as mock_run:
        mock_run.side_effect = [1]
        with pytest.raises(CommandError, match="problems running charm builder"):
            builder.run()

    staging_venv_dir = tmp_path / charm_builder.STAGING_VENV_DIRNAME

    mock_run.assert_called_with(
        [
            sys.executable,
            "-m",
            "charmcraft.charm_builder",
            "--charmdir",
            str(tmp_path),
            "--builddir",
            str(build_dir),
            "--allow-pip-binary",
            "--entrypoint",
            str(entrypoint),
            "-r",
            str(tmp_path / "req1.txt"),
            "-r",
            str(tmp_path / "req2.txt"),
        ],
        env={
            "PATH": "{}/bin:${{PATH}}".format(str(staging_venv_dir)),
            "PYTHONUSERBASE": str(staging_venv_dir),
        },
    )


def test_build_package_tree_structure(tmp_path, monkeypatch, config):
    """The zip file is properly built internally."""
    # the metadata
    metadata_data = {"name": "name-from-metadata"}
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wt", encoding="ascii") as fh:
        yaml.dump(metadata_data, fh)

    # create some dirs and files! a couple of files outside, and the dir we'll zip...
    file_outside_1 = tmp_path / "file_outside_1"
    with file_outside_1.open("wb") as fh:
        fh.write(b"content_out_1")
    file_outside_2 = tmp_path / "file_outside_2"
    with file_outside_2.open("wb") as fh:
        fh.write(b"content_out_2")
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # ...also outside a dir with a file...
    dir_outside = tmp_path / "extdir"
    dir_outside.mkdir()
    file_ext = dir_outside / "file_ext"
    with file_ext.open("wb") as fh:
        fh.write(b"external file")

    # ...then another file inside, and another dir...
    file_inside = to_be_zipped_dir / "file_inside"
    with file_inside.open("wb") as fh:
        fh.write(b"content_in")
    dir_inside = to_be_zipped_dir / "somedir"
    dir_inside.mkdir()

    # ...also inside, a link to the external dir...
    dir_linked_inside = to_be_zipped_dir / "linkeddir"
    dir_linked_inside.symlink_to(dir_outside)

    # ...and finally another real file, and two symlinks
    file_deep_1 = dir_inside / "file_deep_1"
    with file_deep_1.open("wb") as fh:
        fh.write(b"content_deep")
    file_deep_2 = dir_inside / "file_deep_2"
    file_deep_2.symlink_to(file_inside)
    file_deep_3 = dir_inside / "file_deep_3"
    file_deep_3.symlink_to(file_outside_1)

    # zip it
    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = Builder(
        {
            "from": tmp_path,
            "entrypoint": "whatever",
            "requirement": [],
        },
        config,
    )
    zipname = builder.handle_package()

    # check the stuff outside is not in the zip, the stuff inside is zipped (with
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipname)
    assert "file_outside_1" not in [x.filename for x in zf.infolist()]
    assert "file_outside_2" not in [x.filename for x in zf.infolist()]
    assert zf.read("file_inside") == b"content_in"
    assert zf.read("somedir/file_deep_1") == b"content_deep"  # own
    assert zf.read("somedir/file_deep_2") == b"content_in"  # from file inside
    assert zf.read("somedir/file_deep_3") == b"content_out_1"  # from file outside 1
    assert (
        zf.read("linkeddir/file_ext") == b"external file"
    )  # from file in the outside linked dir


def test_build_package_name(tmp_path, monkeypatch, config):
    """The zip file name comes from the metadata."""
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # the metadata
    metadata_data = {"name": "name-from-metadata"}
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wt", encoding="ascii") as fh:
        yaml.dump(metadata_data, fh)

    # zip it
    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = Builder(
        {
            "from": tmp_path,
            "entrypoint": "whatever",
            "requirement": [],
        },
        config,
    )
    zipname = builder.handle_package()

    assert zipname == "name-from-metadata.charm"


def test_build_using_linters_attributes(basic_project, caplog, monkeypatch, config):
    """Use linters, log results, and save them in the manifest."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")
    builder = Builder(
        {
            "from": basic_project,
            "entrypoint": basic_project / "src" / "charm.py",
            "requirement": [],
        },
        config,
    )

    # the results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name-1",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="check-result-1",
        ),
        linters.CheckResult(
            name="check-name-2",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result=linters.IGNORED,
        ),
    ]

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch(
        "charmcraft.commands.build.check_if_base_matches_host",
        return_value=(True, None),
    ):
        with patch("charmcraft.linters.analyze") as mock_analyze:
            mock_analyze.return_value = linting_results
            zipnames = builder.run()

    # check the analyze function was called properly
    mock_analyze.assert_called_with(config, builder.buildpath)

    # logs (do NOT see the ignored check)
    expected = [
        "Check result: check-name-1 [attribute] check-result-1 (text; see more at url).",
    ]
    logged = [rec.message for rec in caplog.records]
    assert all(e in logged for e in expected)

    # the manifest should have all the results (including the ignored one)
    zf = zipfile.ZipFile(zipnames[0])
    manifest = yaml.safe_load(zf.read("manifest.yaml"))
    expected = {
        "attributes": [
            {"name": "check-name-1", "result": "check-result-1"},
            {"name": "check-name-2", "result": "ignored"},
        ]
    }
    assert manifest["analysis"] == expected


# --- tests for relativise helper


def test_relativise_sameparent():
    """Two files in the same dir."""
    src = pathlib.Path("/tmp/foo/bar/src.txt")
    dst = pathlib.Path("/tmp/foo/bar/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("dst.txt")


def test_relativise_src_under():
    """The src is in subdirectory of dst's parent."""
    src = pathlib.Path("/tmp/foo/bar/baz/src.txt")
    dst = pathlib.Path("/tmp/foo/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../../dst.txt")


def test_relativise_dst_under():
    """The dst is in subdirectory of src's parent."""
    src = pathlib.Path("/tmp/foo/src.txt")
    dst = pathlib.Path("/tmp/foo/bar/baz/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("bar/baz/dst.txt")


def test_relativise_different_parents_shallow():
    """Different parents for src and dst, but shallow."""
    src = pathlib.Path("/tmp/foo/bar/src.txt")
    dst = pathlib.Path("/tmp/foo/baz/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../baz/dst.txt")


def test_relativise_different_parents_deep():
    """Different parents for src and dst, in a deep structure."""
    src = pathlib.Path("/tmp/foo/bar1/bar2/src.txt")
    dst = pathlib.Path("/tmp/foo/baz1/baz2/baz3/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../../baz1/baz2/baz3/dst.txt")


def test_format_charm_file_name_legacy():
    """Basic entry."""
    assert format_charm_file_name("charm-name", None) == "charm-name.charm"


def test_format_charm_file_name_basic():
    """Basic entry."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [
                Base(name="xname", channel="xchannel", architectures=["xarch1"])
            ],
        }
    )

    assert (
        format_charm_file_name("charm-name", bases_config)
        == "charm-name_xname-xchannel-xarch1.charm"
    )


def test_format_charm_file_name_multi_arch():
    """Multiple architectures."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [
                Base(
                    name="xname",
                    channel="xchannel",
                    architectures=["xarch1", "xarch2", "xarch3"],
                )
            ],
        }
    )

    assert (
        format_charm_file_name("charm-name", bases_config)
        == "charm-name_xname-xchannel-xarch1-xarch2-xarch3.charm"
    )


def test_format_charm_file_name_multi_run_on():
    """Multiple run-on entries."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [
                Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                Base(
                    name="x2name",
                    channel="x2channel",
                    architectures=["x2arch1", "x2arch2"],
                ),
            ],
        }
    )

    assert (
        format_charm_file_name("charm-name", bases_config)
        == "charm-name_x1name-x1channel-x1arch_x2name-x2channel-x2arch1-x2arch2.charm"
    )
