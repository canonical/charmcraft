# Copyright 2021-2022 Canonical Ltd.
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

"""Tests for analyze and lint code."""

import pathlib
import sys
from textwrap import dedent
from unittest.mock import patch

import pytest

from charmcraft.linters import (
    CHECKERS,
    BaseChecker,
    CheckType,
    Entrypoint,
    Framework,
    JujuActions,
    JujuConfig,
    JujuMetadata,
    Language,
    analyze,
    check_dispatch_with_python_entrypoint,
    get_entrypoint_from_dispatch,
)
from charmcraft.models.lint import LintResult

EXAMPLE_DISPATCH = """
#!/bin/sh

PYTHONPATH=lib:venv ./charm.py
"""

# --- tests for helper functions


def test_epfromdispatch_ok(tmp_path):
    """An entrypoint is found in the dispatch."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(EXAMPLE_DISPATCH)
    entrypoint = tmp_path / "charm.py"
    result = get_entrypoint_from_dispatch(tmp_path)
    assert result == entrypoint


def test_epfromdispatch_no_dispatch(tmp_path):
    """The charm has no dispatch at all."""
    result = get_entrypoint_from_dispatch(tmp_path)
    assert result is None


def test_epfromdispatch_inaccessible_dispatch(tmp_path):
    """The charm has a dispatch we can't use."""
    dispatch = tmp_path / "dispatch"
    dispatch.touch()
    dispatch.chmod(0o000)
    result = get_entrypoint_from_dispatch(tmp_path)
    assert result is None


def test_epfromdispatch_broken_dispatch(tmp_path):
    """The charm has a dispatch which we can't decode."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_bytes(b"\xC0\xC0")
    result = get_entrypoint_from_dispatch(tmp_path)
    assert result is None


def test_epfromdispatch_empty_dispatch(tmp_path):
    """The charm dispatch is empty."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text("")
    result = get_entrypoint_from_dispatch(tmp_path)
    assert result is None


def test_checkdispatchpython_python_ok(tmp_path):
    """The charm is written in Python."""
    entrypoint = tmp_path / "charm.py"
    entrypoint.touch(mode=0o700)
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = check_dispatch_with_python_entrypoint(tmp_path)
    assert result == entrypoint


def test_checkdispatchpython_no_entrypoint(tmp_path):
    """Cannot find the entrypoint used in dispatch."""
    entrypoint = tmp_path / "charm.py"
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = check_dispatch_with_python_entrypoint(tmp_path)
    assert result is None


def test_checkdispatchpython_nothing_from_dispatch(tmp_path):
    """The dispatch is not there, or not usable."""
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=None):
        result = check_dispatch_with_python_entrypoint(tmp_path)
    assert result is None


def test_checkdispatchpython_entrypoint_is_not_python(tmp_path):
    """The charm entrypoint has not a .py extension."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(
        """
        #!/bin/sh
        ./charm
    """
    )
    entrypoint = tmp_path / "charm"
    entrypoint.touch(mode=0o700)
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = check_dispatch_with_python_entrypoint(tmp_path)
    assert result is None


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_checkdispatchpython_entrypoint_no_exec(tmp_path):
    """The charm entrypoint is not executable."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(EXAMPLE_DISPATCH)
    entrypoint = tmp_path / "charm.py"
    entrypoint.touch()
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = check_dispatch_with_python_entrypoint(tmp_path)
    assert result is None


# --- tests for Language checker


def test_language_python():
    """The charm is written in Python."""
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path("entrypoint")
        result = Language().run(pathlib.Path("somedir"))
    assert result == Language.Result.PYTHON
    mock_check.assert_called_with(pathlib.Path("somedir"))


def test_language_no_dispatch(tmp_path):
    """The charm has no dispatch at all."""
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = None
        result = Language().run(pathlib.Path("somedir"))
    assert result == Language.Result.UNKNOWN
    mock_check.assert_called_with(pathlib.Path("somedir"))


# --- tests for Framework checker


def test_framework_run_operator():
    """Check for Operator Framework was successful."""
    checker = Framework()
    with patch.object(Framework, "_check_operator", lambda self, path: True):
        result = checker.run(pathlib.Path("somepath"))
    assert result == Framework.Result.OPERATOR
    assert checker.text == "The charm is based on the Operator Framework."


