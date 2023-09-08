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

import datetime
import os
import pathlib
import sys
import tempfile
import zipfile
from textwrap import dedent
from unittest.mock import call, patch

import dateutil.parser
import pytest
import yaml
from craft_cli import CraftError

from charmcraft.errors import DuplicateCharmsError, InvalidCharmPathError
from charmcraft.utils import (
    ResourceOption,
    SingleOptionEnsurer,
    build_zip,
    confirm_with_user,
    exclude_packages,
    find_charm_sources,
    format_timestamp,
    get_charm_name_from_path,
    get_host_architecture,
    get_os_platform,
    get_package_names,
    get_pip_command,
    get_pip_version,
    get_pypi_packages,
    humanize_list,
    load_yaml,
    make_executable,
    useful_filepath,
)


@pytest.fixture()
def mock_isatty():
    with patch("charmcraft.utils.sys.stdin.isatty", return_value=True) as mock_isatty:
        yield mock_isatty


@pytest.fixture()
def mock_input():
    with patch("charmcraft.utils.input", return_value="") as mock_input:
        yield mock_input


@pytest.fixture()
def mock_is_charmcraft_running_in_managed_mode():
    with patch(
        "charmcraft.utils.is_charmcraft_running_in_managed_mode", return_value=False
    ) as mock_managed:
        yield mock_managed


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_make_executable_read_bits(tmp_path):
    pth = tmp_path / "test"
    pth.touch(mode=0o640)
    # validity check
    assert pth.stat().st_mode & 0o777 == 0o640
    with pth.open() as fd:
        make_executable(fd)
        # only read bits got made executable
        assert pth.stat().st_mode & 0o777 == 0o750


def test_load_yaml_success(tmp_path):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text(
        """
        foo: 33
    """
    )
    content = load_yaml(test_file)
    assert content == {"foo": 33}


