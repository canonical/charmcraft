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
from unittest import mock
from unittest.mock import call, patch, ANY

import pytest
import yaml
from craft_cli import EmitterMode, emit, CraftError

from charmcraft import linters
from charmcraft.charm_builder import DISPATCH_CONTENT, relativise
from charmcraft.bases import get_host_as_base
from charmcraft.commands.build import (
    BUILD_DIRNAME,
    Builder,
    Validator,
    format_charm_file_name,
    launch_shell,
)
from charmcraft.config import Base, BasesConfiguration, load
from charmcraft.metadata import CHARM_METADATA


def get_builder(
    config,
    *,
    project_dir=None,
    entrypoint="src/charm.py",
    requirement=None,
    force=False,
    debug=False,
    shell=False,
    shell_after=False,
):
    if project_dir is None:
        project_dir = config.project.dirpath

    if entrypoint == "src/charm.py":
        entrypoint = project_dir / "src" / "charm.py"

    if requirement is None:
        requirement = []

    return Builder(
        {
            "debug": debug,
            "entrypoint": entrypoint,
            "force": force,
            "from": project_dir,
            "requirement": requirement,
            "shell": shell,
            "shell_after": shell_after,
        },
        config,
    )


@pytest.fixture
def basic_project(tmp_path):
    """Create a basic Charmcraft project."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # the metadata
    metadata_data = {
        "name": "name-from-metadata",
        "summary": "test-summ",
        "description": "text",
    }
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

    # the license file
    license = tmp_path / "LICENSE"
    license.write_text("license content")

    # other optional assets
    icon = tmp_path / "icon.svg"
    icon.write_text("icon content")

    # README
    readme = tmp_path / "README.md"
    readme.write_text("README content")

    yield tmp_path


@pytest.fixture
def basic_project_builder(basic_project):
    def _basic_project_builder(bases_configs: List[BasesConfiguration], **builder_kwargs):
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
        return get_builder(config, **builder_kwargs)

    return _basic_project_builder


@pytest.fixture
def mock_capture_logs_from_instance():
    with patch("charmcraft.commands.build.capture_logs_from_instance") as mock_capture:
        yield mock_capture


@pytest.fixture
def mock_launch_shell():
    with patch("charmcraft.commands.build.launch_shell") as mock_shell:
        yield mock_shell


@pytest.fixture
def mock_linters():
    with patch("charmcraft.commands.build.linters") as mock_linters:
        mock_linters.analyze.return_value = []
        yield mock_linters


@pytest.fixture
def mock_parts():
    with patch("charmcraft.commands.build.parts") as mock_parts:
        yield mock_parts


@pytest.fixture(autouse=True)
def mock_provider(mock_instance, fake_provider):
    mock_provider = mock.Mock(wraps=fake_provider)
    with patch("charmcraft.commands.build.get_provider", return_value=mock_provider):
        yield mock_provider


@pytest.fixture
def mock_subprocess_run():
    with mock.patch("subprocess.run") as mock_run:
        yield mock_run


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


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_validator_from_exist(config):
    """'from' param: checks that the directory exists."""
    validator = Validator(config)
    expected_msg = "Charm directory was not found: '/not_really_there'"
    with pytest.raises(CraftError, match=expected_msg):
        validator.validate_from(pathlib.Path("/not_really_there"))


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_validator_from_isdir(tmp_path, config):
    """'from' param: checks that the directory is really that."""
    testfile = tmp_path / "testfile"
    testfile.touch()

    validator = Validator(config)
    expected_msg = "Charm directory is not really a directory: '{}'".format(testfile)
    with pytest.raises(CraftError, match=expected_msg):
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
    with pytest.raises(CraftError, match=expected_msg):
        validator.validate_bases_indices(bases_indices)


def test_validator_entrypoint_simple(tmp_path, config):
    """'entrypoint' param: simple validation."""
    testfile = tmp_path / "testfile"
    testfile.touch(mode=0o777)

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(testfile)
    assert resp == testfile


def test_validator_entrypoint_none(tmp_path, config):
    """'entrypoint' param: default value."""

    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(None)
    assert resp is None


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


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
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


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_validator_entrypoint_exist(config):
    """'entrypoint' param: checks that the file exists."""
    validator = Validator(config)
    expected_msg = "Charm entry point was not found: '/not_really_there.py'"
    with pytest.raises(CraftError, match=expected_msg):
        validator.validate_entrypoint(pathlib.Path("/not_really_there.py"))


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_validator_entrypoint_inside_project(tmp_path, config):
    """'entrypoint' param: checks that it's part of the project."""
    project_dir = tmp_path / "test-project"
    testfile = tmp_path / "testfile"
    testfile.touch(mode=0o777)

    validator = Validator(config)
    validator.basedir = project_dir

    expected_msg = "Charm entry point must be inside the project: '{}'".format(testfile)
    with pytest.raises(CraftError, match=expected_msg):
        validator.validate_entrypoint(testfile)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_validator_entrypoint_exec(tmp_path, config):
    """'entrypoint' param: checks that the file is executable."""
    testfile = tmp_path / "testfile"
    testfile.touch(mode=0o444)

    validator = Validator(config)
    validator.basedir = tmp_path
    expected_msg = "Charm entry point must be executable: '{}'".format(testfile)
    with pytest.raises(CraftError, match=expected_msg):
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