def test_framework_run_reactive():
    """Check for Reactive Framework was successful."""
    checker = Framework()
    with patch.object(Framework, "_check_operator", lambda self, path: False):
        with patch.object(Framework, "_check_reactive", lambda self, path: True):
            result = checker.run(pathlib.Path("somepath"))
    assert result == Framework.Result.REACTIVE
    assert checker.text == "The charm is based on the Reactive Framework."


def test_framework_run_unknown():
    """No check for any framework was successful."""
    checker = Framework()
    with patch.object(Framework, "_check_operator", lambda self, path: False):
        with patch.object(Framework, "_check_reactive", lambda self, path: False):
            result = checker.run(pathlib.Path("somepath"))
    assert result == Framework.Result.UNKNOWN
    assert checker.text == "The charm is not based on any known Framework."


@pytest.mark.parametrize(
    "import_line",
    [
        "import ops",
        "import stuff, ops, morestuff",
        "from ops import charm",
        "from ops.charm import CharmBase",
    ],
)
def test_framework_operator_used_ok(tmp_path, import_line):
    """All conditions for 'framework' are in place."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text(f"{import_line}")

    # an ops directory inside venv
    opsdir = tmp_path / "venv" / "ops"
    opsdir.mkdir(parents=True)

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path(entrypoint)
        result = Framework()._check_operator(tmp_path)
    assert result is True
    mock_check.assert_called_with(tmp_path)


def test_framework_operator_language_not_python(tmp_path):
    """The language trait is not set to Python."""
    # an entry point that is not really python
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text("no python :)")

    # an ops directory inside venv
    opsdir = tmp_path / "venv" / "ops"
    opsdir.mkdir(parents=True)

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = None
        result = Framework()._check_operator(tmp_path)
    assert result is False


def test_framework_operator_venv_directory_missing(tmp_path):
    """The charm has not a specific 'venv' dir."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text("import ops")

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path(entrypoint)
        result = Framework()._check_operator(tmp_path)
    assert result is False


def test_framework_operator_no_venv_ops_directory(tmp_path):
    """The charm *has not* a specific 'venv/ops' dir."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text("import ops")

    # an empty venv
    venvdir = tmp_path / "venv"
    venvdir.mkdir()

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path(entrypoint)
        result = Framework()._check_operator(tmp_path)
    assert result is False


def test_framework_operator_venv_ops_directory_is_not_a_dir(tmp_path):
    """The charm has not a specific 'venv/ops' *dir*."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text("import ops")

    # an ops *file* inside venv
    opsfile = tmp_path / "venv" / "ops"
    opsfile.parent.mkdir()
    opsfile.touch()

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path(entrypoint)
        result = Framework()._check_operator(tmp_path)
    assert result is False


def test_framework_operator_corrupted_entrypoint(tmp_path):
    """Cannot parse the Python file."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text("xx --")  # not really Python

    # an ops directory inside venv
    opsdir = tmp_path / "venv" / "ops"
    opsdir.mkdir(parents=True)

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path(entrypoint)
        result = Framework()._check_operator(tmp_path)
    assert result is False


@pytest.mark.parametrize(
    "import_line",
    [
        "import logging",
        "import whatever.ops",
        "from stuff import ops",
        "from stuff.ops import whatever",
    ],
)
def test_framework_operator_no_ops_imported(tmp_path, monkeypatch, import_line):
    """Different imports that are NOT importing the Operator Framework."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text(f"{import_line}")

    # an ops directory inside venv
    opsdir = tmp_path / "venv" / "ops"
    opsdir.mkdir(parents=True)

    # check
    with patch("charmcraft.linters.check_dispatch_with_python_entrypoint") as mock_check:
        mock_check.return_value = pathlib.Path(entrypoint)
        result = Framework()._check_operator(tmp_path)
    assert result is False


