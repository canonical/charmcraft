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
"""Project-related models for Charmcraft."""
import datetime
import pathlib
from typing import List, Optional, Any, cast, Type, Iterator

import pydantic
from craft_application import models
from craft_application.util import safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases
from pydantic import dataclasses
from typing_extensions import Self

from craft_application import errors
from charmcraft.models import charmcraft
from charmcraft.models.charmcraft import CharmcraftConfig


@dataclasses.dataclass
class CharmBuildInfo(models.BuildInfo):
    """Information about a single build option, with charmcraft-specific info.

    With CharmBuildInfo, the build_for may also be the string "multi", meaning the charm
    is expected to run on multiple architectures.
    """

    build_for_bases: List[charmcraft.Base]
    """Charmcraft base to build for, including potentially multiple architectures."""
    bases_index: int
    """Index of the base configuration in charmcraft.yaml."""
    build_on_index: int
    """Index of this base configuration's build-on option."""

    @classmethod
    def from_build_on_run_on(
        cls: Type[Self],
        build_on_base: charmcraft.Base,
        build_on_arch: str,
        run_on: List[charmcraft.Base],
        *,
        bases_index: int,
        build_on_index: int,
    ) -> Self:
        """Create a single CharmBuildInfo from a build_on base and run_on bases

        :param build_on_base: A Base object defining a base on which to build
        :param build_on_arch: The architecture on which to run the build (e.g. "amd64")
        :param run_on: A list of bases which this charm should run on after the build.
        :param bases_index: The index of the BasesConfiguration
        :param build_on_index: Which build-on value from the BasesConfiguration to use
        """
        base = bases.BaseName(name=build_on_base.name, version=build_on_base.channel)

        all_architectures = set()
        for run_on_base in run_on:
            all_architectures.update(run_on_base.architectures)

        if len(all_architectures) == 1:
            build_for = all_architectures.pop()
        else:
            build_for = "multi"

        return cls(
            build_on=build_on_arch,
            build_for=build_for,
            base=base,
            build_for_bases=run_on,
            bases_index=bases_index,
            build_on_index=build_on_index,
        )

    @classmethod
    def gen_from_bases_configurations(
        cls: Type[Self], *bases_configs: charmcraft.BasesConfiguration
    ) -> Iterator[Self]:
        """Generate CharmBuildInfo objects from a BasesConfiguration object.

        :param bases_config: One or more BasesConfiguration objects from which to generate
            CharmBuildInfo objects.
        :returns: A list of CharmBuildInfo objects from this BasesConfiguration.
        """
        for bases_index, bases_config in enumerate(bases_configs):
            for build_on_index, build_on_base in enumerate(bases_config.build_on):
                for build_on_arch in build_on_base.architectures:
                    yield cls.from_build_on_run_on(
                        build_on_base,
                        build_on_arch,
                        bases_config.run_on,
                        bases_index=bases_index,
                        build_on_index=build_on_index,
                    )


class CharmcraftProject(CharmcraftConfig, models.Project):
    """A craft-application compatible version of a Charmcraft project.

    This is a Project definition for charmcraft commands that are run through
    craft-application rather than the legacy charmcraft entrypoint. Eventually
    it will be the only form of the project.

    In legacy Charmcraft, this is referred to as CharmcraftConfig.
    """

    version: Optional[models.VersionStr]

    def __init__(self, **data: Any):
        models.Project.__init__(self, **data)
        CharmcraftConfig.__init__(self, **data)

    @classmethod
    def from_yaml_file(cls, path: pathlib.Path) -> Self:
        """Instantiate this model from a YAML file.

        For use with craft-application.
        """
        with path.open() as file:
            data = safe_yaml_load(file)
        try:
            from charmcraft.models.charmcraft import Project

            return cls.unmarshal(
                data,
                Project(
                    dirpath=path.parent,
                    started_at=datetime.datetime.utcnow(),
                    config_provided=True,
                ),
            )
        except pydantic.ValidationError as err:
            raise errors.CraftValidationError.from_pydantic(err, file_name=path.name) from None

    def get_build_plan(self) -> List[models.BuildInfo]:
        """Get build bases for this charmcraft project.

        This method provides a flattened version of every way to build the charm, unfiltered.

        Example 1: a simple charm:
            bases:
              - name: ubuntu
                channel: 24.04
        This gets expanded to a standard long-form:
            bases:
              - build-on:
                  - name: ubuntu
                    channel: "24.04"
                run-on:
                  - name: ubuntu
                    channel: "24.04"
        Presuming charmcraft is run on riscv64 (if architectures are not specified charmcraft will
        use the host architecture as the only architecture), it will output a list containing the
        following single BuildInfo object:
            CharmBuildInfo(
                build_on="riscv64",
                build_for="riscv64",
                base=BaseName(name="ubuntu", channel="24.04"),
                build_for_base=BaseName(name="ubuntu", channel="24.04"),
                bases_index=0,
                build_on_index=0
            )

        Example 2: a more complex set of bases:
            bases:
              - build-on:
                  - name: ubuntu
                    channel: "24.04"
                    architectures: ["amd64", "riscv64"]
                  - name: ubuntu
                    channel: "22.04"
                    architectures: ["arm64"]
                run-on:
                  - name: ubuntu
                    channel: "22.04"
                    architectures: ["amd64", "arm64"]
                  - name: ubuntu
                    channel: "24.04"
                    architectures: ["amd64", "arm64", "riscv64"]
        This will result in the following builds in the plan:
        [
            CharmBuildInfo(
                build_on="amd64",
                build_for="multi",
                base=BaseName(name="ubuntu", channel="24.04"),
                build_for_bases=[
                    Base(name="ubuntu", channel="22.04", architectures=["amd64", "arm64"]),
                    Base(name="ubuntu", channel="24.04", architectures=["amd64", "arm64", "riscv64"])
                ]
                bases_index=0,
                build_on_index=0
            ),
            CharmBuildInfo(
                build_on="riscv64",
                build_for="multi",
                base=BaseName(name="ubuntu", channel="24.04"),
                build_for_bases=[
                    Base(name="ubuntu", channel="22.04", architectures=["amd64", "arm64"]),
                    Base(name="ubuntu", channel="24.04", architectures=["amd64", "arm64", "riscv64"])
                ]
                bases_index=0,
                build_on_index=0
            ),
            CharmBuildInfo(
                build_on="arm64",
                build_for="multi",
                base=BaseName(name="ubuntu", channel="22.04"),
                build_for_bases=[
                    Base(name="ubuntu", channel="22.04", architectures=["amd64", "arm64"]),
                    Base(name="ubuntu", channel="24.04", architectures=["amd64", "arm64", "riscv64"])
                ]
                bases_index=0,
                build_on_index=1
            ),
        ]

        Here the string "multi" defines a destination platform that has multiple architectures.
        """
        if not self.bases:
            raise CraftError("Cannot create build plan because no bases were provided.")

        return list(CharmBuildInfo.gen_from_bases_configurations(*self.bases))
