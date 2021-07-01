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

from charmcraft.linters import Language


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
