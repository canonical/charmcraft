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


from textwrap import dedent
from typing import Any

import pytest
from overrides import override

from charmcraft import extensions
from charmcraft.commands.extensions import ExpandExtensionsCommand
from charmcraft.config import load
from tests.extensions.test_extensions import FakeExtension


class TestExtension(FakeExtension):
    """A fake test Extension that has complete behavior"""

    name = "test-extension"
    bases = [("ubuntu", "22.04")]

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""
        return {"terms": ["https://example.com/test"]}


@pytest.fixture()
def fake_extensions(stub_extensions):
    extensions.register(TestExtension.name, TestExtension)


def test_expand_extensions_simple(tmp_path, prepare_charmcraft_yaml, fake_extensions, emitter):
    """Expand a charmcraft.yaml with a single extension."""
    prepare_charmcraft_yaml(
        dedent(
            f"""
            name: test-charm-name
            type: charm
            summary: test-summary
            description: test-description
            extensions: [{TestExtension.name}]
            """
        )
    )

    config = load(tmp_path)
    cmd = ExpandExtensionsCommand(config)
    cmd.run([])
    emitter.assert_message(
        dedent(
            """\
            analysis:
              ignore:
                attributes: []
                linters: []
            charmhub:
              api-url: https://api.charmhub.io
              registry-url: https://registry.jujucharms.com
              storage-url: https://storage.snapcraftcontent.com
            description: test-description
            name: test-charm-name
            parts: {}
            summary: test-summary
            terms:
            - https://example.com/test
            type: charm
            """
        )
    )
