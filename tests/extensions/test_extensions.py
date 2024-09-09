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

from typing import Any

import pytest
from overrides import override

from charmcraft import const, errors, extensions
from charmcraft.extensions.extension import Extension


class FakeExtension(Extension):
    """A fake test Extension"""

    name = "fake-extension"
    bases = [("ubuntu", "22.04")]

    @classmethod
    def get_supported_bases(cls) -> list[tuple[str, ...]]:
        """Return a list of tuple of supported bases."""
        return cls.bases

    @staticmethod
    def is_experimental(_base: tuple[str, ...] | None) -> bool:
        """Return whether or not this extension is unstable for given base."""
        return False

    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""
        return {}

    def get_part_snippet(self) -> dict[str, Any]:
        """Return the part snippet to apply to existing parts."""
        return {}

    def get_parts_snippet(self) -> dict[str, Any]:
        """Return the parts to add to parts."""
        return {}


class ExperimentalExtension(FakeExtension):
    """A fake test Extension that is experimental"""

    name = "experimental-extension"
    bases = [("ubuntu", "22.04")]

    @staticmethod
    def is_experimental(_base: str | None) -> bool:
        return True


class InvalidPartExtension(FakeExtension):
    """A fake test Extension that has invalid parts snippet"""

    name = "invalid-extension"
    bases = [("ubuntu", "22.04")]

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        return {"bad-name": {"plugin": "dump", "source": None}}


class FullExtension(FakeExtension):
    """A fake test Extension that has complete behavior"""

    name = "full-extension"
    bases = [("ubuntu", "22.04")]

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""
        return {
            "terms": ["https://example.com/terms", "https://example.com/terms2"],
        }

    @override
    def get_part_snippet(self) -> dict[str, Any]:
        """Return the part snippet to apply to existing parts."""
        return {"stage-packages": ["new-package-1"]}

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        """Return the parts to add to parts."""
        return {"full-extension/new-part": {"plugin": "nil", "source": None}}


@pytest.fixture
def fake_extensions(stub_extensions):
    extensions.register(FakeExtension.name, FakeExtension)
    extensions.register(ExperimentalExtension.name, ExperimentalExtension)
    extensions.register(InvalidPartExtension.name, InvalidPartExtension)
    extensions.register(FullExtension.name, FullExtension)


def test_experimental_with_env(fake_extensions, tmp_path, monkeypatch):
    charmcraft_config = {
        "type": "charm",
        "name": "test-charm-name-from-charmcraft-yaml",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": [ExperimentalExtension.name],
    }
    monkeypatch.setenv(const.EXPERIMENTAL_EXTENSIONS_ENV_VAR, "1")
    project_root = tmp_path
    extensions.apply_extensions(project_root, charmcraft_config)


def test_experimental_no_env(fake_extensions, tmp_path):
    charmcraft_config = {
        "type": "charm",
        "name": "test-charm-name-from-charmcraft-yaml",
        "summary": "test summary",
        "description": "test description",
        "bases": [
            {
                "build-on": [{"name": "ubuntu", "channel": "20.04", "architectures": ["amd64"]}],
                "run-on": [{"name": "ubuntu", "channel": "20.04", "architectures": ["amd64"]}],
            }
        ],
        "extensions": [ExperimentalExtension.name],
    }
    with pytest.raises(errors.ExtensionError) as exc:
        extensions.apply_extensions(tmp_path, charmcraft_config)

    expected_message = f"Extension is experimental: '{ExperimentalExtension.name}'"
    assert str(exc.value) == expected_message


def test_wrong_base(fake_extensions, tmp_path):
    charmcraft_config = {
        "type": "charm",
        "name": "test-charm-name-from-charmcraft-yaml",
        "summary": "test summary",
        "description": "test description",
        "bases": [
            {
                "build-on": [{"name": "ubuntu", "channel": "20.04", "architectures": ["amd64"]}],
                "run-on": [{"name": "ubuntu", "channel": "20.04", "architectures": ["amd64"]}],
            }
        ],
        "extensions": [FakeExtension.name],
    }
    with pytest.raises(errors.ExtensionError) as exc:
        extensions.apply_extensions(tmp_path, charmcraft_config)

    expected_message = (
        f"Extension '{FakeExtension.name}' does not support base: ('ubuntu', '20.04')"
    )
    assert str(exc.value) == expected_message


def test_invalid_parts(fake_extensions, tmp_path):
    charmcraft_config = {
        "type": "charm",
        "name": "test-charm-name-from-charmcraft-yaml",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": [InvalidPartExtension.name],
    }

    with pytest.raises(ValueError) as exc:
        extensions.apply_extensions(tmp_path, charmcraft_config)

    assert "Extension has invalid part names" in str(exc.value)


def test_apply_extensions(fake_extensions, tmp_path):
    charmcraft_config = {
        "type": "charm",
        "name": "test-charm-name-from-charmcraft-yaml",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": [FullExtension.name],
        "parts": {"my-part": {"plugin": "nil", "source": None, "stage-packages": ["old-package"]}},
    }

    applied = extensions.apply_extensions(tmp_path, charmcraft_config)

    # Part snippet extends the existing part
    parts = applied["parts"]
    assert parts["my-part"]["stage-packages"] == [
        "new-package-1",
        "old-package",
    ]

    # New part
    assert parts[f"{FullExtension.name}/new-part"] == {"plugin": "nil", "source": None}
