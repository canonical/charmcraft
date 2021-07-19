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

import errno
import filecmp
import logging
import os
import pathlib
import socket
import sys
from unittest.mock import call, patch

import pytest

from charmcraft import charm_builder
from charmcraft.charm_builder import STAGING_VENV_DIRNAME, CharmBuilder
from charmcraft.cmdbase import CommandError
from charmcraft.commands.build import BUILD_DIRNAME, DISPATCH_CONTENT, DISPATCH_FILENAME
from charmcraft.metadata import CHARM_METADATA


def test_build_generics_simple_files(tmp_path):
    """Check transferred metadata and simple entrypoint, also return proper linked entrypoint."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")

    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    linked_entrypoint = builder.handle_generic_paths()

    # check files are there, are files, and are really hard links (so no
    # check for permissions needed)
    built_metadata = build_dir / CHARM_METADATA
    assert built_metadata.is_file()
    assert built_metadata.stat().st_ino == metadata.stat().st_ino

    built_entrypoint = build_dir / "crazycharm.py"
    assert built_entrypoint.is_file()
    assert built_entrypoint.stat().st_ino == entrypoint.stat().st_ino

    assert linked_entrypoint == built_entrypoint


def test_build_generics_simple_dir(tmp_path):
    """Check transferred any directory, with proper permissions."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")

    somedir = tmp_path / "somedir"
    somedir.mkdir(mode=0o700)

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_dir = build_dir / "somedir"
    assert built_dir.is_dir()
    assert built_dir.stat().st_mode & 0xFFF == 0o700


def test_build_generics_ignored_file(tmp_path, caplog):
    """Don't include ignored filed."""
    caplog.set_level(logging.DEBUG)
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")

    # create two files (and the needed entrypoint)
    file1 = tmp_path / "file1.txt"
    file1.touch()
    file2 = tmp_path / "file2.txt"
    file2.touch()
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )

    # set it up to ignore file 2 and make it work
    builder.ignore_rules.extend_patterns(["file2.*"])
    builder.handle_generic_paths()

    assert (build_dir / "file1.txt").exists()
    assert not (build_dir / "file2.txt").exists()

    expected = "Ignoring file because of rules: 'file2.txt'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_ignored_dir(tmp_path, caplog):
    """Don't include ignored dir."""
    caplog.set_level(logging.DEBUG)
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")

    # create two files (and the needed entrypoint)
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )

    # set it up to ignore dir 2 and make it work
    builder.ignore_rules.extend_patterns(["dir2"])
    builder.handle_generic_paths()

    assert (build_dir / "dir1").exists()
    assert not (build_dir / "dir2").exists()

    expected = "Ignoring directory because of rules: 'dir2'"
    assert expected in [rec.message for rec in caplog.records]


def _test_build_generics_tree(tmp_path, caplog, *, expect_hardlinks):
    caplog.set_level(logging.DEBUG)

    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # create this structure:
    # ├─ crazycharm.py  (entrypoint)
    # ├─ file1.txt
    # ├─ dir1
    # │  └─ dir3  (ignored!)
    # └─ dir2
    #    ├─ file2.txt
    #    ├─ file3.txt  (ignored!)
    #    ├─ dir4  (ignored!)
    #    │   └─ file4.txt
    #    └─ dir5
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    file1 = tmp_path / "file1.txt"
    file1.touch()
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir3 = dir1 / "dir3"
    dir3.mkdir()
    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    file2 = dir2 / "file2.txt"
    file2.touch()
    file3 = dir2 / "file3.txt"
    file3.touch()
    dir4 = dir2 / "dir4"
    dir4.mkdir()
    file4 = dir4 / "file4.txt"
    file4.touch()
    dir5 = dir2 / "dir5"
    dir5.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )

    # set it up to ignore some stuff and make it work
    builder.ignore_rules.extend_patterns(
        [
            "dir1/dir3",
            "dir2/file3.txt",
            "dir2/dir4",
        ]
    )
    builder.handle_generic_paths()

    assert (build_dir / "crazycharm.py").exists()
    assert (build_dir / "file1.txt").exists()
    assert (build_dir / "dir1").exists()
    assert not (build_dir / "dir1" / "dir3").exists()
    assert (build_dir / "dir2").exists()
    assert (build_dir / "dir2" / "file2.txt").exists()
    assert not (build_dir / "dir2" / "file3.txt").exists()
    assert not (build_dir / "dir2" / "dir4").exists()
    assert (build_dir / "dir2" / "dir5").exists()

    for (p1, p2) in [
        (build_dir / "crazycharm.py", entrypoint),
        (build_dir / "file1.txt", file1),
        (build_dir / "dir2" / "file2.txt", file2),
    ]:
        if expect_hardlinks:
            # they're hard links
            assert p1.samefile(p2)
        else:
            # they're *not* hard links
            assert not p1.samefile(p2)
            # but they're essentially the same
            assert filecmp.cmp(str(p1), str(p2), shallow=False)
            assert p1.stat().st_mode == p2.stat().st_mode
            assert p1.stat().st_size == p2.stat().st_size
            assert p1.stat().st_atime == pytest.approx(p2.stat().st_atime)
            assert p1.stat().st_mtime == pytest.approx(p2.stat().st_mtime)


