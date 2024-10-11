# Copyright 2024 Canonical Ltd.
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
"""Unit tests for dispatch script creation."""

import pathlib

import pytest
import pytest_check

from charmcraft import const, dispatch


def test_create_dispatch_hooks_exist(fake_path: pathlib.Path):
    """Test that nothing happens if a hooks directory exists."""
    prime_dir = fake_path / "prime"
    (prime_dir / const.HOOKS_DIRNAME).mkdir(parents=True)

    pytest_check.is_false(dispatch.create_dispatch(prime_dir=prime_dir))

    pytest_check.is_false((prime_dir / const.DISPATCH_FILENAME).exists())


def test_create_dispatch_dispatch_exists(fake_path: pathlib.Path):
    """Test that nothing happens if dispatch file already exists."""
    prime_dir = fake_path / "prime"
    prime_dir.mkdir()
    dispatch_path = prime_dir / const.DISPATCH_FILENAME
    dispatch_path.write_text("DO NOT OVERWRITE")

    pytest_check.is_false(dispatch.create_dispatch(prime_dir=prime_dir))

    pytest_check.equal(dispatch_path.read_text(), "DO NOT OVERWRITE")


@pytest.mark.parametrize("entrypoint", ["src/charm.py", "src/some_entrypoint.py"])
def test_create_dispatch_no_entrypoint(fake_path: pathlib.Path, entrypoint):
    prime_dir = fake_path / "prime"
    prime_dir.mkdir()
    dispatch_path = prime_dir / const.DISPATCH_FILENAME

    pytest_check.is_false(
        dispatch.create_dispatch(prime_dir=prime_dir, entrypoint=entrypoint)
    )

    pytest_check.is_false(dispatch_path.exists())


@pytest.mark.parametrize("entrypoint", ["src/charm.py", "src/some_entrypoint.py"])
def test_create_dispatch_with_entrypoint(fake_path: pathlib.Path, entrypoint):
    prime_dir = fake_path / "prime"
    prime_dir.mkdir()
    entrypoint = prime_dir / entrypoint
    entrypoint.parent.mkdir(parents=True, exist_ok=True)
    entrypoint.touch()
    dispatch_file = prime_dir / const.DISPATCH_FILENAME
    expected = dispatch.DISPATCH_SCRIPT_TEMPLATE.format(entrypoint=entrypoint)

    pytest_check.is_true(
        dispatch.create_dispatch(prime_dir=prime_dir, entrypoint=entrypoint)
    )
    pytest_check.equal(dispatch_file.read_text(), expected)