def test_load_yaml_no_file(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    content = load_yaml(test_file)
    assert content is None

    expected = f"Couldn't find config file {str(test_file)!r}"
    emitter.assert_debug(expected)


def test_load_yaml_directory(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    test_file.mkdir()
    content = load_yaml(test_file)
    assert content is None

    expected = f"Couldn't find config file {str(test_file)!r}"
    emitter.assert_debug(expected)


def test_load_yaml_corrupted_format(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text(
        """
        foo: [1, 2
    """
    )
    content = load_yaml(test_file)
    assert content is None

    expected = "Failed to read/parse config file.*testfile.yaml.*ParserError.*"
    emitter.assert_debug(expected, regex=True)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_load_yaml_file_problem(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text(
        """
        foo: bar
    """
    )
    test_file.chmod(0o000)
    content = load_yaml(test_file)
    assert content is None

    expected = f"Failed to read/parse config file {str(test_file)!r}.*PermissionError.*"
    emitter.assert_debug(expected, regex=True)


# -- tests for the SingleOptionEnsurer helper class


def test_singleoptionensurer_convert_ok():
    """Work fine with one call, convert as expected."""
    soe = SingleOptionEnsurer(int)
    assert soe("33") == 33


def test_singleoptionensurer_too_many():
    """Raise an error after one ok call."""
    soe = SingleOptionEnsurer(int)
    assert soe("33") == 33
    with pytest.raises(ValueError) as cm:
        soe("33")
    assert str(cm.value) == "the option can be specified only once"


# -- tests for the ResourceOption helper class


def test_resourceoption_convert_ok():
    """Convert as expected."""
    r = ResourceOption()("foo:13")
    assert r.name == "foo"
    assert r.revision == 13


@pytest.mark.parametrize(
    "value",
    [
        "foo15",  # no separation
        "foo:",  # no revision
        "foo:x3",  # no int
        "foo:-1",  # negative revisions are not allowed
        ":15",  # no name
        "  :15",  # no name, really!
        "foo:bar:15",  # invalid name, anyway
    ],
)
def test_resourceoption_convert_error(value):
    """Error while converting."""
    with pytest.raises(ValueError) as cm:
        ResourceOption()(value)
    assert str(cm.value) == (
        "the resource format must be <name>:<revision> (revision being a non-negative integer)"
    )


# -- tests for the useful_filepath helper


def test_usefulfilepath_pathlib(tmp_path):
    """Convert the string to Path."""
    test_file = tmp_path / "testfile.bin"
    test_file.touch()
    path = useful_filepath(str(test_file))
    assert path == test_file
    assert isinstance(path, pathlib.Path)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_usefulfilepath_home_expanded(tmp_path, monkeypatch):
    """Home-expand the indicated path."""
    fake_home = tmp_path / "homedir"
    fake_home.mkdir()
    test_file = fake_home / "testfile.bin"
    test_file.touch()

    monkeypatch.setitem(os.environ, "HOME", str(fake_home))
    path = useful_filepath("~/testfile.bin")
    assert path == test_file


def test_usefulfilepath_missing():
    """The indicated path is not there."""
    with pytest.raises(CraftError) as cm:
        useful_filepath("not_really_there.txt")
    assert str(cm.value) == "Cannot access 'not_really_there.txt'."


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_usefulfilepath_inaccessible(tmp_path):
    """The indicated path is not readable."""
    test_file = tmp_path / "testfile.bin"
    test_file.touch(mode=0o000)
    with pytest.raises(CraftError) as cm:
        useful_filepath(str(test_file))
    assert str(cm.value) == f"Cannot access {str(test_file)!r}."


def test_usefulfilepath_not_a_file(tmp_path):
    """The indicated path is not a file."""
    with pytest.raises(CraftError) as cm:
        useful_filepath(str(tmp_path))
    assert str(cm.value) == f"{str(tmp_path)!r} is not a file."


# -- tests for the OS platform getter


def test_get_os_platform_linux(tmp_path):
    """Utilize an /etc/os-release file to determine platform."""
    # explicitly add commented and empty lines, for parser robustness
    filepath = tmp_path / "os-release"
    filepath.write_text(
        dedent(
            """
        # the following is an empty line

        NAME="Ubuntu"
        VERSION="20.04.1 LTS (Focal Fossa)"
        ID=ubuntu
        ID_LIKE=debian
        PRETTY_NAME="Ubuntu 20.04.1 LTS"
        VERSION_ID="20.04"
        HOME_URL="https://www.ubuntu.com/"
        SUPPORT_URL="https://help.ubuntu.com/"
        BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"

        # more in the middle; the following even would be "out of standard", but
        # we should not crash, just ignore it
        SOMETHING-WEIRD

        PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
        VERSION_CODENAME=focal
        UBUNTU_CODENAME=focal
        """
        )
    )
    with patch("platform.machine", return_value="x86_64"):
        with patch("platform.system", return_value="Linux"):
            os_platform = get_os_platform(filepath)
    assert os_platform.system == "ubuntu"
    assert os_platform.release == "20.04"
    assert os_platform.machine == "x86_64"


def test_get_os_platform_strict_snaps(tmp_path):
    """Utilize an /etc/os-release file to determine platform, core-20 values."""
    # explicitly add commented and empty lines, for parser robustness
    filepath = tmp_path / "os-release"
    filepath.write_text(
        dedent(
            """
        NAME="Ubuntu Core"
        VERSION="20"
        ID=ubuntu-core
        PRETTY_NAME="Ubuntu Core 20"
        VERSION_ID="20"
        HOME_URL="https://snapcraft.io/"
        BUG_REPORT_URL="https://bugs.launchpad.net/snappy/"
        """
        )
    )
    with patch("platform.machine", return_value="x86_64"):
        with patch("platform.system", return_value="Linux"):
            os_platform = get_os_platform(filepath)
    assert os_platform.system == "ubuntu-core"
    assert os_platform.release == "20"
    assert os_platform.machine == "x86_64"


@pytest.mark.parametrize(
    "name",
    [
        ('"foo bar"', "foo bar"),  # what's normally found
        ("foo bar", "foo bar"),  # no quotes
        ('"foo " bar"', 'foo " bar'),  # quotes in the middle
        ('foo bar"', 'foo bar"'),  # unbalanced quotes (no really enclosing)
        ('"foo bar', '"foo bar'),  # unbalanced quotes (no really enclosing)
        ("'foo bar'", "foo bar"),  # enclosing with single quote
        ("'foo ' bar'", "foo ' bar"),  # single quote in the middle
        ("foo bar'", "foo bar'"),  # unbalanced single quotes (no really enclosing)
        ("'foo bar", "'foo bar"),  # unbalanced single quotes (no really enclosing)
        ("'foo bar\"", "'foo bar\""),  # unbalanced mixed quotes
        ("\"foo bar'", "\"foo bar'"),  # unbalanced mixed quotes
    ],
)
def test_get_os_platform_alternative_formats(name, tmp_path):
    """Support different ways of building the string."""
    source, result = name
    filepath = tmp_path / "os-release"
    filepath.write_text(
        dedent(
            f"""
        ID={source}
        VERSION_ID="20.04"
        """
        )
    )
    # need to patch this to "Linux" so actually uses /etc/os-release...
    with patch("platform.system", return_value="Linux"):
        os_platform = get_os_platform(filepath)
    assert os_platform.system == result


def test_get_os_platform_windows():
    """Get platform from a patched Windows machine."""
    with patch("platform.system", return_value="Windows"):
        with patch("platform.release", return_value="10"):
            with patch("platform.machine", return_value="AMD64"):
                os_platform = get_os_platform()
    assert os_platform.system == "Windows"
    assert os_platform.release == "10"
    assert os_platform.machine == "AMD64"


@pytest.mark.parametrize(
    ("platform_arch", "deb_arch"),
    [
        ("AMD64", "amd64"),
        ("aarch64", "arm64"),
        ("armv7l", "armhf"),
        ("ppc", "powerpc"),
        ("ppc64le", "ppc64el"),
        ("x86_64", "amd64"),
        ("unknown-arch", "unknown-arch"),
    ],
)
def test_get_host_architecture(platform_arch, deb_arch):
    """Test all platform mappings in addition to unknown."""
    with patch("platform.machine", return_value=platform_arch):
        assert get_host_architecture() == deb_arch


def test_confirm_with_user_defaults_with_tty(mock_input, mock_isatty):
    mock_input.return_value = ""
    mock_isatty.return_value = True

    assert confirm_with_user("prompt", default=True) is True
    assert mock_input.mock_calls == [call("prompt [Y/n]: ")]
    mock_input.reset_mock()

    assert confirm_with_user("prompt", default=False) is False
    assert mock_input.mock_calls == [call("prompt [y/N]: ")]


def test_confirm_with_user_defaults_without_tty(mock_input, mock_isatty):
    mock_isatty.return_value = False

    assert confirm_with_user("prompt", default=True) is True
    assert confirm_with_user("prompt", default=False) is False

    assert mock_input.mock_calls == []


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ("y", True),
        ("Y", True),
        ("yes", True),
        ("YES", True),
        ("n", False),
        ("N", False),
        ("no", False),
        ("NO", False),
    ],
)
def test_confirm_with_user(user_input, expected, mock_input, mock_isatty):
    mock_input.return_value = user_input

    assert confirm_with_user("prompt") == expected
    assert mock_input.mock_calls == [call("prompt [y/N]: ")]


def test_confirm_with_user_errors_in_managed_mode(mock_is_charmcraft_running_in_managed_mode):
    mock_is_charmcraft_running_in_managed_mode.return_value = True

    with pytest.raises(RuntimeError):
        confirm_with_user("prompt")


def test_confirm_with_user_pause_emitter(mock_isatty, emitter):
    """The emitter should be paused when using the terminal."""
    mock_isatty.return_value = True

    def fake_input(prompt):
        """Check if the Emitter is paused."""
        assert emitter.paused
        return ""

    with patch("charmcraft.utils.input", fake_input):
        confirm_with_user("prompt")


def test_timestampstr_simple():
    """Converts a timestamp without timezone."""
    source = datetime.datetime(2020, 7, 3, 20, 30, 40)
    result = format_timestamp(source)
    assert result == "2020-07-03T20:30:40Z"


def test_timestampstr_utc():
    """Converts a timestamp with UTC timezone."""
    source = dateutil.parser.parse("2020-07-03T20:30:40Z")
    result = format_timestamp(source)
    assert result == "2020-07-03T20:30:40Z"


def test_timestampstr_nonutc():
    """Converts a timestamp with other timezone."""
    source = dateutil.parser.parse("2020-07-03T20:30:40+03:00")
    result = format_timestamp(source)
    assert result == "2020-07-03T17:30:40Z"


# -- tests for humanizing list joins


@pytest.mark.parametrize(
    ("items", "conjunction", "expected"),
    (
        (["foo"], "xor", "'foo'"),
        (["foo", "bar"], "xor", "'bar' xor 'foo'"),
        (["foo", "bar", "baz"], "xor", "'bar', 'baz' xor 'foo'"),
        (["foo", "bar", "baz", "qux"], "xor", "'bar', 'baz', 'foo' xor 'qux'"),
    ),
)
def test_humanize_list_ok(items, conjunction, expected):
    """Several successful cases."""
    assert humanize_list(items, conjunction) == expected


def test_humanize_list_empty():
    """Calling to humanize an empty list is an error that should be explicit."""
    with pytest.raises(ValueError):
        humanize_list([], "whatever")


# region tests for zip builder
def test_zipbuild_simple(tmp_path):
    """Build a bunch of files in the zip."""
    build_dir = tmp_path / "somedir"
    build_dir.mkdir()

    testfile1 = build_dir / "foo.txt"
    testfile1.write_bytes(b"123\x00456")
    subdir = build_dir / "bar"
    subdir.mkdir()
    testfile2 = subdir / "baz.txt"
    testfile2.write_bytes(b"mo\xc3\xb1o")

    zip_filepath = tmp_path / "testresult.zip"
    build_zip(zip_filepath, build_dir)

    zf = zipfile.ZipFile(zip_filepath)
    assert sorted(x.filename for x in zf.infolist()) == ["bar/baz.txt", "foo.txt"]
    assert zf.read("foo.txt") == b"123\x00456"
    assert zf.read("bar/baz.txt") == b"mo\xc3\xb1o"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_zipbuild_symlink_simple(tmp_path):
    """Symlinks are supported."""
    build_dir = tmp_path / "somedir"
    build_dir.mkdir()

    testfile1 = build_dir / "real.txt"
    testfile1.write_bytes(b"123\x00456")
    testfile2 = build_dir / "link.txt"
    testfile2.symlink_to(testfile1)

    zip_filepath = tmp_path / "testresult.zip"
    build_zip(zip_filepath, build_dir)

    zf = zipfile.ZipFile(zip_filepath)
    assert sorted(x.filename for x in zf.infolist()) == ["link.txt", "real.txt"]
    assert zf.read("real.txt") == b"123\x00456"
    assert zf.read("link.txt") == b"123\x00456"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_zipbuild_symlink_outside(tmp_path):
    """No matter where the symlink points to."""
    # outside the build dir
    testfile1 = tmp_path / "real.txt"
    testfile1.write_bytes(b"123\x00456")

    # inside the build dir
    build_dir = tmp_path / "somedir"
    build_dir.mkdir()
    testfile2 = build_dir / "link.txt"
    testfile2.symlink_to(testfile1)

    zip_filepath = tmp_path / "testresult.zip"
    build_zip(zip_filepath, build_dir)

    zf = zipfile.ZipFile(zip_filepath)
    assert sorted(x.filename for x in zf.infolist()) == ["link.txt"]
    assert zf.read("link.txt") == b"123\x00456"


# endregion
# region Tests for find_charm_sources
BASIC_CHARM_MAP = {
    "charm1": pathlib.Path("charms/charm1/"),
    "charm2": pathlib.Path("charms/charm2/"),
    "operator1": pathlib.Path("operators/operator1"),
    "operator2": pathlib.Path("operators/operator2"),
    "basic": pathlib.Path("basic"),
    "basic2": pathlib.Path("basic2"),
}


def test_find_charm_sources_empty_directory(tmp_path):
    actual = find_charm_sources(tmp_path, ["a", "b", "c"])

    assert actual == {}


@pytest.mark.parametrize("fake_charms", [BASIC_CHARM_MAP])
def test_find_charm_sources_finds_values(tmp_path, fake_charms, build_charm_directory):
    expected = build_charm_directory(tmp_path, fake_charms)

    actual = find_charm_sources(tmp_path, fake_charms.keys())

    assert actual == expected


@pytest.mark.parametrize(
    "fake_charms",
    [{"basic": pathlib.Path("charms/basic"), "basic2": pathlib.Path("charms/basic2")}],
)
def test_find_charm_sources_with_symlinks(tmp_path, build_charm_directory, fake_charms):
    symlinks_path = tmp_path / "operators"
    symlinks_path.mkdir()
    expected = build_charm_directory(tmp_path, fake_charms)
    for name, path in fake_charms.items():
        (symlinks_path / name).symlink_to(tmp_path / path, target_is_directory=True)

    actual = find_charm_sources(tmp_path, fake_charms)

    assert actual == expected


@pytest.mark.parametrize("fake_charms", [BASIC_CHARM_MAP])
def test_find_charm_sources_extra_charms(tmp_path, build_charm_directory, fake_charms):
    expected = build_charm_directory(tmp_path, fake_charms)
    invalid_charm = tmp_path / "charms/invalid"
    build_charm_directory(tmp_path, {"invalid": invalid_charm})

    actual = find_charm_sources(tmp_path, fake_charms)

    assert actual == expected


@pytest.mark.parametrize("fake_charms", [BASIC_CHARM_MAP])
def test_find_charm_sources_non_matching_path(tmp_path, build_charm_directory, fake_charms):
    charms = {name: path.with_name(f"non_matching_{name}") for name, path in fake_charms.items()}
    build_charm_directory(tmp_path, charms)

    actual = find_charm_sources(tmp_path, fake_charms)

    assert actual == {}


def test_find_charm_sources_duplicates(check, tmp_path, build_charm_directory):
    fake_charms = {"charm1": pathlib.Path("charm1")}
    build_charm_directory(tmp_path, fake_charms)
    build_charm_directory(tmp_path, {"charm1": pathlib.Path("charms/charm1")})
    build_charm_directory(tmp_path, {"charm1": pathlib.Path("operators/charm1")})
    expected = DuplicateCharmsError(
        {
            "charm1": [
                pathlib.Path("charm1"),
                pathlib.Path("charms/charm1"),
                pathlib.Path("operators/charm1"),
            ]
        }
    )

    with pytest.raises(DuplicateCharmsError) as exc_info:
        find_charm_sources(tmp_path, fake_charms)

    check.equal(exc_info.value.args, expected.args)
    check.equal(exc_info.value.resolution, expected.resolution)


# endregion
# region Tests for get_charm_name_from_path
@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("test1", "test1"),
        ("test1", "charms/test1"),
        ("test1", "operators/test1"),
    ],
)
def test_get_charm_name_from_path_success(tmp_path, build_charm_directory, name, path):
    build_charm_directory(tmp_path, {name: path})

    actual = get_charm_name_from_path(tmp_path / path)

    assert actual == name


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("test1", "test1"),
        ("test1", "charms/test1"),
        ("test1", "operators/test1"),
    ],
)
def test_get_charm_name_from_path_bundle(tmp_path, build_charm_directory, name, path):
    build_charm_directory(tmp_path, {name: path}, file_type="bundle")
    full_path = tmp_path / path

    with pytest.raises(InvalidCharmPathError) as exc_info:
        get_charm_name_from_path(full_path)

    assert exc_info.value.args[0] == f"Path does not contain source for a valid charm: {full_path}"


