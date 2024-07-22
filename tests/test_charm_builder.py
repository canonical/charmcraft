# Copyright 2020-2022 Canonical Ltd.
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
import os
import pathlib
import socket
import subprocess
import sys
from collections.abc import Callable
from unittest.mock import call, patch

import pytest

from charmcraft import charm_builder, const
from charmcraft.charm_builder import (
    KNOWN_GOOD_PIP_URL,
    CharmBuilder,
    _process_run,
)


def test_build_generics_simple_files(tmp_path):
    """Check transferred metadata and simple entrypoint, also return proper linked entrypoint."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")

    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    linked_entrypoint = builder.handle_generic_paths()

    # check files are there, are files, and are really hard links (so no
    # check for permissions needed)
    built_metadata = build_dir / const.METADATA_FILENAME
    assert built_metadata.is_file()
    assert built_metadata.stat().st_ino == metadata.stat().st_ino

    built_entrypoint = build_dir / "crazycharm.py"
    assert built_entrypoint.is_file()
    assert built_entrypoint.stat().st_ino == entrypoint.stat().st_ino

    assert linked_entrypoint == built_entrypoint


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_simple_dir(tmp_path):
    """Check transferred any directory, with proper permissions."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")

    somedir = tmp_path / "somedir"
    somedir.mkdir(mode=0o700)

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_dir = build_dir / "somedir"
    assert built_dir.is_dir()
    assert built_dir.stat().st_mode & 0xFFF == 0o700


def test_build_generics_ignored_file(tmp_path, assert_output):
    """Don't include ignored filed."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")

    # create two files (and the needed entrypoint)
    file1 = tmp_path / "file1.txt"
    file1.touch()
    file2 = tmp_path / "file2.txt"
    file2.touch()
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )

    # set it up to ignore file 2 and make it work
    builder.ignore_rules.extend_patterns(["file2.*"])
    builder.handle_generic_paths()

    assert (build_dir / "file1.txt").exists()
    assert not (build_dir / "file2.txt").exists()

    expected = "Ignoring file because of rules: 'file2.txt'"
    assert_output(expected)


def test_build_generics_ignored_dir(tmp_path, assert_output):
    """Don't include ignored dir."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")

    # create two files (and the needed entrypoint)
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )

    # set it up to ignore dir 2 and make it work
    builder.ignore_rules.extend_patterns(["dir2"])
    builder.handle_generic_paths()

    assert (build_dir / "dir1").exists()
    assert not (build_dir / "dir2").exists()

    expected = "Ignoring directory because of rules: 'dir2'"
    assert_output(expected)


