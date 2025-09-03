# Copyright 2023,2025 Canonical Ltd.
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
import sys
from typing import Any

import pytest
from overrides import override

from charmcraft import extensions
from tests.extensions.test_extensions import FakeExtension


class MyFakeExtension(FakeExtension):
    """A fake test Extension that has complete behavior"""

    name = "test-extension"
    bases = [("ubuntu", "22.04")]

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""
        return {"terms": ["https://example.com/test"]}


# Add an extension to the project YAML.
@pytest.fixture
def fake_project_yaml(fake_project_yaml):
    return fake_project_yaml + "\nextensions: [test-extension]"


@pytest.fixture
def fake_extensions(stub_extensions):
    extensions.register(MyFakeExtension.name, MyFakeExtension)


def test_expand_extensions_simple(
    fake_project_yaml, monkeypatch, new_path, app, fake_extensions, emitter
):
    """Expand a charmcraft.yaml with a single extension."""
    monkeypatch.setattr(sys, "argv", ["charmcraft", "expand-extensions"])
    project = app.services.get("project").get()

    app.run()

    assert project.terms == ["https://example.com/test"]

    emitter.assert_message(project.to_yaml_string())
