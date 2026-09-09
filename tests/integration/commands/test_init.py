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
"""Tests for init command."""

import argparse
import contextlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
from unittest import mock

import craft_application
import pytest
import pytest_check
import yaml
from craft_application.errors import InitError

import charmcraft
import charmcraft.application
from charmcraft import errors, services
from charmcraft.application.commands import init
from charmcraft.utils import S_IXALL

with contextlib.suppress(ImportError):
    import pwd

BASIC_INIT_FILES = frozenset(
    pathlib.Path(p)
    for p in (
        ".gitignore",
        "charmcraft.yaml",
        "CONTRIBUTING.md",
        "LICENSE",
        "pyproject.toml",
        "README.md",
        "src",
        "src/charm.py",
        "tests",
        "tests/integration",
        "tests/integration/conftest.py",
        "tests/integration/test_charm.py",
        "tests/unit",
        "tests/unit/test_charm.py",
        "tox.ini",
    )
)
UNKNOWN_AUTHOR_REGEX = re.compile(
    r"^Unable to automatically determine author's name, specify it with --author$"
)
BAD_CHARM_NAME_REGEX = re.compile(
    r" is not a valid charm name. The name must start with a lowercase letter and contain only alphanumeric characters and hyphens.$",
)
VALID_AUTHORS = [
    pytest.param("Author McAuthorFace", id="ascii-author"),
    pytest.param("فلانة الفلانية", id="non-ascii-author"),
]
FRAMEWORK_PROFILES = [
    "django-framework",
    "expressjs-framework",
    "fastapi-framework",
    "flask-framework",
    "go-framework",
    "spring-boot-framework",
]
ALL_PROFILES = [
    *FRAMEWORK_PROFILES,
    "kubernetes",
    "machine",
    "test-kubernetes",
    "test-machine",
]


@pytest.fixture
def init_command():
    services.register_services()
    service_factory = craft_application.ServiceFactory(
        app=charmcraft.application.APP_METADATA
    )
    return init.InitCommand(
        {
            "app": charmcraft.application.APP_METADATA,
            "services": service_factory,
        }
    )


def create_namespace(
    *,
    name="my-charm",
    author="J Doe",
    force=False,
    profile=init.DEFAULT_PROFILE,
    base=None,
    project_dir: pathlib.Path | None = None,
    project_dir_option: pathlib.Path | None = None,
):
    """Helper to create a valid namespace."""
    if project_dir is None:
        project_dir = pathlib.Path.cwd()
    return argparse.Namespace(
        name=name,
        author=author,
        force=force,
        profile=profile,
        base=base,
        project_dir=project_dir,
        project_dir_option=project_dir_option,
    )


@pytest.mark.parametrize(
    ("profile", "base_expected_files", "has_workload_module"),
    [
        pytest.param("machine", BASIC_INIT_FILES, True, id="machine"),
        pytest.param("kubernetes", BASIC_INIT_FILES, True, id="kubernetes"),
    ],
)
@pytest.mark.parametrize(
    ("charm_name", "workload_module_filename"),
    [
        pytest.param("machine", "workload.py", id="generic_name"),
        pytest.param(
            "foo-bar-k8s-operator", "foo_bar.py", id="generic_suffix_k8s_operator"
        ),
        pytest.param("foo-bar-k8s", "foo_bar.py", id="generic_suffix_k8s"),
        pytest.param("foo-bar-operator", "foo_bar.py", id="generic_suffix_operator"),
        pytest.param("charm123", "charm123.py", id="name_with_numbers"),
    ],
)
@pytest.mark.parametrize("author", VALID_AUTHORS)
def test_files_created_correct(
    new_path,
    init_command,
    profile: str,
    base_expected_files: set[pathlib.Path],
    has_workload_module: bool,
    charm_name,
    workload_module_filename: str,
    author,
):
    params = create_namespace(name=charm_name, author=author, profile=profile)
    init_command.run(params)

    if has_workload_module:
        workload_module_path = pathlib.Path(f"src/{workload_module_filename}")
        expected_files = base_expected_files.union({workload_module_path})
    else:
        expected_files = base_expected_files

    actual_files = {p.relative_to(new_path) for p in new_path.rglob("*")}

    charmcraft_yaml = (new_path / "charmcraft.yaml").read_text()
    tox_ini = (new_path / "tox.ini").read_text(encoding="utf-8")

    pytest_check.equal(actual_files, expected_files)
    pytest_check.is_true(
        re.search(rf"^name: {charm_name}$", charmcraft_yaml, re.MULTILINE)
    )
    pytest_check.is_true(re.search(rf"^# Copyright \d+ {author}", tox_ini))