@pytest.mark.parametrize(
    ("name", "path", "del_file"),
    [
        ("test1", "test1", "charmcraft.yaml"),
        ("test1", "charms/test1", "metadata.yaml"),
        ("test1", "operators/test1", "charmcraft.yaml"),
    ],
)
def test_get_charm_name_from_path_missing_file(
    tmp_path, build_charm_directory, name, path, del_file
):
    build_charm_directory(tmp_path, {name: path})
    full_path = tmp_path / path
    (full_path / del_file).unlink()

    with pytest.raises(InvalidCharmPathError) as exc_info:
        get_charm_name_from_path(full_path)

    assert exc_info.value.args[0] == f"Path does not contain source for a valid charm: {full_path}"


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("test1", "test1"),
        ("test1", "charms/test1"),
        ("test1", "operators/test1"),
    ],
)
def test_get_charm_name_from_path_wrong_name(tmp_path, build_charm_directory, name, path):
    build_charm_directory(tmp_path, {name: path}, file_type="bundle")
    full_path = tmp_path / path
    with (full_path / "metadata.yaml").open("w") as file:
        yaml.safe_dump({"naam": "not a name"}, file)

    with pytest.raises(InvalidCharmPathError) as exc_info:
        get_charm_name_from_path(full_path)

    assert exc_info.value.args[0] == f"Path does not contain source for a valid charm: {full_path}"


