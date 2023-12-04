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

"""Extension registry."""
from typing import Any

from charmcraft import errors
from charmcraft.extensions.extension import Extension

_EXTENSIONS: dict[str, type[Extension]] = {}


def get_extension_names() -> list[str]:
    """Obtain a extension class given the name.

    :param name: The extension name.
    :return: The list of available extensions.
    :raises ExtensionError: If the extension name is invalid.
    """
    return list(_EXTENSIONS.keys())


def get_extension_class(extension_name: str) -> type[Extension]:
    """Obtain a extension class given the name.

    :param extension_name: The extension name.
    :return: The extension class.
    :raises ExtensionError: If the extension name is invalid.
    """
    try:
        return _EXTENSIONS[extension_name]
    except KeyError:
        raise errors.ExtensionError(
            f"Extension {extension_name!r} does not exist",
            details=f"Registered extensions: {get_extension_names()}",
        ) from None


def get_extensions() -> list[dict[str, Any]]:
    """Get metadata about registered extensions."""
    return sorted(
        (
            {
                "name": name,
                "bases": [
                    "@".join(base)
                    for base in cls.get_supported_bases()
                    if not cls.is_experimental(base)
                ],
                "experimental_bases": [
                    "@".join(base)
                    for base in cls.get_supported_bases()
                    if cls.is_experimental(base)
                ],
            }
            for name, cls in _EXTENSIONS.items()
        ),
        key=lambda d: d["name"],
    )


def register(extension_name: str, extension_class: type[Extension]) -> None:
    """Register extension.

    :param extension_name: the name to register.
    :param extension_class: the Extension implementation.
    """
    _EXTENSIONS[extension_name] = extension_class


def unregister(extension_name: str) -> None:
    """Unregister extension_name.

    :raises KeyError: if extension_name is not registered.
    """
    del _EXTENSIONS[extension_name]