def test_validator_requirement_none(tmp_path, config):
    """'requirement' param: default value when a requirements.txt is there and readable."""
    validator = Validator(config)
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == []


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


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
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


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_validator_requirement_exist(config):
    """'requirement' param: checks that the file exists."""
    validator = Validator(config)
    expected_msg = "the requirements file was not found: '/not_really_there.txt'"
    with pytest.raises(CraftError, match=expected_msg):
        validator.validate_requirement([pathlib.Path("/not_really_there.txt")])


@pytest.mark.parametrize(
    "inp_value,out_value",
    [
        (None, False),
        (False, False),
        (True, True),
    ],
)
def test_validator_force(config, inp_value, out_value):
    """'entrypoint' param: checks that the file exists."""
    validator = Validator(config)
    result = validator.validate_force(inp_value)
    assert result == out_value


# --- (real) build tests


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_basic_complete_structure(basic_project, caplog, monkeypatch, config, tmp_path):
    """Integration test: a simple structure with custom lib and normal src dir."""
    caplog.set_level(logging.WARNING, logger="charmcraft")
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    monkeypatch.chdir(basic_project)  # so the zip file is left in the temp dir
    builder = get_builder(config)

    # save original metadata and verify later
    metadata_file = basic_project / "metadata.yaml"
    metadata_raw = metadata_file.read_bytes()

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch(
        "charmcraft.commands.build.check_if_base_matches_host",
        return_value=(True, None),
    ), patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run()

    assert zipnames == [f"name-from-metadata_ubuntu-20.04-{host_arch}.charm"]

    # check all is properly inside the zip
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipnames[0])
    assert zf.read("metadata.yaml") == metadata_raw
    assert zf.read("src/charm.py") == b"all the magic"
    dispatch = DISPATCH_CONTENT.format(entrypoint_relative_path="src/charm.py").encode("ascii")
    assert zf.read("dispatch") == dispatch
    assert zf.read("hooks/install") == dispatch
    assert zf.read("hooks/start") == dispatch
    assert zf.read("hooks/upgrade-charm") == dispatch
    assert zf.read("lib/ops/stuff.txt") == b"ops stuff"
    assert zf.read("LICENSE") == b"license content"
    assert zf.read("icon.svg") == b"icon content"
    assert zf.read("README.md") == b"README content"

    # check the manifest is present and with particular values that depend on given info
    manifest = yaml.safe_load(zf.read("manifest.yaml"))
    assert manifest["charmcraft-started-at"] == config.project.started_at.isoformat() + "Z"
    assert caplog.records == []


def test_build_error_without_metadata_yaml(basic_project, monkeypatch):
    """Validate error if trying to build project without metadata.yaml."""
    metadata = basic_project / CHARM_METADATA
    metadata.unlink()

    config = load(basic_project)
    monkeypatch.chdir(basic_project)

    with pytest.raises(CraftError, match=r"Missing mandatory metadata.yaml."):
        get_builder(config)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_with_charmcraft_yaml_destructive_mode(basic_project_builder, emitter, monkeypatch):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})]
    )

    zipnames = builder.run(destructive_mode=True)

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm"
    ]

    emitter.assert_trace("Building for 'bases[0]' as host matches 'build-on[0]'.")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_with_charmcraft_yaml_managed_mode(
    basic_project_builder, emitter, monkeypatch, tmp_path
):
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})]
    )

    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run()

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm"
    ]

    emitter.assert_trace("Building for 'bases[0]' as host matches 'build-on[0]'.")