def test_build_generics_tree(tmp_path, caplog):
    """Manages ok a deep tree, including internal ignores."""
    _test_build_generics_tree(tmp_path, caplog, expect_hardlinks=True)


def test_build_generics_tree_vagrant(tmp_path, caplog):
    """Manages ok a deep tree, including internal ignores, when hardlinks aren't allowed."""
    with patch("os.link") as mock_link:
        mock_link.side_effect = PermissionError("No you don't.")
        _test_build_generics_tree(tmp_path, caplog, expect_hardlinks=False)


def test_build_generics_tree_xdev(tmp_path, caplog):
    """Manages ok a deep tree, including internal ignores, when hardlinks can't be done."""
    with patch("os.link") as mock_link:
        mock_link.side_effect = OSError(errno.EXDEV, os.strerror(errno.EXDEV))
        _test_build_generics_tree(tmp_path, caplog, expect_hardlinks=False)


def test_build_generics_symlink_file(tmp_path):
    """Respects a symlinked file."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    the_symlink = tmp_path / "somehook.py"
    the_symlink.symlink_to(entrypoint)

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_symlink = build_dir / "somehook.py"
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / "crazycharm.py"
    real_link = os.readlink(str(built_symlink))
    assert real_link == "crazycharm.py"


def test_build_generics_symlink_dir(tmp_path):
    """Respects a symlinked dir."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    somedir = tmp_path / "somedir"
    somedir.mkdir()
    somefile = somedir / "sanity check"
    somefile.touch()
    the_symlink = tmp_path / "thelink"
    the_symlink.symlink_to(somedir)

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_symlink = build_dir / "thelink"
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / "somedir"
    real_link = os.readlink(str(built_symlink))
    assert real_link == "somedir"

    # as a sanity check, the file inside the linked dir should exist
    assert (build_dir / "thelink" / "sanity check").exists()