# endregion
# region Tests for pip-related functions.


@pytest.mark.parametrize(
    ("requirements", "expected"),
    [
        pytest.param([], set(), id="empty"),
        pytest.param(["abc==1.0.0"], {"abc==1.0.0"}, id="simple"),
        pytest.param(["-e ."], set(), id="editable-ignored"),
    ],
)
def test_get_pypi_packages(requirements, expected):
    assert get_pypi_packages(requirements) == expected


@pytest.mark.parametrize(
    ("packages", "expected"),
    [
        # Specifiers from pep440: https://peps.python.org/pep-0440/#version-specifiers
        pytest.param({"abc"}, {"abc"}, id="no-version"),
        pytest.param({"abc==1.0.0"}, {"abc"}, id="version-matching"),
        pytest.param({"abc >= 1.0.0"}, {"abc"}, id="inclusive-ordered-gt"),
        pytest.param({"abc<= 1.0.0"}, {"abc"}, id="inclusive-ordered-lt"),
        pytest.param({"abc ~= 1.0"}, {"abc"}, id="compatible-release"),
        pytest.param({"abc===foobar"}, {"abc"}, id="arbitrary-equality"),
        pytest.param({"abc >=1.0,<2.0, !=1.2.3.*"}, {"abc"}, id="compound-specifier"),
    ],
)
def test_get_package_names(packages, expected):
    assert get_package_names(packages) == expected