@pytest.mark.parametrize(
    "profile",
    FRAMEWORK_PROFILES,
)
def test_framework_profile_charm_user(new_path, init_command, profile):
    v1_dir = new_path / "v1"
    init_command.run(create_namespace(profile=profile, project_dir=v1_dir))

    v1_project = yaml.safe_load((v1_dir / "charmcraft.yaml").read_text())
    assert "charm-user" not in v1_project

    v2_dir = new_path / "v2"
    init_command.run(
        create_namespace(
            profile=profile,
            base="ubuntu@26.04",
            project_dir=v2_dir,
        )
    )

    v2_project = yaml.safe_load((v2_dir / "charmcraft.yaml").read_text())
    assert v2_project["charm-user"] == "non-root"


def test_profiles_discovered_from_templates(init_command):
    assert init_command.profiles == sorted(ALL_PROFILES)


@pytest.mark.parametrize(
    "profile",
    [
        "django-framework",
        "expressjs-framework",
        "flask-framework",
        "fastapi-framework",
        "go-framework",
        "spring-boot-framework",
    ],
)
@pytest.mark.parametrize("base", ["ubuntu@24.04", "ubuntu@26.04"])
def test_explicit_base_variant(new_path, init_command, profile: str, base: str):
    init_command.run(create_namespace(profile=profile, base=base))

    project = yaml.safe_load((new_path / "charmcraft.yaml").read_text())

    assert project["base"] == base
    assert project.get("charm-user") == ("non-root" if base == "ubuntu@26.04" else None)
    assert (new_path / "pyproject.toml").exists()
    if base == "ubuntu@26.04":
        assert not (new_path / "requirements.txt").exists()
    elif profile in ["django-framework", "flask-framework", "fastapi-framework"]:
        assert (new_path / "requirements.txt").exists()


def test_unavailable_base_variant(new_path, init_command):
    with pytest.raises(
        InitError,
        match="Base variant 'ubuntu@25.04' is not available",
    ) as exc_info:
        init_command.run(
            create_namespace(profile="flask-framework", base="ubuntu@25.04")
        )

    assert exc_info.value.resolution == (
        "Choose a different base for this profile.\n"
        "Available bases are: 'ubuntu@24.04' and 'ubuntu@26.04'"
    )


def test_base_selection_not_available(new_path, init_command):
    with pytest.raises(
        InitError,
        match="Base selection is not available for this profile",
    ):
        init_command.run(
            create_namespace(profile="test-kubernetes", base="ubuntu@26.04")
        )


def test_invalid_base(new_path, init_command):
    with pytest.raises(InitError, match="invalid base name"):
        init_command.run(
            create_namespace(profile="flask-framework", base="../../ubuntu@26.04")
        )


@pytest.mark.parametrize(
    ("profile", "uses_uv"),
    [
        pytest.param("machine", True, id="machine"),
        pytest.param("kubernetes", True, id="kubernetes"),
        pytest.param("flask-framework", False, id="flask-framework"),
    ],
)
def test_success_message(new_path, init_command, emitter, profile: str, uses_uv: bool):
    init_command.run(create_namespace(profile=profile))
    output = "\n".join(
        c.args[1] for c in emitter.interactions if c.args[0] == "message"
    )
    if uses_uv:
        assert "Run 'uv lock'" in output
        # uv.lock is mentioned in the instructions but isn't listed as a created file.
        assert "including uv.lock" in output
        assert "uv.lock" not in output.replace("including uv.lock", "")
    else:
        assert "uv.lock" not in output
        assert "uv lock" not in output


def test_force(new_path, init_command):
    tmp_file = new_path / "README.md"
    with tmp_file.open("w") as f:
        f.write("This is a nonsense readme")

    init_command.run(create_namespace(force=True))

    # Check that init ran
    assert (new_path / "LICENSE").exists()

    # Check that init did not overwrite files
    with tmp_file.open("r") as f:
        assert f.read() == "This is a nonsense readme"


def test_nonoverlapping_file_does_not_require_force(new_path, init_command):
    unrelated_file = new_path / "unrelated"
    unrelated_file.touch()

    init_command.run(create_namespace())

    assert unrelated_file.exists()
    assert (new_path / "charmcraft.yaml").exists()


def test_project_dir_alias(new_path, init_command):
    project_dir = new_path / "project"
    params = create_namespace(project_dir=new_path)
    params.project_dir = None
    params.project_dir_option = project_dir

    init_command.run(params)

    assert (project_dir / "charmcraft.yaml").exists()


def test_project_dir_arguments_conflict(new_path, init_command):
    with pytest.raises(
        errors.CraftError,
        match="Cannot use <project-dir> and --project-dir at the same time",
    ):
        init_command.run(
            create_namespace(
                project_dir=new_path / "positional",
                project_dir_option=new_path / "option",
            )
        )