def test_build_generics_symlink_deep(tmp_path):
    """Correctly re-links a symlink across deep dirs."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    original_target = dir1 / "file.real"
    original_target.touch()
    the_symlink = dir2 / "file.link"
    the_symlink.symlink_to(original_target)

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_symlink = build_dir / "dir2" / "file.link"
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / "dir1" / "file.real"
    real_link = os.readlink(str(built_symlink))
    assert real_link == "../dir1/file.real"


def test_build_generics_symlink_file_outside(tmp_path, caplog):
    """Ignores (with warning) a symlink pointing a file outside projects dir."""
    caplog.set_level(logging.WARNING)

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    metadata = project_dir / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = project_dir / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = project_dir / "crazycharm.py"
    entrypoint.touch()

    outside_project = tmp_path / "dangerous.txt"
    outside_project.touch()
    the_symlink = project_dir / "external-file"
    the_symlink.symlink_to(outside_project)

    builder = CharmBuilder(
        charmdir=project_dir,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    assert not (build_dir / "external-file").exists()
    expected = "Ignoring symlink because targets outside the project: 'external-file'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_symlink_directory_outside(tmp_path, caplog):
    """Ignores (with warning) a symlink pointing a dir outside projects dir."""
    caplog.set_level(logging.WARNING)

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    metadata = project_dir / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = project_dir / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = project_dir / "crazycharm.py"
    entrypoint.touch()

    outside_project = tmp_path / "dangerous"
    outside_project.mkdir()
    the_symlink = project_dir / "external-dir"
    the_symlink.symlink_to(outside_project)

    builder = CharmBuilder(
        charmdir=project_dir,
        builddir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    assert not (build_dir / "external-dir").exists()
    expected = "Ignoring symlink because targets outside the project: 'external-dir'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_different_filetype(tmp_path, caplog, monkeypatch):
    """Ignores whatever is not a regular file, symlink or dir."""
    caplog.set_level(logging.DEBUG)

    # change into the tmp path and do everything locally, because otherwise the socket path
    # will be too long for mac os
    monkeypatch.chdir(tmp_path)

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = pathlib.Path(BUILD_DIRNAME)
    build_dir.mkdir()
    entrypoint = pathlib.Path("crazycharm.py")
    entrypoint.touch()

    # create a socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind("test-socket")

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=tmp_path / entrypoint,
    )
    builder.handle_generic_paths()

    assert not (build_dir / "test-socket").exists()
    expected = "Ignoring file because of type: 'test-socket'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_staging_venv(tmp_path, caplog):
    """Ignores the staging venv directory."""
    caplog.set_level(logging.DEBUG)

    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = pathlib.Path("crazycharm.py")
    entrypoint.touch()
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")

    # create staging venv directory
    staging_venv_dir = tmp_path / STAGING_VENV_DIRNAME
    staging_venv_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=tmp_path / entrypoint,
    )
    builder.handle_generic_paths()

    installed_staging_venv_dir = build_dir / STAGING_VENV_DIRNAME
    assert not installed_staging_venv_dir.exists()
    expected = f"Ignoring staging venv: {STAGING_VENV_DIRNAME!r}"
    assert expected in [rec.message for rec in caplog.records]


def test_build_dispatcher_modern_dispatch_created(tmp_path):
    """The dispatcher script is properly built."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    linked_entrypoint = build_dir / "somestuff.py"

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    builder.handle_dispatcher(linked_entrypoint)

    included_dispatcher = build_dir / DISPATCH_FILENAME
    with included_dispatcher.open("rt", encoding="utf8") as fh:
        dispatcher_code = fh.read()
    assert dispatcher_code == DISPATCH_CONTENT.format(
        entrypoint_relative_path="somestuff.py"
    )


def test_build_dispatcher_modern_dispatch_respected(tmp_path):
    """The already included dispatcher script is left untouched."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    already_present_dispatch = build_dir / DISPATCH_FILENAME
    with already_present_dispatch.open("wb") as fh:
        fh.write(b"abc")

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    builder.handle_dispatcher("whatever")

    with already_present_dispatch.open("rb") as fh:
        assert fh.read() == b"abc"


def test_build_dispatcher_classic_hooks_mandatory_created(tmp_path):
    """The mandatory classic hooks are implemented ok if not present."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    linked_entrypoint = build_dir / "somestuff.py"
    included_dispatcher = build_dir / DISPATCH_FILENAME

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    with patch("charmcraft.charm_builder.MANDATORY_HOOK_NAMES", {"testhook"}):
        builder.handle_dispatcher(linked_entrypoint)

    test_hook = build_dir / "hooks" / "testhook"
    assert test_hook.is_symlink()
    assert test_hook.resolve() == included_dispatcher
    real_link = os.readlink(str(test_hook))
    assert real_link == os.path.join("..", DISPATCH_FILENAME)