def _test_build_generics_tree(tmp_path, *, expect_hardlinks):
    build_dir = tmp_path / const.BUILD_DIRNAME
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
    metadata = tmp_path / const.METADATA_FILENAME
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
        builddir=tmp_path,
        installdir=build_dir,
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

    for p1, p2 in [
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


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_tree(tmp_path):
    """Manages ok a deep tree, including internal ignores."""
    _test_build_generics_tree(tmp_path, expect_hardlinks=True)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_tree_vagrant(tmp_path):
    """Manages ok a deep tree, including internal ignores, when hardlinks aren't allowed."""
    with patch("os.link") as mock_link:
        mock_link.side_effect = PermissionError("No you don't.")
        _test_build_generics_tree(tmp_path, expect_hardlinks=False)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_tree_xdev(tmp_path):
    """Manages ok a deep tree, including internal ignores, when hardlinks can't be done."""
    with patch("os.link") as mock_link:
        mock_link.side_effect = OSError(errno.EXDEV, os.strerror(errno.EXDEV))
        _test_build_generics_tree(tmp_path, expect_hardlinks=False)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_symlink_file(tmp_path):
    """Respects a symlinked file."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    the_symlink = tmp_path / "somehook.py"
    the_symlink.symlink_to(entrypoint)

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_symlink = build_dir / "somehook.py"
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / "crazycharm.py"
    assert built_symlink.readlink() == pathlib.Path("crazycharm.py")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_symlink_dir(tmp_path):
    """Respects a symlinked dir."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    entrypoint = tmp_path / "crazycharm.py"
    entrypoint.touch()
    somedir = tmp_path / "somedir"
    somedir.mkdir()
    somefile = somedir / "some file"
    somefile.touch()
    the_symlink = tmp_path / "thelink"
    the_symlink.symlink_to(somedir)

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_symlink = build_dir / "thelink"
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / "somedir"
    assert built_symlink.readlink() == pathlib.Path("somedir")

    # the file inside the linked dir should exist
    assert (build_dir / "thelink" / "some file").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_symlink_deep(tmp_path):
    """Correctly re-links a symlink across deep dirs."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / const.METADATA_FILENAME
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
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    built_symlink = build_dir / "dir2" / "file.link"
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / "dir1" / "file.real"
    assert built_symlink.readlink() == pathlib.Path("..", "dir1", "file.real")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_symlink_file_outside(tmp_path, assert_output):
    """Ignores (with warning) a symlink pointing a file outside projects dir."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    metadata = project_dir / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = project_dir / const.BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = project_dir / "crazycharm.py"
    entrypoint.touch()

    outside_project = tmp_path / "dangerous.txt"
    outside_project.touch()
    the_symlink = project_dir / "external-file"
    the_symlink.symlink_to(outside_project)

    builder = CharmBuilder(
        builddir=project_dir,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    assert not (build_dir / "external-file").exists()
    expected = "Ignoring symlink because targets outside the project: 'external-file'"
    assert_output(expected)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_symlink_directory_outside(tmp_path, assert_output):
    """Ignores (with warning) a symlink pointing a dir outside projects dir."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    metadata = project_dir / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = project_dir / const.BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = project_dir / "crazycharm.py"
    entrypoint.touch()

    outside_project = tmp_path / "dangerous"
    outside_project.mkdir()
    the_symlink = project_dir / "external-dir"
    the_symlink.symlink_to(outside_project)

    builder = CharmBuilder(
        builddir=project_dir,
        installdir=build_dir,
        entrypoint=entrypoint,
    )
    builder.handle_generic_paths()

    assert not (build_dir / "external-dir").exists()
    expected = "Ignoring symlink because targets outside the project: 'external-dir'"
    assert_output(expected)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_generics_different_filetype(tmp_path, assert_output, monkeypatch):
    """Ignores whatever is not a regular file, symlink or dir."""
    # change into the tmp path and do everything locally, because otherwise the socket path
    # will be too long for mac os
    monkeypatch.chdir(tmp_path)

    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = pathlib.Path(const.BUILD_DIRNAME)
    build_dir.mkdir()
    entrypoint = pathlib.Path("crazycharm.py")
    entrypoint.touch()

    # create a socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind("test-socket")

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=tmp_path / entrypoint,
    )
    builder.handle_generic_paths()

    assert not (build_dir / "test-socket").exists()
    expected = "Ignoring file because of type: 'test-socket'"
    assert_output(expected)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_dispatcher_modern_dispatch_created(tmp_path):
    """The dispatcher script is properly built."""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    linked_entrypoint = build_dir / "somestuff.py"

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    builder.handle_dispatcher(linked_entrypoint)

    included_dispatcher = build_dir / const.DISPATCH_FILENAME
    with included_dispatcher.open("rt", encoding="utf8") as fh:
        dispatcher_code = fh.read()
    assert dispatcher_code == const.DISPATCH_CONTENT.format(
        entrypoint_relative_path="somestuff.py"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_dispatcher_modern_dispatch_respected(tmp_path):
    """The already included dispatcher script is left untouched."""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    already_present_dispatch = build_dir / const.DISPATCH_FILENAME
    with already_present_dispatch.open("wb") as fh:
        fh.write(b"abc")

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    builder.handle_dispatcher("whatever")

    with already_present_dispatch.open("rb") as fh:
        assert fh.read() == b"abc"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_dispatcher_classic_hooks_mandatory_created(tmp_path):
    """The mandatory classic hooks are implemented ok if not present."""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    linked_entrypoint = build_dir / "somestuff.py"
    included_dispatcher = build_dir / const.DISPATCH_FILENAME

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    with patch("charmcraft.const.MANDATORY_HOOK_NAMES", {"testhook"}):
        builder.handle_dispatcher(linked_entrypoint)

    test_hook = build_dir / const.HOOKS_DIRNAME / "testhook"
    assert test_hook.is_symlink()
    assert test_hook.resolve() == included_dispatcher
    assert test_hook.readlink() == pathlib.Path("..", const.DISPATCH_FILENAME)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_dispatcher_classic_hooks_mandatory_respected(tmp_path):
    """The already included mandatory classic hooks are left untouched."""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    built_hooks_dir = build_dir / const.HOOKS_DIRNAME
    built_hooks_dir.mkdir()
    test_hook = built_hooks_dir / "testhook"
    with test_hook.open("wb") as fh:
        fh.write(b"abc")

    linked_entrypoint = build_dir / "somestuff.py"

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    with patch("charmcraft.const.MANDATORY_HOOK_NAMES", {"testhook"}):
        builder.handle_dispatcher(linked_entrypoint)

    with test_hook.open("rb") as fh:
        assert fh.read() == b"abc"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_dispatcher_classic_hooks_linking_charm_replaced(tmp_path, assert_output):
    """Hooks that are just a symlink to the entrypoint are replaced."""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    # simple source code
    src_dir = build_dir / "src"
    src_dir.mkdir()
    built_charm_script = src_dir / "charm.py"
    with built_charm_script.open("wb") as fh:
        fh.write(b"all the magic")

    # a test hook, just a symlink to the charm
    built_hooks_dir = build_dir / const.HOOKS_DIRNAME
    built_hooks_dir.mkdir()
    test_hook = built_hooks_dir / "somehook"
    test_hook.symlink_to(built_charm_script)

    included_dispatcher = build_dir / const.DISPATCH_FILENAME

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    builder.handle_dispatcher(built_charm_script)

    # the test hook is still there and a symlink, but now pointing to the dispatcher
    assert test_hook.is_symlink()
    assert test_hook.resolve() == included_dispatcher
    expected = "Replacing existing hook 'somehook' as it's a symlink to the entrypoint"
    assert_output(expected)


# -- tests about dependencies handling


@pytest.mark.parametrize(
    ("python_packages", "binary_packages", "reqs_contents", "charmlibs", "expected_call_params"),
    [
        pytest.param(
            [],
            [],
            [],
            [],
            [["install", "--no-binary=:all:", "--requirement={reqs_file}"]],
            id="simple",
        ),
        pytest.param(
            ["pkg1", "pkg2"],
            [],
            [],
            [],
            [
                ["install", "--no-binary=:all:", "pkg1", "pkg2"],
                ["install", "--no-binary=:all:", "--requirement={reqs_file}"],
            ],
            id="packages-only",
        ),
        pytest.param(
            [],
            ["bin-pkg1", "bin-pkg2"],
            [],
            [],
            [
                ["install", "bin-pkg1", "bin-pkg2"],
                ["install", "--no-binary=:all:", "--requirement={reqs_file}"],
            ],
            id="binary-packages-only",
        ),
        pytest.param(
            ["pkg1", "pkg2"],
            ["bin-pkg1", "bin-pkg2"],
            [],
            [],
            [
                ["install", "bin-pkg1", "bin-pkg2"],
                ["install", "--no-binary=:all:", "pkg1", "pkg2"],
                ["install", "--no-binary=:all:", "--requirement={reqs_file}"],
            ],
            id="binary-and-source-packages",
        ),
        pytest.param(
            [],
            [],
            ["req1", "req2"],
            [],
            [
                ["install", "--no-binary=:all:", "--requirement={reqs_file}"],
            ],
            id="requirements-only",
        ),
        pytest.param(
            ["req1"],
            ["req2"],
            ["req1", "req2"],
            [],
            [
                ["install", "req2"],
                ["install", "--no-binary=:all:", "req1"],
                ["install", "--no-binary=:all:", "--requirement={reqs_file}"],
            ],
            id="requirements-duplicated-in-charmcraft_yaml",
        ),
        pytest.param(
            [],
            [],
            [],
            ["charmlib-dep"],
            [["install", "--no-binary=:all:", "--requirement={reqs_file}", "charmlib-dep"]],
            id="charmlib-dep-only",
        ),
        pytest.param(
            [],
            [],
            ["charmlib-dep==0.1", "req1"],
            ["charmlib-dep"],
            [["install", "--no-binary=:all:", "--requirement={reqs_file}"]],
            id="charmlib-dep-in-requirements",
        ),
        pytest.param(
            ["duplicate"],
            ["duplicate"],
            ["duplicate"],
            ["duplicate"],
            [
                ["install", "duplicate"],
                ["install", "--no-binary=:all:", "duplicate"],
                ["install", "--no-binary=:all:", "--requirement={reqs_file}"],
            ],
            id="all-same",
        ),
        pytest.param(
            ["duplicate", "pkg1"],
            ["duplicate", "bin-pkg1"],
            ["duplicate", "req1"],
            ["duplicate", "lib-dep"],
            [
                ["install", "bin-pkg1", "duplicate"],
                ["install", "--no-binary=:all:", "duplicate", "pkg1"],
                ["install", "--no-binary=:all:", "--requirement={reqs_file}", "lib-dep"],
            ],
            id="all-overlap",
        ),
    ],
)
def test_build_dependencies_virtualenv(
    tmp_path: pathlib.Path,
    assert_output: Callable,
    python_packages: list[str],
    binary_packages: list[str],
    reqs_contents: list[str],
    charmlibs: list[str],
    expected_call_params,
):
    """A virtualenv is created with the specified requirements file."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    reqs_file = tmp_path / "reqs.txt"
    reqs_file.write_text("\n".join(reqs_contents))

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=binary_packages,
        python_packages=python_packages,
        requirements=[reqs_file],
    )
    builder.charmlib_deps = set(charmlibs)

    with patch("charmcraft.charm_builder.get_pip_version") as mock_pip_version:
        mock_pip_version.return_value = (22, 0)
        with patch("charmcraft.charm_builder._process_run") as mock:
            with patch("shutil.copytree") as mock_copytree:
                builder.handle_dependencies()

    pip_cmd = str(charm_builder._find_venv_bin(tmp_path / const.STAGING_VENV_DIRNAME, "pip"))

    formatted_calls = [
        [param.format(reqs_file=str(reqs_file)) for param in call] for call in expected_call_params
    ]
    extra_pip_calls = [call([pip_cmd, *params]) for params in formatted_calls]

    assert mock.mock_calls == [
        call(["python3", "-m", "venv", str(tmp_path / const.STAGING_VENV_DIRNAME)]),
        call([pip_cmd, "install", f"pip@{KNOWN_GOOD_PIP_URL}"]),
        *extra_pip_calls,
    ]

    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]
    assert_output("Handling dependencies", "Installing dependencies")


