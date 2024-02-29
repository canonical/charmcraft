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
"""Tests for extension commands."""
import argparse
import textwrap

import pytest

from charmcraft import application, extensions
from charmcraft.application import commands


def create_extension(ext_name, bases, experimental):
    class FakeExtension(extensions.Extension):
        name = ext_name

        @staticmethod
        def get_supported_bases() -> list[tuple[str, str]]:
            return bases + experimental

        @staticmethod
        def is_experimental(base: tuple[str, str] | None) -> bool:
            return base in experimental

    return FakeExtension


@pytest.fixture(autouse=True, scope="module")
def registered_extensions():
    default_extensions = {
        name: extensions.get_extension_class(name) for name in extensions.get_extension_names()
    }
    for ext in default_extensions:
        extensions.unregister(ext)
    fake_extensions = [
        create_extension("f1", [("ubuntu", "22.04")], [("ubuntu", "24.04")]),
        create_extension("f2", [], [("almalinux", "9")]),
    ]
    for ext in fake_extensions:
        extensions.register(ext.name, ext)
    yield fake_extensions
    for ext in fake_extensions:
        extensions.unregister(ext.name)
    for name, cls in default_extensions.items():
        extensions.register(name, cls)


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (
            None,
            textwrap.dedent(
                """\
            Extension name    Supported bases    Experimental bases
            ----------------  -----------------  --------------------
            f1                ubuntu@22.04       ubuntu@24.04
            f2                                   almalinux@9"""
            ),
        ),
        (
            "json",
            textwrap.dedent(
                """\
            [
                {
                    "name": "f1",
                    "bases": [
                        "ubuntu@22.04"
                    ],
                    "experimental_bases": [
                        "ubuntu@24.04"
                    ]
                },
                {
                    "name": "f2",
                    "bases": [],
                    "experimental_bases": [
                        "almalinux@9"
                    ]
                }
            ]"""
            ),
        ),
    ],
)
def test_list_extensions(emitter, fmt, expected):
    cmd = commands.ListExtensionsCommand(
        {
            "app": application.APP_METADATA,
            "services": None,
        }
    )

    cmd.run(argparse.Namespace(format=fmt))

    emitter.assert_message(expected)