def test_build_checks_provider(basic_project, mock_provider):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = get_builder(config)

    builder.run()

    mock_provider.ensure_provider_is_available.assert_called_once()


def test_build_with_debug_no_error(
    basic_project_builder,
    mock_linters,
    mock_parts,
    mock_launch_shell,
):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        debug=True,
    )

    charms = builder.run(destructive_mode=True)

    assert len(charms) == 1
    assert mock_launch_shell.mock_calls == []


def test_build_with_debug_with_error(
    basic_project_builder,
    mock_linters,
    mock_parts,
    mock_launch_shell,
):
    mock_parts.PartsLifecycle.return_value.run.side_effect = CraftError("fail")
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        debug=True,
    )

    with pytest.raises(CraftError):
        builder.run(destructive_mode=True)

    assert mock_launch_shell.mock_calls == [mock.call()]


def test_build_with_shell(basic_project_builder, mock_parts, mock_provider, mock_launch_shell):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        shell=True,
    )

    charms = builder.run(destructive_mode=True)

    assert charms == []
    assert mock_launch_shell.mock_calls == [mock.call()]


def test_build_with_shell_after(
    basic_project_builder,
    mock_linters,
    mock_parts,
    mock_launch_shell,
):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        shell_after=True,
    )

    charms = builder.run(destructive_mode=True)

    assert len(charms) == 1
    assert mock_launch_shell.mock_calls == [mock.call()]


def test_build_checks_provider_error(basic_project, mock_provider):
    """Test cases for base-index parameter."""
    mock_provider.ensure_provider_is_available.side_effect = RuntimeError("foo")
    config = load(basic_project)
    builder = get_builder(config)

    with pytest.raises(RuntimeError, match="foo"):
        builder.run()


def test_build_without_charmcraft_yaml_issues_dn02(basic_project, emitter):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = get_builder(config)

    builder.run()

    emitter.assert_message(
        "DEPRECATED: A charmcraft.yaml configuration file is now required.", intermediate=True
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_multiple_with_charmcraft_yaml_destructive_mode(basic_project_builder, emitter):
    """Build multiple charms for multiple matching bases, skipping one unmatched config."""
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
            BasesConfiguration(**{"build-on": [unmatched_base], "run-on": [unmatched_base]}),
            BasesConfiguration(**{"build-on": [host_base], "run-on": [matched_cross_base]}),
        ]
    )

    zipnames = builder.run(destructive_mode=True)

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm",
        "name-from-metadata_cross-name-cross-channel-cross-arch1.charm",
    ]

    reason = f"name 'unmatched-name' does not match host {host_base.name!r}."
    emitter.assert_interactions(
        [
            call("trace", "Building for 'bases[0]' as host matches 'build-on[0]'."),
            call("progress", f"Skipping 'bases[1].build-on[0]': {reason}"),
            call(
                "message",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                intermediate=True,
            ),
            call("trace", "Building for 'bases[2]' as host matches 'build-on[0]'."),
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_multiple_with_charmcraft_yaml_managed_mode(
    basic_project_builder, monkeypatch, emitter, tmp_path
):
    """Build multiple charms for multiple matching bases, skipping one unmatched config."""
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
            BasesConfiguration(**{"build-on": [unmatched_base], "run-on": [unmatched_base]}),
            BasesConfiguration(**{"build-on": [host_base], "run-on": [matched_cross_base]}),
        ]
    )

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run()

    host_arch = host_base.architectures[0]
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm",
        "name-from-metadata_cross-name-cross-channel-cross-arch1.charm",
    ]

    reason = f"name 'unmatched-name' does not match host {host_base.name!r}."
    emitter.assert_interactions(
        [
            call("trace", "Building for 'bases[0]' as host matches 'build-on[0]'."),
            call("progress", f"Skipping 'bases[1].build-on[0]': {reason}"),
            call(
                "message",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                intermediate=True,
            ),
            call("trace", "Building for 'bases[2]' as host matches 'build-on[0]'."),
        ]
    )


def test_build_project_is_cwd(
    basic_project,
    emitter,
    mock_capture_logs_from_instance,
    mock_instance,
    mock_provider,
    monkeypatch,
):
    """Test cases for base-index parameter."""
    emit.set_mode(EmitterMode.NORMAL)
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
    builder = get_builder(config)

    monkeypatch.chdir(basic_project)
    zipnames = builder.run([0])

    assert zipnames == [
        f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.ensure_provider_is_available(),
        call.is_base_available(
            Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
        ),
        call.launched_environment(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
            bases_index=0,
            build_on_index=0,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"],
            check=True,
            cwd=pathlib.Path("/root/project"),
            stdout=ANY,
            stderr=ANY,
        ),
    ]


