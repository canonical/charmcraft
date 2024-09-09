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
"""YAML-related utilities for Charmcraft."""

from typing import Any

import pydantic
import yaml
from craft_cli import emit

from charmcraft import const


def load_yaml(fpath) -> dict[str, Any] | None:
    """Return the content of a YAML file."""
    if not fpath.is_file():
        emit.debug(f"Couldn't find config file {str(fpath)!r}")
        return None
    try:
        with fpath.open("r") as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        emit.debug(f"Failed to read/parse config file {str(fpath)!r}: {err!r}")
        return None
    return content


def _repr_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Multi-line string representer for the YAML dumper."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def dump_yaml(data: Any) -> str:  # noqa: ANN401: yaml.dump takes anything, so why can't we?
    """Dump a craft model to a YAML string."""
    yaml.add_representer(str, _repr_str, Dumper=yaml.SafeDumper)
    yaml.add_representer(
        pydantic.AnyHttpUrl, _repr_str, Dumper=yaml.SafeDumper  # type: ignore[arg-type]
    )
    yaml.add_representer(
        const.CharmArch,
        yaml.representer.SafeRepresenter.represent_str,
        Dumper=yaml.SafeDumper,
    )
    return yaml.dump(data, Dumper=yaml.SafeDumper, sort_keys=False)