def test_build_dependencies_virtualenv_multiple(tmp_path, assert_output):
    """A virtualenv is created with multiple requirements files."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    reqs_file_1 = tmp_path / "reqs.txt"
    reqs_file_1.touch()
    reqs_file_2 = tmp_path / "reqs.txt"
    reqs_file_1.touch()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=[],
        python_packages=[],
        requirements=[reqs_file_1, reqs_file_2],
    )

    with patch("charmcraft.charm_builder.get_pip_version") as mock_pip_version:
        mock_pip_version.return_value = (22, 0)
        with patch("charmcraft.charm_builder._process_run") as mock:
            with patch("shutil.copytree") as mock_copytree:
                builder.handle_dependencies()

    pip_cmd = str(charm_builder._find_venv_bin(tmp_path / const.STAGING_VENV_DIRNAME, "pip"))
    assert mock.mock_calls == [
        call(["python3", "-m", "venv", str(tmp_path / const.STAGING_VENV_DIRNAME)]),
        call([pip_cmd, "install", f"pip@{KNOWN_GOOD_PIP_URL}"]),
        call(
            [
                pip_cmd,
                "install",
                "--no-binary=:all:",
                f"--requirement={reqs_file_1}",
                f"--requirement={reqs_file_2}",
            ]
        ),
    ]

    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]
    assert_output("Handling dependencies", "Installing dependencies")


def test_build_dependencies_virtualenv_none(tmp_path, assert_output):
    """The virtualenv is NOT created if no needed."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=[],
        python_packages=[],
        requirements=[],
    )

    with patch("charmcraft.charm_builder.subprocess.run") as mock_run:
        builder.handle_dependencies()

    mock_run.assert_not_called()
    assert_output("Handling dependencies", "No dependencies to handle")