def test_build_project_is_not_cwd(
    basic_project,
    mock_capture_logs_from_instance,
    mock_instance,
    mock_provider,
):
    """Test cases for base-index parameter."""
    emit.set_mode(EmitterMode.NORMAL)
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
    builder = get_builder(config)

    zipnames = builder.run([0])

    assert zipnames == [
        f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.ensure_provider_is_available(),
        call.is_base_available(
            Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
        ),
        call.launched_environment(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
            bases_index=0,
            build_on_index=0,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"],
            check=True,
            cwd=pathlib.Path("/root"),
            stdout=ANY,
            stderr=ANY,
        ),
        call.pull_file(
            source=pathlib.Path("/root") / zipnames[0],
            destination=pathlib.Path.cwd() / zipnames[0],
        ),
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize(
    "mode,cmd_flags",
    [
        (EmitterMode.VERBOSE, ["--verbose"]),
        (EmitterMode.QUIET, ["--quiet"]),
        (EmitterMode.TRACE, ["--trace"]),
        (EmitterMode.NORMAL, []),
    ],
)
def test_build_bases_index_scenarios_provider(
    mode,
    cmd_flags,
    basic_project,
    emitter,
    mock_capture_logs_from_instance,
    mock_instance,
    mock_provider,
    monkeypatch,
):
    """Test cases for base-index parameter."""
    emit.set_mode(mode)
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
    builder = get_builder(config)

    zipnames = builder.run([0])
    assert zipnames == [
        f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
    ]

    assert mock_provider.mock_calls == [
        call.ensure_provider_is_available(),
        call.is_base_available(
            Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
        ),
        call.launched_environment(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
            bases_index=0,
            build_on_index=0,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
            check=True,
            cwd=pathlib.Path("/root/project"),
            stdout=ANY,
            stderr=ANY,
        ),
    ]
    emitter.assert_progress(
        "Launching environment to pack for base "
        "name='ubuntu' channel='18.04' architectures=['amd64'] "
        "(may take a while the first time but it's reusable)"
    )
    emitter.assert_progress("Packing the charm")
    mock_provider.reset_mock()
    mock_instance.reset_mock()

    zipnames = builder.run([1])
    assert zipnames == [
        f"name-from-metadata_ubuntu-20.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.ensure_provider_is_available(),
        call.is_base_available(
            Base(name="ubuntu", channel="20.04", architectures=[host_arch]),
        ),
        call.launched_environment(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="20.04", architectures=[host_arch]),
            bases_index=1,
            build_on_index=0,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
            check=True,
            cwd=pathlib.Path("/root/project"),
            stdout=ANY,
            stderr=ANY,
        ),
    ]
    mock_provider.reset_mock()
    mock_instance.reset_mock()

    zipnames = builder.run([0, 1])
    assert zipnames == [
        f"name-from-metadata_ubuntu-18.04-{host_arch}.charm",
        f"name-from-metadata_ubuntu-20.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.ensure_provider_is_available(),
        call.is_base_available(
            Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
        ),
        call.is_base_available(
            Base(name="ubuntu", channel="20.04", architectures=[host_arch]),
        ),
        call.launched_environment(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
            bases_index=0,
            build_on_index=0,
        ),
        call.launched_environment(
            charm_name="name-from-metadata",
            project_path=basic_project,
            base=Base(name="ubuntu", channel="20.04", architectures=[host_arch]),
            bases_index=1,
            build_on_index=0,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
            check=True,
            cwd=pathlib.Path("/root/project"),
            stdout=ANY,
            stderr=ANY,
        ),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
            check=True,
            cwd=pathlib.Path("/root/project"),
            stdout=ANY,
            stderr=ANY,
        ),
    ]
    mock_provider.reset_mock()
    mock_instance.reset_mock()

    with pytest.raises(
        CraftError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run([3])

    mock_provider.reset_mock()
    mock_instance.reset_mock()

    expected_msg = re.escape("Failed to build charm for bases index '0'.")
    with pytest.raises(
        CraftError,
        match=expected_msg,
    ):
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
            cwd=pathlib.Path("/root/project"),
            stdout=ANY,
            stderr=ANY,
        ),
    ]
    assert mock_capture_logs_from_instance.mock_calls == [call(mock_instance)]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_bases_index_scenarios_managed_mode(basic_project, monkeypatch, tmp_path):
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
    builder = get_builder(config)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run([0])
    assert zipnames == [
        f"name-from-metadata_{host_base.name}-{host_base.channel}-{host_arch}.charm",
    ]

    with pytest.raises(
        CraftError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run([1])

    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run([2])
    assert zipnames == [
        "name-from-metadata_cross-name-cross-channel-cross-arch1.charm",
    ]


@patch(
    "charmcraft.bases.get_host_as_base",
    return_value=Base(name="xname", channel="xchannel", architectures=["xarch"]),
)
def test_build_error_no_match_with_charmcraft_yaml(
    mock_host_base, basic_project, monkeypatch, emitter
):
    """Error when no charms are buildable with host base, verifying each mismatched reason."""
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
    builder = get_builder(config)

    # Managed bases build.
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with pytest.raises(
        CraftError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run()

    emitter.assert_interactions(
        [
            call(
                "progress",
                "Skipping 'bases[0].build-on[0]': "
                "name 'unmatched-name' does not match host 'xname'.",
            ),
            call(
                "message",
                "No suitable 'build-on' environment found in 'bases[0]' configuration.",
                intermediate=True,
            ),
            call(
                "progress",
                "Skipping 'bases[1].build-on[0]': "
                "channel 'unmatched-channel' does not match host 'xchannel'.",
            ),
            call(
                "message",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                intermediate=True,
            ),
            call(
                "progress",
                "Skipping 'bases[2].build-on[0]': "
                "host architecture 'xarch' not in base architectures "
                "['unmatched-arch1', 'unmatched-arch2'].",
            ),
            call(
                "message",
                "No suitable 'build-on' environment found in 'bases[2]' configuration.",
                intermediate=True,
            ),
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
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
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )
    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = get_builder(config, entrypoint="whatever")
    zipname = builder.handle_package(to_be_zipped_dir, bases_config)

    # check the stuff outside is not in the zip, the stuff inside is zipped (with
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipname)
    assert "file_outside_1" not in [x.filename for x in zf.infolist()]
    assert "file_outside_2" not in [x.filename for x in zf.infolist()]
    assert zf.read("file_inside") == b"content_in"
    assert zf.read("somedir/file_deep_1") == b"content_deep"  # own
    assert zf.read("somedir/file_deep_2") == b"content_in"  # from file inside
    assert zf.read("somedir/file_deep_3") == b"content_out_1"  # from file outside 1
    assert zf.read("linkeddir/file_ext") == b"external file"  # from file in the outside linked dir


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
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )
    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = get_builder(config, entrypoint="whatever")
    zipname = builder.handle_package(to_be_zipped_dir, bases_config)

    assert zipname == "name-from-metadata_xname-xchannel-xarch1.charm"


def test_build_with_entrypoint_argument_issues_dn04(basic_project, emitter, monkeypatch):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = get_builder(config)

    builder.run()

    emitter.assert_message(
        "DEPRECATED: Use 'charm-entrypoint' in charmcraft.yaml parts to define the entry point.",
        intermediate=True,
    )


def test_build_entrypoint_from_parts(basic_project, monkeypatch):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                parts:
                  charm:
                    charm-entrypoint: "my_entrypoint.py"
                    charm-requirements: ["reqs.txt"]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None)

    entrypoint = basic_project / "my_entrypoint.py"
    entrypoint.touch()
    entrypoint.chmod(0o700)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "my_entrypoint.py",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "my_entrypoint.py",
                        "charm-requirements": ["reqs.txt"],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_entrypoint_from_commandline(basic_project, monkeypatch):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                parts:
                  charm:
                     charm-requirements: ["reqs.txt"]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    entrypoint = basic_project / "my_entrypoint.py"
    builder = get_builder(config, entrypoint=entrypoint)

    entrypoint.touch()
    entrypoint.chmod(0o700)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "my_entrypoint.py",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "my_entrypoint.py",
                        "charm-requirements": ["reqs.txt"],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_entrypoint_default(basic_project, monkeypatch):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                parts:
                  charm:
                     charm-requirements: ["reqs.txt"]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None, force=True)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": ["reqs.txt"],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_entrypoint_from_both(basic_project, monkeypatch):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}

                parts:
                  charm:
                    charm-entrypoint: "my_entrypoint.py"
                    charm-requirements: ["reqs.txt"]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    entrypoint = basic_project / "my_entrypoint.py"

    builder = get_builder(config, entrypoint=entrypoint, force=True)

    entrypoint.touch()
    entrypoint.chmod(0o700)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with pytest.raises(CraftError) as raised:
        builder.run([0])
    assert str(raised.value) == (
        "--entrypoint not supported when charm-entrypoint specified in charmcraft.yaml"
    )


