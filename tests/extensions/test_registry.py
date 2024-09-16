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
import contextlib

import pytest

from charmcraft import errors, extensions
from charmcraft.extensions.extension import Extension


class FakeExtension1(Extension):
    """A fake test Extension"""

    name = "fake-extension-1"

    @staticmethod
    def get_supported_bases() -> list[tuple[str, str]]:
        return [("ubuntu", "22.04")]

    @staticmethod
    def is_experimental(_base: tuple[str, str] | None) -> bool:
        return False


class FakeExtension2(Extension):
    """A fake test Extension"""

    name = "fake-extension-2"

    @staticmethod
    def get_supported_bases() -> list[tuple[str, str]]:
        return [("ubuntu", "24.04"), ("ubuntu", "22.04")]

    @staticmethod
    def is_experimental(base: tuple[str, str] | None) -> bool:
        return base == ("ubuntu", "24.04")


class FakeExtension3(Extension):
    """A fake test Extension"""

    name = "fake-extension-3"


@pytest.fixture
def fake_extensions(stub_extensions):
    fakes = [FakeExtension1, FakeExtension2]
    for ext_class in fakes:
        extensions.register(ext_class.name, ext_class)
    yield fakes
    for ext_class in fakes:
        with contextlib.suppress(KeyError):
            extensions.unregister(ext_class.name)


def test_get_extension_names(fake_extensions):
    assert extensions.get_extension_names() == [
        FakeExtension1.name,
        FakeExtension2.name,
    ]


def test_get_extension_class(fake_extensions):
    assert extensions.get_extension_class(FakeExtension1.name) is FakeExtension1
    assert extensions.get_extension_class(FakeExtension2.name) is FakeExtension2


def test_get_extension_class_error(fake_extensions):
    with pytest.raises(errors.ExtensionError):
        extensions.get_extension_class(FakeExtension3.name)


def test_get_extensions(fake_extensions):
    assert extensions.get_extensions() == [
        {"name": "fake-extension-1", "bases": [("ubuntu@22.04")], "experimental_bases": []},
        {
            "name": "fake-extension-2",
            "bases": [("ubuntu@22.04")],
            "experimental_bases": [("ubuntu@24.04")],
        },
    ]


def test_register(fake_extensions):
    assert FakeExtension3.name not in extensions.get_extension_names()
    extensions.register(FakeExtension3.name, FakeExtension3)
    assert FakeExtension3.name in extensions.get_extension_names()
    assert extensions.get_extension_class(FakeExtension3.name) is FakeExtension3


def test_unregister(fake_extensions):
    assert extensions.get_extension_class(FakeExtension1.name) is FakeExtension1
    extensions.unregister(FakeExtension1.name)
    with pytest.raises(errors.ExtensionError):
        extensions.get_extension_class(FakeExtension1.name)