@pytest.mark.parametrize(
    "import_line",
    [
        "import charms.reactive",
        "import stuff, charms.reactive, morestuff",
        "from charms.reactive import stuff",
        "from charms.reactive.stuff import Stuff",
    ],
)
@pytest.mark.parametrize(
    ("charm_module", "charmcraft_yaml", "metadata_yaml"),
    [
        (
            "foobar.py",
            dedent(
                """\
                type: charm
                """
            ),
            dedent(
                """\
                name: foobar
                summary: Small text.
                description: Lot of text.
                """
            ),
        ),
        (
            "foo_bar.py",
            dedent(
                """\
                type: charm
                """
            ),
            dedent(
                """\
                name: foo-bar
                summary: Small text.
                description: Lot of text.
                """
            ),
        ),
        (
            "foobar.py",
            None,
            dedent(
                """\
                name: foobar
                summary: Small text.
                description: Lot of text.
                """
            ),
        ),
        (
            "foo_bar.py",
            None,
            dedent(
                """\
                name: foo-bar
                summary: Small text.
                description: Lot of text.
                """
            ),
        ),
    ],
)
def test_framework_reactive_used_ok(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
    import_line,
    charm_module,
):
    """The reactive framework was used.

    Parametrized args:
    - import_line: different ways to express the import
    """
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / charm_module
    entrypoint.parent.mkdir()
    entrypoint.write_text(f"{import_line}")

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.reactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is True


def test_framework_reactive_no_metadata(tmp_path, monkeypatch):
    """No useful name from metadata."""
    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / "foobar.py"
    entrypoint.parent.mkdir()
    entrypoint.write_text("import charms.reactive")

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.reactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


def test_framework_reactive_no_entrypoint(tmp_path, monkeypatch):
    """Missing entrypoint file."""
    # metadata file with needed name field
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("name: foobar")

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.reactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_framework_reactive_unaccesible_entrypoint(tmp_path, monkeypatch):
    """Cannot read the entrypoint file."""
    # metadata file with needed name field
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("name: foobar")

    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / "foobar.py"
    entrypoint.parent.mkdir()
    entrypoint.write_text("import charms.reactive")
    entrypoint.chmod(0o000)

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.reactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


def test_framework_reactive_corrupted_entrypoint(tmp_path, monkeypatch):
    """The entrypoint is not really a Python file."""
    # metadata file with needed name field
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("name: foobar")

    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / "foobar.py"
    entrypoint.parent.mkdir()
    entrypoint.write_text("xx --")  # not really Python

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.reactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


def test_framework_reactive_no_wheelhouse(tmp_path, monkeypatch):
    """The wheelhouse directory does not exist."""
    # metadata file with needed name field
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("name: foobar")

    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / "foobar.py"
    entrypoint.parent.mkdir()
    entrypoint.write_text("import charms.reactive")

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


def test_framework_reactive_no_reactive_lib(tmp_path, monkeypatch):
    """The wheelhouse directory has no reactive lib."""
    # metadata file with needed name field
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("name: foobar")

    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / "foobar.py"
    entrypoint.parent.mkdir()
    entrypoint.write_text("import charms.reactive")

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.noreallyreactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


@pytest.mark.parametrize(
    "import_line",
    [
        "import logging",
        "import whatever.charms.reactive",
        "import charms.whatever.reactive",
        "from stuff.charms import reactive",
        "from charms.stuff import reactive",
        "from stuff.charms.reactive import whatever",
    ],
)
def test_framework_reactive_no_reactive_imported(tmp_path, monkeypatch, import_line):
    """Different imports that are NOT importing the Reactive Framework."""
    # metadata file with needed name field
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("name: foobar")

    # a Python file that imports charms.reactive
    entrypoint = tmp_path / "reactive" / "foobar.py"
    entrypoint.parent.mkdir()
    entrypoint.write_text(f"{import_line}")

    # the reactive lib is used
    reactive_lib = tmp_path / "wheelhouse" / "charms.reactive-1.0.1.zip"
    reactive_lib.parent.mkdir()
    reactive_lib.touch()

    # check
    result = Framework()._check_reactive(tmp_path)
    assert result is False


# --- tests for JujuMetadata checker


def test_jujumetadata_all_ok(tmp_path):
    """All conditions ok for JujuMetadata to result ok."""
    # metadata file with proper fields
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(
        """
        name: foobar
        summary: Small text.
        description: Lot of text.
    """
    )
    result = JujuMetadata().run(tmp_path)
    assert result == JujuMetadata.Result.OK


def test_jujumetadata_missing_file(tmp_path):
    """No metadata.yaml file at all."""
    linter = JujuMetadata()
    result = linter.run(tmp_path)
    assert result == JujuMetadata.Result.ERRORS
    assert linter.text == "Cannot read the metadata.yaml file."


def test_jujumetadata_file_corrupted(tmp_path):
    """The metadata.yaml file is not valid YAML."""
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(" - \n-")
    linter = JujuMetadata()
    result = linter.run(tmp_path)
    assert result == JujuMetadata.Result.ERRORS
    assert linter.text == "The metadata.yaml file is not a valid YAML file."