def test_build_with_requirement_argment_issues_dn05(basic_project, emitter, monkeypatch):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = get_builder(config, entrypoint=None, requirement=["reqs.txt"])

    builder.run()

    emitter.assert_message(
        "DEPRECATED: Use 'charm-requirements' in charmcraft.yaml parts to define requirements.",
        intermediate=True,
    )


def test_build_requirements_from_parts(basic_project, monkeypatch):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}

                parts:
                  charm:
                    charm-entrypoint: src/charm.py
                    charm-requirements: ["reqs.txt"]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None, force=True)

    reqs = basic_project / "reqs.txt"
    reqs.touch()

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": ["reqs.txt"],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_requirements_from_commandline(basic_project, monkeypatch, emitter):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}

                parts:
                  charm:
                    charm-entrypoint: src/charm.py
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None, force=True, requirement=["reqs.txt"])

    reqs = basic_project / "reqs.txt"
    reqs.touch()

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": ["reqs.txt"],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_requirements_default(basic_project, monkeypatch, emitter):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}

                parts:
                  charm:
                    charm-entrypoint: src/charm.py
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None, force=True)

    # create a requirements.txt file
    pathlib.Path(basic_project, "requirements.txt").write_text("ops >= 1.2.0")

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": ["requirements.txt"],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_requirements_no_requirements_txt(basic_project, monkeypatch, emitter):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}

                parts:
                  charm:
                    charm-entrypoint: src/charm.py
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None, force=True)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": [],
                        "source": str(basic_project),
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