@pytest.mark.parametrize("name", [None, 0, "1234", "yolo swag", "camelCase"])
def test_bad_name(monkeypatch, new_path, init_command, name):
    with pytest.raises(errors.CraftError, match=BAD_CHARM_NAME_REGEX):
        init_command.run(create_namespace(name=name))


@pytest.mark.skipif(sys.platform == "win32", reason=("Password database only on Unix"))
@pytest.mark.parametrize("author", VALID_AUTHORS)
def test_gecos_valid_author(monkeypatch, new_path, init_command, author):
    monkeypatch.setattr(
        pwd,
        "getpwuid",
        mock.Mock(
            return_value=pwd.struct_passwd(
                ("user", "pass", 1, 1, f"{author},,,", "homedir", "shell")
            )
        ),
    )

    init_command.run(create_namespace(author=None))

    pytest_check.is_true(
        re.search(rf"^# Copyright \d+ {author}", (new_path / "tox.ini").read_text())
    )


@pytest.mark.skipif(sys.platform == "win32", reason=("Password database only on Unix"))
@pytest.mark.parametrize(
    ("mock_getpwuid", "error_msg"),
    [
        pytest.param(
            mock.Mock(side_effect=KeyError("no user")),
            UNKNOWN_AUTHOR_REGEX,
            id="user-doesnt-exist",
        ),
    ],
)
def test_gecos_user_not_found(
    monkeypatch, new_path, init_command, mock_getpwuid, error_msg
):
    monkeypatch.setattr(pwd, "getpwuid", mock_getpwuid)

    with pytest.raises(errors.CraftError, match=error_msg):
        init_command.run(create_namespace(author=None))


@pytest.mark.skipif(sys.platform == "win32", reason=("Password database only on Unix"))
def test_gecos_user_has_no_name(monkeypatch, new_path, init_command):
    mock_getpwuid = mock.Mock(
        return_value=pwd.struct_passwd(("user", "pass", 1, 1, "", "dir", "shell"))
    )
    monkeypatch.setattr(pwd, "getpwuid", mock_getpwuid)

    with pytest.raises(errors.CraftError, match=UNKNOWN_AUTHOR_REGEX):
        init_command.run(create_namespace(author=None))


@pytest.mark.parametrize(
    "subdir",
    [
        "somedir",
        "some/dir",
        "a/really/deep/path/with_parents/all/created",
        pytest.param(
            "/tmp/test_charm_dir-absolute_directory_path",
            marks=pytest.mark.skipif(os.name != "posix", reason="This is a posix path"),
        ),
    ],
)
@pytest.mark.parametrize("base_expected_files", [BASIC_INIT_FILES])
def test_create_directory(new_path, init_command, subdir, base_expected_files):
    init_dir = new_path / subdir

    try:
        params = create_namespace(name="foo-bar-k8s", project_dir=pathlib.Path(subdir))
        init_command.run(params)

        workload_module_path = pathlib.Path("src/foo_bar.py")
        expected_files = base_expected_files.union({workload_module_path})

        actual_files = {p.relative_to(init_dir) for p in init_dir.rglob("*")}

        assert actual_files == expected_files

    finally:
        shutil.rmtree(init_dir)


@pytest.mark.skipif(os.name != "posix", reason="Checking posix executable bit.")
def test_executable_set(new_path, init_command):
    init_command.run(create_namespace())

    assert (new_path / "src/charm.py").stat().st_mode & S_IXALL == S_IXALL


@pytest.mark.slow
@pytest.mark.skipif(
    bool(os.getenv("RUNNING_TOX")) and sys.version_info < (3, 11),
    reason="does not work inside tox in Python3.10 and below",
)
@pytest.mark.parametrize("profile", ALL_PROFILES)
def test_tox_success(new_path, init_command, profile):
    # fix the PYTHONPATH and PATH so the tests in the initted environment use our own
    # virtualenv libs and bins (if any), as they need them, but we're not creating a
    # venv for the local tests (note that for CI doesn't use a venv)
    env = os.environ.copy()
    env_paths = [p for p in sys.path if "env/lib/python" in p]
    if env_paths:
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] += ":" + ":".join(env_paths)
        else:
            env["PYTHONPATH"] = ":".join(env_paths)
        for path in env_paths:
            bin_path = path[: path.index("env/lib/python")] + "env/bin"
            env["PATH"] = bin_path + ":" + env["PATH"]

    init_command.run(create_namespace(profile=profile))

    if not (new_path / "tox.ini").exists():
        pytest.skip("init template doesn't contain tox.ini file")

    if list((new_path / "tests").glob("*.py")):  # If any tests exist
        result = subprocess.run(
            ["tox", "-v", "run", "-e", "unit"],
            cwd=new_path,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, "Tox run failed:\n" + result.stdout