def test_build_dispatcher_classic_hooks_mandatory_respected(tmp_path):
    """The already included mandatory classic hooks are left untouched."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    built_hooks_dir = build_dir / "hooks"
    built_hooks_dir.mkdir()
    test_hook = built_hooks_dir / "testhook"
    with test_hook.open("wb") as fh:
        fh.write(b"abc")

    linked_entrypoint = build_dir / "somestuff.py"

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    with patch("charmcraft.charm_builder.MANDATORY_HOOK_NAMES", {"testhook"}):
        builder.handle_dispatcher(linked_entrypoint)

    with test_hook.open("rb") as fh:
        assert fh.read() == b"abc"


def test_build_dispatcher_classic_hooks_linking_charm_replaced(tmp_path, caplog):
    """Hooks that are just a symlink to the entrypoint are replaced."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # simple source code
    src_dir = build_dir / "src"
    src_dir.mkdir()
    built_charm_script = src_dir / "charm.py"
    with built_charm_script.open("wb") as fh:
        fh.write(b"all the magic")

    # a test hook, just a symlink to the charm
    built_hooks_dir = build_dir / "hooks"
    built_hooks_dir.mkdir()
    test_hook = built_hooks_dir / "somehook"
    test_hook.symlink_to(built_charm_script)

    included_dispatcher = build_dir / DISPATCH_FILENAME

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    builder.handle_dispatcher(built_charm_script)

    # the test hook is still there and a symlink, but now pointing to the dispatcher
    assert test_hook.is_symlink()
    assert test_hook.resolve() == included_dispatcher
    expected = "Replacing existing hook 'somehook' as it's a symlink to the entrypoint"
    assert expected in [rec.message for rec in caplog.records]


def test_build_dependencies_virtualenv_simple(tmp_path):
    """A virtualenv is created with the specified requirements file."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        requirements=["reqs.txt"],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        builder.handle_dependencies()

    envpath = tmp_path / STAGING_VENV_DIRNAME
    assert mock_run.mock_calls == [
        call([sys.executable, "-m", "venv", str(envpath)]),
        call(["pip3", "--version"]),
        call(["pip3", "install", "--no-binary", ":all:", "-r", "reqs.txt"]),
    ]


def test_build_dependencies_virtualenv_allow_binary(tmp_path):
    """A virtualenv is created allowing binary wheels."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        allow_pip_binary=True,
        requirements=["reqs.txt"],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        builder.handle_dependencies()

    envpath = tmp_path / STAGING_VENV_DIRNAME
    assert mock_run.mock_calls == [
        call([sys.executable, "-m", "venv", str(envpath)]),
        call(["pip3", "--version"]),
        call(["pip3", "install", "-r", "reqs.txt"]),
    ]


def test_build_dependencies_virtualenv_multiple(tmp_path):
    """A virtualenv is created with multiple requirements files."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        requirements=["reqs1.txt", "reqs2.txt"],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        builder.handle_dependencies()

    envpath = tmp_path / STAGING_VENV_DIRNAME
    assert mock_run.mock_calls == [
        call([sys.executable, "-m", "venv", str(envpath)]),
        call(["pip3", "--version"]),
        call(
            [
                "pip3",
                "install",
                "--no-binary",
                ":all:",
                "-r",
                "reqs1.txt",
                "-r",
                "reqs2.txt",
            ]
        ),
    ]


def test_build_dependencies_virtualenv_packages_simple(tmp_path):
    """A virtualenv is created with the specified python package."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        python_packages=["pkg"],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        builder.handle_dependencies()

    envpath = tmp_path / STAGING_VENV_DIRNAME
    assert mock_run.mock_calls == [
        call([sys.executable, "-m", "venv", str(envpath)]),
        call(["pip3", "--version"]),
        call(["pip3", "install", "--no-binary", ":all:", "pkg"]),
    ]


def test_build_dependencies_virtualenv_packages_multiple(tmp_path):
    """A virtualenv is created with the specified python packages."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        python_packages=["pkg1", "pkg2"],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        builder.handle_dependencies()

    envpath = tmp_path / STAGING_VENV_DIRNAME
    assert mock_run.mock_calls == [
        call([sys.executable, "-m", "venv", str(envpath)]),
        call(["pip3", "--version"]),
        call(["pip3", "install", "--no-binary", ":all:", "pkg1", "pkg2"]),
    ]


def test_build_dependencies_virtualenv_reqs_and_packages(tmp_path):
    """A virtualenv is created with both requirements and packages."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        python_packages=["pkg"],
        requirements=["reqs.txt"],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        builder.handle_dependencies()

    envpath = tmp_path / STAGING_VENV_DIRNAME
    assert mock_run.mock_calls == [
        call([sys.executable, "-m", "venv", str(envpath)]),
        call(["pip3", "--version"]),
        call(["pip3", "install", "--no-binary", ":all:", "pkg", "-r", "reqs.txt"]),
    ]