def test_build_requirements_from_both(basic_project, monkeypatch, emitter):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    charmcraft_file = basic_project / "charmcraft.yaml"
    charmcraft_file.write_text(
        dedent(
            f"""\
                type: charm
                bases:
                  - build-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}
                    run-on:
                      - name: {host_base.name!r}
                        channel: {host_base.channel!r}

                parts:
                  charm:
                    charm-requirements: ["reqs.txt"]
                """
        )
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None, force=True, requirement=["reqs.txt"])

    reqs = basic_project / "reqs.txt"
    reqs.touch()

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with pytest.raises(CraftError) as raised:
        builder.run([0])
    assert str(raised.value) == (
        "--requirement not supported when charm-requirements specified in charmcraft.yaml"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_using_linters_attributes(basic_project, monkeypatch, config, tmp_path):
    """Generic use of linters, pass them ok to their proceessor and save them in the manifest."""
    builder = get_builder(config)

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
    ), patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        with patch("charmcraft.linters.analyze") as mock_analyze:
            with patch.object(Builder, "show_linting_results") as mock_show_lint:
                mock_analyze.return_value = linting_results
                zipnames = builder.run()

    # check the analyze and processing functions were called properly
    mock_analyze.assert_called_with(config, tmp_path / "root" / "prime")
    mock_show_lint.assert_called_with(linting_results)

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


def test_show_linters_attributes(basic_project, emitter, config):
    """Show the linting results, only attributes, one ignored."""
    builder = get_builder(config)

    # fake results from the analyzer
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

    builder.show_linting_results(linting_results)

    expected = "Check result: check-name-1 [attribute] check-result-1 (text; see more at url)."
    emitter.assert_trace(expected)


def test_show_linters_lint_warnings(basic_project, emitter, config):
    """Show the linting results, some warnings."""
    builder = get_builder(config)

    # fake result from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.lint,
            url="check-url",
            text="Some text",
            result=linters.WARNINGS,
        ),
    ]

    builder.show_linting_results(linting_results)

    emitter.assert_interactions(
        [
            call("message", "Lint Warnings:", intermediate=True),
            call("message", "- check-name: Some text (check-url)", intermediate=True),
        ]
    )