def test_build_dependencies_no_reused_missing_venv(tmp_path, assert_output):
    """Dependencies are built again because installation dir was not found."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=[],
        python_packages=["ops"],
        requirements=[],
    )
    staging_venv_dir = tmp_path / const.STAGING_VENV_DIRNAME

    # patch the dependencies installation method so it skips all subprocessing but actually
    # creates the directory, to simplify testing
    builder._install_dependencies = lambda dirpath: dirpath.mkdir()

    # first run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies directory not found",
        "Installing dependencies",
    )

    # directory created and packages installed
    assert staging_venv_dir.exists()

    # installation directory copied to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]

    # remove the site venv directory
    staging_venv_dir.rmdir()

    # second run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies directory not found",
        "Installing dependencies",
    )

    # directory created and packages installed *again*
    assert staging_venv_dir.exists()

    # installation directory copied *again* to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]


def test_build_dependencies_no_reused_missing_hash_file(tmp_path, assert_output):
    """Dependencies are built again because previous hash file was not found."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=[],
        python_packages=["ops"],
        requirements=[],
    )
    staging_venv_dir = tmp_path / const.STAGING_VENV_DIRNAME

    # patch the dependencies installation method so it skips all subprocessing but actually
    # creates the directory, to simplify testing
    builder._install_dependencies = lambda dirpath: dirpath.mkdir(exist_ok=True)

    # first run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies directory not found",
        "Installing dependencies",
    )

    # directory created and packages installed
    assert staging_venv_dir.exists()

    # installation directory copied to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]

    # remove the hash file
    (tmp_path / const.DEPENDENCIES_HASH_FILENAME).unlink()

    # second run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies hash file not found",
        "Installing dependencies",
    )

    # directory created and packages installed *again*
    assert staging_venv_dir.exists()

    # installation directory copied *again* to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]