def test_build_dependencies_virtualenv_none(tmp_path):
    """The virtualenv is NOT created if no needed."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        requirements=[],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        builder.handle_dependencies()

    mock_run.assert_not_called()


def test_build_dependencies_virtualenv_error_creation(tmp_path):
    """Process is properly interrupted if creating venv fails."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        requirements=["something"],
    )

    with patch("charmcraft.charm_builder._process_run") as mock:
        mock.return_value = -7
        with pytest.raises(CommandError, match="problems creating venv"):
            builder.handle_dependencies()


def test_build_dependencies_virtualenv_error_basicpip(tmp_path):
    """Process is properly interrupted if using pip fails."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        requirements=["something"],
    )

    with patch("charmcraft.charm_builder._process_run") as mock:
        mock.side_effect = [0, -7]
        with pytest.raises(CommandError, match="problems using pip"):
            builder.handle_dependencies()


def test_build_dependencies_virtualenv_error_installing(tmp_path):
    """Process is properly interrupted if virtualenv creation fails."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        requirements=["something"],
    )

    with patch("charmcraft.charm_builder._process_run") as mock:
        mock.side_effect = [0, 0, -7]
        with pytest.raises(CommandError, match="problems installing dependencies"):
            builder.handle_dependencies()


def test_builder_without_jujuignore(tmp_path):
    """Without a .jujuignore we still have a default set of ignores"""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    ignore = builder._load_juju_ignore()
    assert ignore.match("/.git", is_dir=True)
    assert ignore.match("/build", is_dir=True)
    assert not ignore.match("myfile.py", is_dir=False)


def test_builder_with_jujuignore(tmp_path):
    """With a .jujuignore we will include additional ignores."""
    metadata = tmp_path / CHARM_METADATA
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    with (tmp_path / ".jujuignore").open("w", encoding="utf-8") as ignores:
        ignores.write("*.py\n" "/h\xef.txt\n")

    builder = CharmBuilder(
        charmdir=tmp_path,
        builddir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    ignore = builder._load_juju_ignore()
    assert ignore.match("/.git", is_dir=True)
    assert ignore.match("/build", is_dir=True)
    assert ignore.match("myfile.py", is_dir=False)
    assert not ignore.match("hi.txt", is_dir=False)
    assert ignore.match("h\xef.txt", is_dir=False)
    assert not ignore.match("myfile.c", is_dir=False)


def test_builder_arguments_defaults(tmp_path):
    """The arguments passed to the cli must be correctly parsed."""

    def mock_build_charm(self):
        assert self.charmdir == pathlib.Path("charmdir")
        assert self.buildpath == pathlib.Path("builddir")
        assert self.entrypoint == pathlib.Path("src/charm.py")
        assert self.allow_pip_binary is False
        assert self.python_packages is None
        assert self.requirements is None

    with patch.object(
        sys, "argv", ["cmd", "--charmdir", "charmdir", "--builddir", "builddir"]
    ):
        with patch(
            "charmcraft.charm_builder.CharmBuilder.build_charm", new=mock_build_charm
        ):
            charm_builder.main()


def test_builder_arguments_full(tmp_path):
    """The arguments passed to the cli must be correctly parsed."""

    def mock_build_charm(self):
        assert self.charmdir == pathlib.Path("charmdir")
        assert self.buildpath == pathlib.Path("builddir")
        assert self.entrypoint == pathlib.Path("src/charm.py")
        assert self.allow_pip_binary is True
        assert self.python_packages == ["pkg1", "pkg2"]
        assert self.requirements == ["reqs1.txt", "reqs2.txt"]

    with patch.object(
        sys,
        "argv",
        [
            "cmd",
            "--charmdir",
            "charmdir",
            "--builddir",
            "builddir",
            "--allow-pip-binary",
            "-p" "pkg1",
            "--python-packages",
            "pkg2",
            "-r" "reqs1.txt",
            "--requirement",
            "reqs2.txt",
        ],
    ):
        with patch(
            "charmcraft.charm_builder.CharmBuilder.build_charm", new=mock_build_charm
        ):
            charm_builder.main()
