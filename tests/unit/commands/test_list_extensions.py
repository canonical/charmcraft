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
import argparse
from textwrap import dedent
from typing import Any

import pytest
from overrides import override

from charmcraft import extensions
from charmcraft.application.commands.extensions import ListExtensionsCommand
from tests.extensions.test_extensions import FakeExtension


class MyFakeExtension(FakeExtension):
    """A fake test Extension that has complete behavior"""

    name = "test-extension"
    bases = [("ubuntu", "22.04")]

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""
        return {"terms": ["https://example.com/test"]}


class YourFakeExtension(FakeExtension):
    """A fake test Extension that has complete behavior"""

    name = "test-extension-2"
    bases = [("ubuntu", "23.04")]

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""
        return {"terms": ["https://example.com/test2"]}


@pytest.fixture
def fake_extensions(stub_extensions):
    extensions.register(MyFakeExtension.name, MyFakeExtension)
    extensions.register(YourFakeExtension.name, YourFakeExtension)


def test_expand_extensions_simple(fake_extensions, emitter):
    """List extensions"""
    cmd = ListExtensionsCommand(None)
    cmd.run(argparse.Namespace(format=None))
    emitter.assert_message(
        dedent(
            """\
            Extension name    Supported bases    Experimental bases
            ----------------  -----------------  --------------------
            test-extension    ubuntu@22.04
            test-extension-2  ubuntu@23.04"""
        )
    )