def test_show_linters_lint_errors_normal(basic_project, emitter, config):
    """Show the linting results, have errors."""
    builder = get_builder(config)

    # fake result from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.lint,
            url="check-url",
            text="Some text",
            result=linters.ERRORS,
        ),
    ]

    with pytest.raises(CraftError) as cm:
        builder.show_linting_results(linting_results)
    exc = cm.value
    assert str(exc) == "Aborting due to lint errors (use --force to override)."
    assert exc.retcode == 2

    emitter.assert_interactions(
        [
            call("message", "Lint Errors:", intermediate=True),
            call("message", "- check-name: Some text (check-url)", intermediate=True),
        ]
    )


def test_show_linters_lint_errors_forced(basic_project, emitter, config):
    """Show the linting results, have errors but the packing is forced."""
    builder = get_builder(config, force=True)

    # fake result from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.lint,
            url="check-url",
            text="Some text",
            result=linters.ERRORS,
        ),
    ]

    builder.show_linting_results(linting_results)

    emitter.assert_interactions(
        [
            call("message", "Lint Errors:", intermediate=True),
            call("message", "- check-name: Some text (check-url)", intermediate=True),
            call("message", "Packing anyway as requested.", intermediate=True),
        ]
    )


# -- tests for implicit charm part


@pytest.fixture
def charmcraft_yaml():
    """Create a charmcraft.yaml with the given parts data."""

    def _write_yaml_file(project_dir, parts):
        host_base = get_host_as_base()
        header = dedent(
            f"""
            type: charm
            bases:
              - build-on:
                  - name: {host_base.name!r}
                    channel: {host_base.channel!r}
                run-on:
                  - name: {host_base.name!r}
                    channel: {host_base.channel!r}
            """
        )

        charmcraft_file = project_dir / "charmcraft.yaml"
        charmcraft_file.write_text(header + parts)

    return _write_yaml_file


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_parts_not_defined(basic_project, charmcraft_yaml, monkeypatch):
    """Parts are not defined.

    When the "parts" section does not exist, create an implicit "charm" part and
    populate it with the default charm building parameters.
    """
    charmcraft_yaml(basic_project, "")

    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None)

    # create a requirements.txt file
    pathlib.Path(basic_project, "requirements.txt").write_text("ops >= 1.2.0")

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": ["requirements.txt"],
                        "source": str(basic_project),
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_parts_with_charm_part(basic_project, charmcraft_yaml, monkeypatch):
    """Parts are declared with a charm part with implicit plugin.

    When the "parts" section exists in chamcraft.yaml and a part named "charm"
    is defined with implicit plugin (or explicit "charm" plugin), populate it
    with the defaults for charm building.
    """
    charmcraft_yaml(
        basic_project,
        dedent(
            """
            parts:
              charm:
                prime:
                  - my_extra_file.txt
            """
        ),
    )

    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None)

    # create a requirements.txt file
    pathlib.Path(basic_project, "requirements.txt").write_text("ops >= 1.2.0")

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "charm-entrypoint": "src/charm.py",
                        "charm-requirements": ["requirements.txt"],
                        "source": str(basic_project),
                        "prime": [
                            "my_extra_file.txt",
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_parts_without_charm_part(basic_project, charmcraft_yaml, monkeypatch):
    """Parts are declared without a charm part.

    When the "parts" section exists in chamcraft.yaml and a part named "charm"
    is not defined, process parts normally and don't invoke the charm plugin.
    This scenario is used to use parts processing to pack a generic hooks-based
    charm.
    """
    charmcraft_yaml(
        basic_project,
        dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        ),
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "foo": {
                        "plugin": "nil",
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_parts_with_charm_part_with_plugin(basic_project, charmcraft_yaml, monkeypatch):
    """Parts are declared with a charm part that uses a different plugin.

    When the "parts" section exists in chamcraft.yaml and a part named "charm"
    is defined with a plugin that's not "charm", handle it as a regular part
    without populating fields for charm building.
    """
    charmcraft_yaml(
        basic_project,
        dedent(
            """
            parts:
              charm:
                plugin: nil
            """
        ),
    )
    config = load(basic_project)
    monkeypatch.chdir(basic_project)
    builder = get_builder(config, entrypoint=None)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "nil",
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="name-from-metadata",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


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


def test_format_charm_file_name_basic():
    """Basic entry."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
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


def test_launch_shell(mock_subprocess_run):
    launch_shell()

    assert mock_subprocess_run.mock_calls == [mock.call(["bash"], check=False, cwd=None)]