def test_build_dependencies_no_reused_problematic_hash_file(tmp_path, assert_output):
    """Dependencies are built again because having problems to read the previous hash file."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=[],
        python_packages=["ops"],
        requirements=[],
    )
    staging_venv_dir = tmp_path / const.STAGING_VENV_DIRNAME

    # patch the dependencies installation method so it skips all subprocessing but actually
    # creates the directory, to simplify testing
    builder._install_dependencies = lambda dirpath: dirpath.mkdir(exist_ok=True)

    # first run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies directory not found",
        "Installing dependencies",
    )

    # directory created and packages installed
    assert staging_venv_dir.exists()

    # installation directory copied to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]

    # avoid the file to be read successfully
    (tmp_path / const.DEPENDENCIES_HASH_FILENAME).write_bytes(b"\xc3\x28")  # invalid UTF8

    # second run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Problems reading the dependencies hash file: "
        "'utf-8' codec can't decode byte 0xc3 in position 0: invalid continuation byte",
        "Installing dependencies",
    )

    # directory created and packages installed *again*
    assert staging_venv_dir.exists()

    # installation directory copied *again* to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]


@pytest.mark.parametrize(
    ("new_reqs_content", "new_pypackages", "new_pybinaries", "new_charmlibdeps"),
    [
        ("ops==2", None, None, None),
        (None, ["foo2", "bar"], None, None),
        (None, None, ["otherbinthing"], None),
        (None, None, None, {"bazooka"}),
    ],
)
def test_build_dependencies_no_reused_different_dependencies(
    tmp_path,
    assert_output,
    new_reqs_content,
    new_pypackages,
    new_pybinaries,
    new_charmlibdeps,
):
    """Dependencies are built again because changed from previous run."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    # prepare some dependencies for the first call (and some content for the second one)
    reqs_file = tmp_path / "requirements.txt"
    reqs_file.write_text("ops==1")
    requirements = [reqs_file]
    python_packages = ["foo", "bar"]
    binary_python_packages = ["binthing"]
    charmlib_deps = {"baz"}

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=binary_python_packages,
        python_packages=python_packages,
        requirements=requirements,
    )
    builder.charmlib_deps = charmlib_deps
    staging_venv_dir = tmp_path / const.STAGING_VENV_DIRNAME

    # patch the dependencies installation method so it skips all subprocessing but actually
    # creates the directory, to simplify testing
    builder._install_dependencies = lambda dirpath: dirpath.mkdir(exist_ok=True)

    # first run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies directory not found",
        "Installing dependencies",
    )

    # directory created and packages installed
    assert staging_venv_dir.exists()

    # installation directory copied to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]

    # for the second call, default new dependencies to first ones so only one is changed at a time
    if new_reqs_content is not None:
        reqs_file.write_text(new_reqs_content)
    if new_pypackages is None:
        new_pypackages = python_packages
    if new_pybinaries is None:
        new_pybinaries = binary_python_packages
    if new_charmlibdeps is None:
        new_charmlibdeps = charmlib_deps

    # second run with other dependencies!
    builder.binary_python_packages = new_pybinaries
    builder.python_packages = new_pypackages
    builder.charmlib_deps = new_charmlibdeps
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output("Handling dependencies", "Installing dependencies")

    # directory created and packages installed *again*
    assert staging_venv_dir.exists()

    # installation directory copied *again* to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]


