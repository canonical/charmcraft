# Copyright 2021 Canonical Ltd.
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

import textwrap

import pytest

from charmcraft.linters import Language, Framework, shared_state


EXAMPLE_DISPATCH = """
#!/bin/sh

PYTHONPATH=lib:venv ./charm.py
"""


def test_language_python(tmp_path):
    """The charm is written in Python."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(EXAMPLE_DISPATCH)
    entrypoint = tmp_path / "charm.py"
    entrypoint.touch()
    entrypoint.chmod(0o700)
    result = Language.run(tmp_path)
    assert result == Language.Result.python


def test_language_no_dispatch(tmp_path):
    """The charm has no dispatch at all."""
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


def test_language_inaccessible_dispatch(tmp_path):
    """The charm has a dispatch we can't use."""
    dispatch = tmp_path / "dispatch"
    dispatch.touch()
    dispatch.chmod(0o000)
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


def test_language_broken_dispatch(tmp_path):
    """The charm has a dispatch which we can't decode."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_bytes(b"\xC0\xC0")
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


def test_language_empty_dispatch(tmp_path):
    """The charm dispatch is empty."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text("")
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


def test_language_no_entrypoint(tmp_path):
    """Cannot find the entrypoint used in dispatch."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(EXAMPLE_DISPATCH)
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


def test_language_entrypoint_is_no_python(tmp_path):
    """The charm entrypoint has not a .py extension."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(
        """
        #!/bin/sh
        ./charm
    """
    )
    entrypoint = tmp_path / "charm.py"
    entrypoint.touch()
    entrypoint.chmod(0o700)
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


def test_language_entrypoint_no_exec(tmp_path):
    """The charm entrypoint is not executable."""
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(EXAMPLE_DISPATCH)
    entrypoint = tmp_path / "charm.py"
    entrypoint.touch()
    result = Language.run(tmp_path)
    assert result == Language.Result.unknown


@pytest.mark.parametrize("import_line", [
    "import ops",
    "from ops import charm",
    "from ops.charm import CharmBase",
])
def test_framework_operator_used(tmp_path, monkeypatch, import_line):
    """All conditions for 'framework' are in place."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text(textwrap.dedent(f"""
        {import_line}

        class Foo:
            pass
    """))

    # an ops directory inside venv
    opsdir = tmp_path / 'venv' / 'ops'
    opsdir.mkdir(parents=True)

    # the result from previously run Language
    monkeypatch.setitem(shared_state, 'language', {'result': 'python', 'entrypoint': entrypoint})

    # check
    result = Framework.run(tmp_path)
    assert result == Framework.Result.operator


def test_framework_language_not_python(tmp_path, monkeypatch):
    """The language trait is not set to Python."""
    # the result from previously run Language
    monkeypatch.setitem(shared_state, 'language', {'result': 'unknown'})

    # check
    result = Framework.run(tmp_path)
    assert result == Framework.Result.unknown


def test_framework_venv_directory_missing(tmp_path, monkeypatch):
    """The charm has not a specific 'venv' dir."""
    # the result from previously run Language
    monkeypatch.setitem(shared_state, 'language', {'result': 'python', 'entrypoint': 'whatever'})

    # check
    result = Framework.run(tmp_path)
    assert result == Framework.Result.unknown


def test_framework_no_venv_ops_directory(tmp_path, monkeypatch):
    """The charm *has not* a specific 'venv/ops' dir."""
    # the result from previously run Language
    monkeypatch.setitem(shared_state, 'language', {'result': 'python', 'entrypoint': 'whatever'})

    # an empty venv
    venvdir = tmp_path / 'venv'
    venvdir.mkdir()

    # check
    result = Framework.run(tmp_path)
    assert result == Framework.Result.unknown


def test_framework_venv_ops_directory_is_not_a_dir(tmp_path, monkeypatch):
    """The charm has not a specific 'venv/ops' *dir*."""
    # the result from previously run Language
    monkeypatch.setitem(shared_state, 'language', {'result': 'python', 'entrypoint': 'whatever'})

    # an ops *file* inside venv
    venvdir = tmp_path / 'venv'
    venvdir.mkdir()
    opsfile = venvdir / 'ops'
    opsfile.touch()

    # check
    result = Framework.run(tmp_path)
    assert result == Framework.Result.unknown


@pytest.mark.parametrize("import_line", [
    "import logging",
    "import whatever.ops",
    "from stuff import ops",
    "from stuff.ops import whatever",
])
def test_framework_no_ops_imported(tmp_path, monkeypatch, import_line):
    """."""
    # an entry point that import ops
    entrypoint = tmp_path / "charm.py"
    entrypoint.write_text(textwrap.dedent(f"""
        {import_line}

        class Foo:
            pass
    """))

    # an ops directory inside venv
    opsdir = tmp_path / 'venv' / 'ops'
    opsdir.mkdir(parents=True)

    # the result from previously run Language
    monkeypatch.setitem(shared_state, 'language', {'result': 'python', 'entrypoint': entrypoint})

    # check
    result = Framework.run(tmp_path)
    assert result == Framework.Result.unknown

fixme: add "reactive" stuff