_mandatory_fields = ["summary", "description", "name"]


@pytest.mark.parametrize("to_miss", range(len(_mandatory_fields)))
def test_jujumetadata_missing_field_simple(tmp_path, to_miss):
    """A required field is missing in the metadata file."""
    included_fields = _mandatory_fields.copy()
    missing = included_fields.pop(to_miss)

    # metadata file with not all fields
    metadata_file = tmp_path / "metadata.yaml"
    content = "\n".join(f"{field}: some text" for field in included_fields)
    metadata_file.write_text(content)
    linter = JujuMetadata()
    result = linter.run(tmp_path)
    assert result == JujuMetadata.Result.ERRORS
    assert linter.text == (
        f"The metadata.yaml file is missing the following attribute(s): '{missing}'."
    )


def test_jujumetadata_missing_field_multiple(tmp_path):
    """More than one required field is missing in the metadata file."""
    # metadata file with not all fields
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(
        """
        name: foobar
    """
    )
    linter = JujuMetadata()
    result = linter.run(tmp_path)
    assert result == JujuMetadata.Result.ERRORS
    assert linter.text == (
        "The metadata.yaml file is missing the following attribute(s): "
        "'description' and 'summary'."
    )


# --- tests for analyze function


def create_fake_checker(**kwargs):
    """Create a fake Checker.

    Receive generic kwargs and process them as a dict for the defaults, as we can't declare
    the name in the function definition and then use it in the class definition.
    """
    params = {
        "check_type": "type",
        "name": "name",
        "url": "url",
        "text": "text",
        "result": "result",
    }
    params.update(kwargs)

    class FakeChecker(BaseChecker):
        check_type = params["check_type"]
        name = params["name"]
        url = params["url"]
        text = params["text"]

        def run(self, basedir):
            return params["result"]

    return FakeChecker


def test_analyze_run_everything(config):
    """Check that analyze runs all and collect the results."""
    FakeChecker1 = create_fake_checker(
        check_type=CheckType.ATTRIBUTE, name="name1", url="url1", text="text1", result="result1"
    )
    FakeChecker2 = create_fake_checker(
        check_type=CheckType.LINT, name="name2", url="url2", text="text2", result="result2"
    )
    FakeChecker3 = create_fake_checker(
        check_type=CheckType.LINT, name="returns_none", url="url3", text=None, result="result3"
    )

    # hack the first fake checker to validate that it receives the indicated path
    def dir_validator(self, basedir):
        assert basedir == pathlib.Path("test-buildpath")
        return "result1"

    FakeChecker1.run = dir_validator

    with patch("charmcraft.linters.CHECKERS", [FakeChecker1, FakeChecker2, FakeChecker3]):
        result = analyze(config, pathlib.Path("test-buildpath"))

    r1, r2, r3 = result
    assert r1.check_type == "attribute"
    assert r1.name == "name1"
    assert r1.url == "url1"
    assert r1.text == "text1"
    assert r1.result == "result1"
    assert r2.check_type == "lint"
    assert r2.name == "name2"
    assert r2.url == "url2"
    assert r2.text == "text2"
    assert r2.result == "result2"
    assert r3.name == "returns_none"
    assert r3.url == "url3"
    assert r3.text == "n/a"
    assert r3.result == "result3"


def test_analyze_ignore_attribute(config):
    """Run all checkers except the ignored attribute."""
    FakeChecker1 = create_fake_checker(
        check_type=CheckType.ATTRIBUTE,
        name="name1",
        result="res1",
        text="text1",
        url="url1",
    )
    FakeChecker2 = create_fake_checker(
        check_type=CheckType.LINT,
        name="name2",
        result="res2",
        text="text2",
        url="url2",
    )

    config.analysis.ignore.attributes.append("name1")
    with patch("charmcraft.linters.CHECKERS", [FakeChecker1, FakeChecker2]):
        result = analyze(config, pathlib.Path("somepath"))

    res1, res2 = result
    assert res1.check_type == CheckType.ATTRIBUTE
    assert res1.name == "name1"
    assert res1.result == LintResult.IGNORED
    assert res1.text == ""
    assert res1.url == "url1"
    assert res2.check_type == CheckType.LINT
    assert res2.name == "name2"
    assert res2.result == "res2"
    assert res2.text == "text2"
    assert res2.url == "url2"