def test_build_dependencies_reused(tmp_path, assert_output):
    """Happy case to reuse dependencies from last run."""
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    reqs_file = tmp_path / "reqs.txt"
    reqs_file.touch()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
        binary_python_packages=[],
        python_packages=[],
        requirements=[reqs_file],
    )
    staging_venv_dir = tmp_path / const.STAGING_VENV_DIRNAME

    # patch the dependencies installation method so it skips all subprocessing but actually
    # creates the directory, to simplify testing; note that we specifically are calling mkdir
    # to fail if the directory is already there, so we ensure it is called once
    builder._install_dependencies = lambda dirpath: dirpath.mkdir(exist_ok=False)

    # first run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Dependencies directory not found",
        "Installing dependencies",
    )

    # directory created and packages installed
    assert staging_venv_dir.exists()

    # installation directory copied to the build directory
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]

    # second run!
    with patch("shutil.copytree") as mock_copytree:
        builder.handle_dependencies()
    assert_output(
        "Handling dependencies",
        "Reusing installed dependencies, they are equal to last run ones",
    )

    # installation directory copied *again* to the build directory (this is always done as
    # buildpath is cleaned)
    site_packages_dir = charm_builder._find_venv_site_packages(
        pathlib.Path(const.STAGING_VENV_DIRNAME)
    )
    assert mock_copytree.mock_calls == [call(site_packages_dir, build_dir / const.VENV_DIRNAME)]


# -- tests about juju ignore


def test_builder_without_jujuignore(tmp_path):
    """Without a .jujuignore we still have a default set of ignores"""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
        entrypoint=pathlib.Path("whatever"),
    )
    ignore = builder._load_juju_ignore()
    assert ignore.match("/.git", is_dir=True)
    assert ignore.match("/build", is_dir=True)
    assert not ignore.match("myfile.py", is_dir=False)


