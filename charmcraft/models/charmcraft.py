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
from typing import TypedDict, cast

import pydantic
from craft_application import util
from craft_application.models import CraftBaseModel
from typing_extensions import Self

from charmcraft.models.basic import AttributeName, LinterName


class BaseDict(TypedDict, total=False):
    """TypedDict that describes only one base.

    This is equivalent to the short form base definition.
    """

    name: str
    channel: str
    architectures: list[str]


LongFormBasesDict = TypedDict(
    "LongFormBasesDict", {"build-on": list[BaseDict], "run-on": list[BaseDict]}
)


class Charmhub(CraftBaseModel):
    """Definition of Charmhub endpoint configuration."""

    api_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://api.charmhub.io")
    storage_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://storage.snapcraftcontent.com")
    registry_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://registry.jujucharms.com")


class Base(CraftBaseModel):
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


class BasesConfiguration(CraftBaseModel):
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

    @pydantic.model_validator(mode="before")
    def _expand_base(cls, base: BaseDict | LongFormBasesDict) -> LongFormBasesDict:
        """Expand short-form bases into long-form bases."""
        if "build-on" in base:  # Assume long-form base already.
            return cast(LongFormBasesDict, base)
        return cast(LongFormBasesDict, {"build-on": [base], "run-on": [base]})


class Ignore(CraftBaseModel):
    """Definition of `analysis.ignore` configuration."""

    attributes: list[AttributeName] = []
    linters: list[LinterName] = []


class AnalysisConfig(CraftBaseModel):
    """Definition of `analysis` configuration."""

    ignore: Ignore = Ignore()


class Links(CraftBaseModel):
    """Definition of `links` in metadata."""

    contact: pydantic.StrictStr | list[pydantic.StrictStr] | None = None
    """Instructions for contacting the owner of the charm."""
    documentation: pydantic.AnyHttpUrl | None = None
    """The URL of the documentation for this charm."""
    issues: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None = None
    """A link to the issue tracker for this charm."""
    source: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None = None
    """Where to find this charm's source code."""
    website: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None = None
    """The website for this charm."""