def test_analyze_ignore_linter(config):
    """Run all checkers except the ignored linter."""
    FakeChecker1 = create_fake_checker(
        check_type=CheckType.ATTRIBUTE,
        name="name1",
        result="res1",
        text="text1",
        url="url1",
    )
    FakeChecker2 = create_fake_checker(
        check_type=CheckType.LINT,
        name="name2",
        result="res2",
        text="text2",
        url="url2",
    )

    config.analysis.ignore.linters.append("name2")
    with patch("charmcraft.linters.CHECKERS", [FakeChecker1, FakeChecker2]):
        result = analyze(config, pathlib.Path("somepath"))

    res1, res2 = result
    assert res1.check_type == CheckType.ATTRIBUTE
    assert res1.name == "name1"
    assert res1.result == "res1"
    assert res1.text == "text1"
    assert res1.url == "url1"
    assert res2.check_type == CheckType.LINT
    assert res2.name == "name2"
    assert res2.result == LintResult.IGNORED
    assert res2.text == ""
    assert res2.url == "url2"


def test_analyze_override_ignore(config):
    """Run all checkers even the ignored ones, if requested."""
    FakeChecker1 = create_fake_checker(check_type=CheckType.ATTRIBUTE, name="name1", result="res1")
    FakeChecker2 = create_fake_checker(check_type=CheckType.LINT, name="name2", result="res2")

    config.analysis.ignore.attributes.append("name1")
    config.analysis.ignore.linters.append("name2")
    with patch("charmcraft.linters.CHECKERS", [FakeChecker1, FakeChecker2]):
        result = analyze(config, pathlib.Path("somepath"), override_ignore_config=True)

    res1, res2 = result
    assert res1.check_type == CheckType.ATTRIBUTE
    assert res1.name == "name1"
    assert res1.result == "res1"
    assert res2.check_type == CheckType.LINT
    assert res2.name == "name2"
    assert res2.result == "res2"


def test_analyze_crash_attribute(config):
    """The attribute checker crashes."""
    FakeChecker = create_fake_checker(
        check_type=CheckType.ATTRIBUTE, name="name", text="text", url="url"
    )

    def raises(*a):
        raise ValueError

    FakeChecker.run = raises

    with patch("charmcraft.linters.CHECKERS", [FakeChecker]):
        result = analyze(config, pathlib.Path("somepath"))

    (res,) = result
    assert res.check_type == CheckType.ATTRIBUTE
    assert res.name == "name"
    assert res.result == LintResult.UNKNOWN
    assert res.text == "text"
    assert res.url == "url"


def test_analyze_crash_lint(config):
    """The lint checker crashes."""
    FakeChecker = create_fake_checker(
        check_type=CheckType.LINT, name="name", text="text", url="url"
    )

    def raises(*a):
        raise ValueError

    FakeChecker.run = raises

    with patch("charmcraft.linters.CHECKERS", [FakeChecker]):
        result = analyze(config, pathlib.Path("somepath"))

    (res,) = result
    assert res.check_type == CheckType.LINT
    assert res.name == "name"
    assert res.result == LintResult.FATAL
    assert res.text == "text"
    assert res.url == "url"


def test_analyze_all_can_be_ignored(config):
    """Control that all real life checkers can be ignored."""
    config.analysis.ignore.attributes.extend(
        c.name for c in CHECKERS if c.check_type == CheckType.ATTRIBUTE
    )
    config.analysis.ignore.linters.extend(
        c.name for c in CHECKERS if c.check_type == CheckType.LINT
    )
    result = analyze(config, pathlib.Path("somepath"))
    assert all(r.result == LintResult.IGNORED for r in result)


# --- tests for JujuActions checker


def test_jujuactions_ok(tmp_path):
    """The actions.yaml file is valid."""
    actions_file = tmp_path / "actions.yaml"
    actions_file.write_text("stuff: foobar")
    result = JujuActions().run(tmp_path)
    assert result == JujuActions.Result.OK


def test_jujuactions_missing_file(tmp_path):
    """No actions.yaml file at all."""
    result = JujuActions().run(tmp_path)
    assert result == JujuActions.Result.OK


def test_jujuactions_file_corrupted(tmp_path):
    """The actions.yaml file is not valid YAML."""
    actions_file = tmp_path / "actions.yaml"
    actions_file.write_text(" - \n-")
    result = JujuActions().run(tmp_path)
    assert result == JujuActions.Result.ERRORS


