# Copyright 2023-2024 Canonical Ltd.
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

"""Charmcraft configuration pydantic model."""
import datetime
import os
import pathlib
from typing import Any, Literal, cast

import pydantic
from craft_application import util
from craft_application.util.error_formatting import format_pydantic_errors
from craft_cli import CraftError
from typing_extensions import Self

from charmcraft import const, parts
from charmcraft.extensions import apply_extensions
from charmcraft.models.actions import JujuActions
from charmcraft.models.basic import AttributeName, LinterName, ModelConfigDefaults
from charmcraft.models.config import JujuConfig


class CharmhubConfig(
    ModelConfigDefaults,
    alias_generator=lambda s: s.replace("_", "-"),
    frozen=True,
):
    """Definition of Charmhub endpoint configuration."""

    api_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://api.charmhub.io")
    storage_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://storage.snapcraftcontent.com")
    registry_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://registry.jujucharms.com")


class Base(ModelConfigDefaults, frozen=True):
    """Represents a base."""

    name: pydantic.StrictStr
    channel: pydantic.StrictStr
    architectures: list[pydantic.StrictStr] = [util.get_host_architecture()]

    @classmethod
    def from_str_and_arch(cls, base_str: str, architectures: list[str]) -> Self:
        """Get a Base from a base string and list of architectures.

        :param base_str: A base string along the lines of "<name>@<channel>"
        :param architectures: A list of architectures (or ["all"])
        """
        name, _, channel = base_str.partition("@")
        return cls(name=name, channel=channel, architectures=architectures)


class BasesConfiguration(
    ModelConfigDefaults,
    alias_generator=lambda s: s.replace("_", "-"),
    frozen=True,
):
    """Definition of build-on/run-on combinations.

    Example::

        bases:
          - build-on:
              - name: ubuntu
                channel: "20.04"
                architectures: [amd64, arm64]
            run-on:
              - name: ubuntu
                channel: "20.04"
                architectures: [amd64, arm64]
              - name: ubuntu
                channel: "22.04"
                architectures: [amd64, arm64]
    """

    build_on: list[Base]
    run_on: list[Base]


class Ignore(ModelConfigDefaults, frozen=True):
    """Definition of `analysis.ignore` configuration."""

    attributes: list[AttributeName] = []
    linters: list[LinterName] = []


class AnalysisConfig(ModelConfigDefaults, allow_population_by_field_name=True, frozen=True):
    """Definition of `analysis` configuration."""

    ignore: Ignore = Ignore()


class Links(ModelConfigDefaults, frozen=True):
    """Definition of `links` in metadata."""

    contact: pydantic.StrictStr | list[pydantic.StrictStr] | None
    """Instructions for contacting the owner of the charm."""
    documentation: pydantic.AnyHttpUrl | None
    """The URL of the documentation for this charm."""
    issues: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    """A link to the issue tracker for this charm."""
    source: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    """Where to find this charm's source code."""
    website: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    """The website for this charm."""
