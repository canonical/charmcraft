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

"""Extension base class definition."""

import abc
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, final

from craft_cli import emit

from charmcraft import const, errors


class Extension(abc.ABC):
    """Extension is the class from which all extensions inherit.

    Extensions have the ability to add snippets to charms, parts, config, actions,
    and indeed add new parts to a given charmcraft.yaml.
    :ivar project_root: the root of the project.
    :ivar yaml_data: the raw yaml data.
    """

    def __init__(
        self,
        *,
        project_root: Path,
        yaml_data: dict[str, Any],
    ) -> None:
        """Create a new Extension."""
        self.project_root = project_root
        self.yaml_data: Final[dict[str, Any]] = yaml_data

    @staticmethod
    @abc.abstractmethod
    def get_supported_bases() -> list[tuple[str, str]]:
        """Return a list of tuple of supported bases."""

    @staticmethod
    @abc.abstractmethod
    def is_experimental(base: tuple[str, str] | None) -> bool:
        """Return whether or not this extension is unstable for given base."""

    @abc.abstractmethod
    def get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to apply."""

    @abc.abstractmethod
    def get_part_snippet(self) -> dict[str, Any]:
        """Return the part snippet to apply to existing parts."""

    @abc.abstractmethod
    def get_parts_snippet(self) -> dict[str, Any]:
        """Return the parts to add to parts."""

    @final
    def validate(self, extension_name: str):
        """Validate that the extension can be used with the current project.

        :param extension_name: the name of the extension being parsed.
        :raises errors.ExtensionError: if the extension is incompatible with the project.
        """
        if "bases" not in self.yaml_data:
            # There is nothing to validate, the extension will set the preferred base.
            return

        bases: list = self.yaml_data["bases"]

        for base in bases:
            for build_on in base.get("build-on", []):
                build_base = (build_on["name"], build_on["channel"])

                if self.is_experimental(build_base) and not os.getenv(
                    const.EXPERIMENTAL_EXTENSIONS_ENV_VAR
                ):
                    raise errors.ExtensionError(
                        f"Extension is experimental: {extension_name!r}",
                        docs_url="https://juju.is/docs/sdk/charmcraft-config",  # no docs yet
                    )

                if self.is_experimental(build_base):
                    emit.progress(
                        f"*EXPERIMENTAL* extension {extension_name!r} enabled",
                        permanent=True,
                    )

                if build_base not in self.get_supported_bases():
                    raise errors.ExtensionError(
                        f"Extension {extension_name!r} does not support base: {build_base!r}"
                    )

        invalid_parts = [
            p for p in self.get_parts_snippet() if not p.startswith(f"{extension_name}/")
        ]
        if invalid_parts:
            raise ValueError(
                f"Extension has invalid part names: {invalid_parts!r}. "
                "Format is <extension-name>/<part-name>"
            )


def get_extensions_data_dir() -> Path:
    """Return the path to the extension data directory."""
    return Path(sys.prefix) / "share" / "charmcraft" / "extensions"


def append_to_env(env_variable: str, paths: Sequence[str], separator: str = ":") -> str:
    """Return a string for env_variable with one of more paths appended.

    :param env_variable: the variable to operate on.
    :param paths: one or more paths to append.
    :param separator: the separator to use.
    :returns: a shell string where one or more paths are appended
                  to env_variable. The code takes into account the case
                  where the environment variable is empty, to avoid putting
                  a separator token at the start.
    """
    return f"${{{env_variable}:+${env_variable}{separator}}}" + separator.join(paths)


def prepend_to_env(env_variable: str, paths: Sequence[str], separator: str = ":") -> str:
    """Return a string for env_variable with one of more paths prepended.

    :param env_variable: the variable to operate on.
    :param paths: one or more paths to append.
    :param separator: the separator to use.
    :returns: a shell string where one or more paths are prepended
                  before env_variable. The code takes into account the case
                  where the environment variable is empty, to avoid putting
                  a separator token at the end.
    """
    return separator.join(paths) + f"${{{env_variable}:+{separator}${env_variable}}}"
