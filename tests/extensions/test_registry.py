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

import pytest

from charmcraft import errors, extensions
from charmcraft.extensions.extension import Extension


class FakeExtension1(Extension):
    """A fake test Extension"""

    name = "fake-extension-1"


class FakeExtension2(Extension):
    """A fake test Extension"""

    name = "fake-extension-2"


class FakeExtension3(Extension):
    """A fake test Extension"""

    name = "fake-extension-3"


@pytest.fixture()
def fake_extensions(stub_extensions):
    for ext_class in (FakeExtension1, FakeExtension2):
        extensions.register(ext_class.name, ext_class)


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