# --- tests for JujuConfig checker


def test_jujuconfig_ok(tmp_path):
    """The config.yaml file is valid."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        options:
            foo:
                type: buzz
    """
    )
    result = JujuConfig().run(tmp_path)
    assert result == JujuConfig.Result.OK


def test_jujuconfig_missing_file(tmp_path):
    """No config.yaml file at all."""
    result = JujuConfig().run(tmp_path)
    assert result == JujuConfig.Result.OK


def test_jujuconfig_file_corrupted(tmp_path):
    """The config.yaml file is not valid YAML."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(" - \n-")
    linter = JujuConfig()
    result = linter.run(tmp_path)
    assert result == JujuConfig.Result.ERRORS
    assert linter.text == "The config.yaml file is not a valid YAML file."


def test_jujuconfig_no_options(tmp_path):
    """The config.yaml file does not have an options key."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        summary: Small text.
    """
    )
    linter = JujuConfig()
    result = linter.run(tmp_path)
    assert result == JujuConfig.Result.ERRORS
    assert linter.text == "Error in config.yaml: must have an 'options' dictionary."


def test_jujuconfig_empty_options(tmp_path):
    """The config.yaml file has an empty options key."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        options:
    """
    )
    linter = JujuConfig()
    result = linter.run(tmp_path)
    assert result == JujuConfig.Result.ERRORS
    assert linter.text == "Error in config.yaml: must have an 'options' dictionary."


def test_jujuconfig_options_not_dict(tmp_path):
    """The config.yaml file has an options key that is not a dict."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        options:
          - foo
          - bar
    """
    )
    linter = JujuConfig()
    result = linter.run(tmp_path)
    assert result == JujuConfig.Result.ERRORS
    assert linter.text == "Error in config.yaml: must have an 'options' dictionary."


def test_jujuconfig_no_type_in_options_items(tmp_path):
    """The items under 'options' must have a 'type' key."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        options:
          foo:
            description: something missing
    """
    )
    linter = JujuConfig()
    result = linter.run(tmp_path)
    assert result == JujuConfig.Result.ERRORS
    assert linter.text == "Error in config.yaml: items under 'options' must have a 'type' key."


# --- tests for Entrypoint checker


def test_entrypoint_not_used(tmp_path):
    """An entrypoint is not really used, nothing to check."""
    with patch("charmcraft.linters.get_entrypoint_from_dispatch") as mock_check:
        mock_check.return_value = None
        result = Entrypoint().run(tmp_path)
    assert result == Entrypoint.Result.NONAPPLICABLE
    mock_check.assert_called_with(tmp_path)


def test_entrypoint_all_ok(tmp_path):
    """All conditions for 'framework' are in place."""
    entrypoint = tmp_path / "charm.sh"
    entrypoint.touch(mode=0o777)
    with patch("charmcraft.linters.get_entrypoint_from_dispatch") as mock_check:
        mock_check.return_value = entrypoint
        result = Entrypoint().run(tmp_path)
    assert result == Entrypoint.Result.OK
    mock_check.assert_called_with(tmp_path)


def test_entrypoint_missing(tmp_path):
    """The file does not exist."""
    entrypoint = tmp_path / "charm"
    linter = Entrypoint()
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = linter.run(tmp_path)
    assert result == Entrypoint.Result.ERRORS
    assert linter.text == f"Cannot find the entrypoint file: {str(entrypoint)!r}"


def test_entrypoint_directory(tmp_path):
    """The pointed entrypoint is a directory."""
    entrypoint = tmp_path / "charm"
    entrypoint.mkdir()
    linter = Entrypoint()
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = linter.run(tmp_path)
    assert result == Entrypoint.Result.ERRORS
    assert linter.text == f"The entrypoint is not a file: {str(entrypoint)!r}"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_entrypoint_non_exec(tmp_path):
    """The pointed entrypoint is not an executable file."""
    entrypoint = tmp_path / "charm"
    entrypoint.touch()
    linter = Entrypoint()
    with patch("charmcraft.linters.get_entrypoint_from_dispatch", return_value=entrypoint):
        result = linter.run(tmp_path)
    assert result == Entrypoint.Result.ERRORS
    assert linter.text == f"The entrypoint file is not executable: {str(entrypoint)!r}"