@pytest.mark.parametrize(
    ("requirements", "excluded", "expected"),
    [
        pytest.param(set(), set(), set(), id="empty"),
        pytest.param({"abc==1.0.0"}, {"abc"}, set(), id="make-empty"),
        pytest.param({"abc==1.0.0", "def==1.2.3"}, {"abc"}, {"def==1.2.3"}, id="remove-one"),
        pytest.param({"abc==1.0.0"}, {"invalid"}, {"abc==1.0.0"}, id="irrelevant-exclusion"),
    ],
)
def test_exclude_packages(requirements, excluded, expected):
    assert exclude_packages(requirements, excluded=excluded) == expected


@pytest.mark.parametrize(
    (
        "requirements",
        "source_deps",
        "binary_deps",
        "expected_no_binary",
        "expected_other_packages",
    ),
    [
        (["abc==1.0.0", "def>=1.2.3"], [], ["def"], "--no-binary=abc", []),
        (
            ["abc==1.0", "def>=1.2.3"],
            ["ghi"],
            ["def", "jkl"],
            "--no-binary=abc,ghi",
            ["ghi", "jkl"],
        ),
    ],
)
@pytest.mark.parametrize("prefix", [["/bin/pip"], ["/some/path/to/pip3"], ["pip", "--some-param"]])
def test_get_pip_command(
    prefix, requirements, source_deps, binary_deps, expected_no_binary, expected_other_packages
):
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = pathlib.Path(tmp_dir, "requirements.txt")
        path.write_text("\n".join(requirements))

        command = get_pip_command(prefix, [path], source_deps=source_deps, binary_deps=binary_deps)
        assert command[: len(prefix)] == prefix
        actual_no_binary, actual_requirement, *actual_other_packgaes = command[len(prefix) :]
        assert actual_no_binary == expected_no_binary
        assert actual_other_packgaes == expected_other_packages
        assert actual_requirement == f"--requirement={path}"


@pytest.mark.parametrize(
    ("pip_cmd", "stdout", "expected"),
    [("pip", "pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)\n", (22, 0, 2))],
)
def test_get_pip_version_success(
    fake_process,
    pip_cmd,
    stdout,
    expected,
):
    fake_process.register([pip_cmd, "--version"], stdout=stdout)

    assert get_pip_version(pip_cmd) == expected


@pytest.mark.parametrize(
    ("pip_cmd", "stdout", "error_msg"),
    [
        ("pip", "pip?", "Unknown pip version"),
        ("pip", "pip 1.0.0-dev0-yolo", "Unknown pip version 1.0.0-dev0-yolo"),
    ],
)
def test_get_pip_version_parsing_failure(fake_process, pip_cmd, stdout, error_msg):
    fake_process.register([pip_cmd, "--version"], stdout=stdout)

    with pytest.raises(ValueError) as exc_info:
        get_pip_version(pip_cmd)

    assert exc_info.value.args[0] == error_msg


# endregion