def test_builder_with_jujuignore(tmp_path):
    """With a .jujuignore we will include additional ignores."""
    metadata = tmp_path / const.METADATA_FILENAME
    metadata.write_text("name: crazycharm")
    build_dir = tmp_path / const.BUILD_DIRNAME
    build_dir.mkdir()
    with (tmp_path / ".jujuignore").open("w", encoding="utf-8") as ignores:
        ignores.write("*.py\n/h\xef.txt\n")

    builder = CharmBuilder(
        builddir=tmp_path,
        installdir=build_dir,
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
        assert self.builddir == pathlib.Path("builddir")
        assert self.installdir == pathlib.Path("installdir")
        assert self.entrypoint == pathlib.Path("src/charm.py")
        assert self.requirement_paths == []
        sys.exit(42)

    fake_argv = ["cmd", "--builddir", "builddir", "--installdir", "installdir"]
    with patch.object(sys, "argv", fake_argv):
        with patch("charmcraft.charm_builder.CharmBuilder.build_charm", new=mock_build_charm):
            with patch("charmcraft.charm_builder.collect_charmlib_pydeps") as mock_collect_pydeps:
                with pytest.raises(SystemExit) as raised:
                    charm_builder.main()
        assert raised.value.code == 42
    mock_collect_pydeps.assert_called_with(pathlib.Path("builddir"))


def test_builder_arguments_full(tmp_path):
    """The arguments passed to the cli must be correctly parsed."""

    def mock_build_charm(self):
        assert self.builddir == pathlib.Path("builddir")
        assert self.installdir == pathlib.Path("installdir")
        assert self.entrypoint == pathlib.Path("src/charm.py")
        assert self.requirement_paths == [
            pathlib.Path("reqs1.txt"),
            pathlib.Path("reqs2.txt"),
        ]
        sys.exit(42)

    fake_argv = ["cmd", "--builddir", "builddir", "--installdir", "installdir"]
    fake_argv += ["-rreqs1.txt", "--requirement", "reqs2.txt"]
    with patch.object(sys, "argv", fake_argv):
        with patch("charmcraft.charm_builder.CharmBuilder.build_charm", new=mock_build_charm):
            with patch("charmcraft.charm_builder.collect_charmlib_pydeps") as mock_collect_pydeps:
                with pytest.raises(SystemExit) as raised:
                    charm_builder.main()
        assert raised.value.code == 42
    mock_collect_pydeps.assert_called_with(pathlib.Path("builddir"))


# --- subprocess runner tests


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_processrun_base(assert_output):
    """Basic execution."""
    cmd = ["echo", "HELO"]
    _process_run(cmd)
    assert_output(
        "Running external command ['echo', 'HELO']",
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_processrun_stdout_logged(assert_output):
    """The standard output is logged in debug."""
    cmd = ["echo", "HELO"]
    _process_run(cmd)
    assert_output(
        "Running external command ['echo', 'HELO']",
        "   :: HELO",
    )


def test_processrun_stderr_logged(assert_output):
    """The standard error is logged in debug."""
    cmd = [sys.executable, "-c", "import sys; print('weird, huh?', file=sys.stderr)"]
    _process_run(cmd)
    assert_output(
        "Running external command " + str(cmd),
        "   :: weird, huh?",
    )


def test_processrun_failed():
    """It's logged in error if subprocess is run but ends with return code not zero."""
    cmd = [sys.executable, "-c", "exit(3)"]
    with pytest.raises(RuntimeError) as cm:
        _process_run(cmd)
    assert str(cm.value) == f"Subprocess command {cmd} execution failed with retcode 3"


def test_processrun_crashed(tmp_path):
    """It's logged in error if the subprocess fails to even run."""
    nonexistent = tmp_path / "whatever"
    cmd = [str(nonexistent)]
    with pytest.raises(RuntimeError) as cm:
        _process_run(cmd)

    # get a real exception to build the message as its internal text varies across OSes
    try:
        subprocess.run([nonexistent], check=True)
    except Exception as exc:
        exc_text = repr(exc)

    assert str(cm.value) == f"Subprocess command {cmd} execution crashed: {exc_text}"


# --- helper tests


@pytest.mark.parametrize(
    ("platform", "result"),
    [
        ("win32", "/basedir/Scripts/cmd.exe"),
        ("linux", "/basedir/bin/cmd"),
        ("darwin", "/basedir/bin/cmd"),
    ],
)
def test_find_venv_bin(monkeypatch, platform, result):
    monkeypatch.setattr(sys, "platform", platform)
    basedir = pathlib.Path("/basedir")
    venv_bin = charm_builder._find_venv_bin(basedir, "cmd")
    assert venv_bin.as_posix() == result


@pytest.mark.parametrize(
    ("platform", "result"),
    [
        ("win32", "/basedir/PythonXY/site-packages"),
        ("linux", "/basedir/lib/pythonX.Y/site-packages"),
        ("darwin", "/basedir/lib/pythonX.Y/site-packages"),
    ],
)
def test_find_venv_site_packages(monkeypatch, platform, result):
    monkeypatch.setattr(sys, "platform", platform)
    basedir = pathlib.Path("/basedir")
    with patch("subprocess.check_output", return_value="X Y") as mock_run:
        site_packages_dir = charm_builder._find_venv_site_packages(basedir)
    assert mock_run.mock_calls == [
        call(
            [
                "python3",
                "-c",
                "import sys; v=sys.version_info; print(f'{v.major} {v.minor}')",
            ],
            text=True,
        )
    ]
    assert site_packages_dir.as_posix() == result
