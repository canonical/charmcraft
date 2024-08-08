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

"""Constants used in charmcraft."""
import enum
from typing import Literal

from craft_providers.bases import BaseName

# region Environment variables
ALTERNATE_AUTH_ENV_VAR = "CHARMCRAFT_AUTH"
DEVELOPER_MODE_ENV_VAR = "CHARMCRAFT_DEVELOPER"
EXPERIMENTAL_EXTENSIONS_ENV_VAR = "CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS"
IMAGE_INFO_ENV_VAR = "CHARMCRAFT_IMAGE_INFO"
PROVIDER_ENV_VAR = "CHARMCRAFT_PROVIDER"
SHARED_CACHE_ENV_VAR = "CRAFT_SHARED_CACHE"
STORE_API_ENV_VAR = "CHARMCRAFT_STORE_API_URL"
STORE_STORAGE_ENV_VAR = "CHARMCRAFT_UPLOAD_URL"
STORE_REGISTRY_ENV_VAR = "CHARMCRAFT_REGISTRY_URL"
# These are only for use within the managed environment
MANAGED_MODE_ENV_VAR = "CHARMCRAFT_MANAGED_MODE"
# endregion
# region Project files and directories
CHARMCRAFT_FILENAME = "charmcraft.yaml"
BUNDLE_FILENAME = "bundle.yaml"
MANIFEST_FILENAME = "manifest.yaml"
JUJU_CONFIG_FILENAME = "config.yaml"
METADATA_FILENAME = "metadata.yaml"
JUJU_ACTIONS_FILENAME = "actions.yaml"

WORK_DIRNAME = "work_dir"
BUILD_DIRNAME = "build"
VENV_DIRNAME = "venv"
STAGING_VENV_DIRNAME = "staging-venv"
# endregion
# region Output files and directories
# Dispatch script filename
DISPATCH_FILENAME = "dispatch"
# Hooks directory name
HOOKS_DIRNAME = "hooks"
# The minimum set of hooks to be provided for compatibility with old Juju
MANDATORY_HOOK_NAMES = frozenset(("install", "start", "upgrade-charm"))

CommonBaseStr = Literal[  # Bases supported as both build bases and run bases
    "ubuntu@18.04",
    "ubuntu@20.04",
    "ubuntu@22.04",
    "ubuntu@23.10",
    "ubuntu@24.04",
    "centos@7",
    "almalinux@9",
]
BaseStr = CommonBaseStr
BuildBaseStr = CommonBaseStr | Literal["ubuntu@devel"]

DEVEL_BASE_STRINGS = ()  # Bases that require a specified build base.

SUPPORTED_BASES = frozenset(
    (
        BaseName("ubuntu", "18.04"),
        BaseName("ubuntu", "20.04"),
        BaseName("ubuntu", "22.04"),
        BaseName("ubuntu", "23.10"),
        BaseName("ubuntu", "24.04"),
        BaseName("ubuntu", "devel"),
        BaseName("centos", "7"),
        BaseName("almalinux", "9"),
    )
)

SUPPORTED_OSES = frozenset(base.name for base in SUPPORTED_BASES)


class CharmArch(str, enum.Enum):
    """An architecture for a charm."""

    amd64 = "amd64"
    arm64 = "arm64"
    armhf = "armhf"
    ppc64el = "ppc64el"
    riscv64 = "riscv64"
    s390x = "s390x"

    def __str__(self) -> str:
        return str(self.value)


SUPPORTED_ARCHITECTURES = frozenset(arch.value for arch in CharmArch)


# The minimum set of files for a charm to be considered valid
CHARM_MANDATORY_FILES = frozenset(
    (
        DISPATCH_FILENAME,
        HOOKS_DIRNAME,
    )
)
# Optional files that can be present in a charm
CHARM_OPTIONAL_FILES = frozenset(
    (
        METADATA_FILENAME,
        JUJU_ACTIONS_FILENAME,
        JUJU_CONFIG_FILENAME,
        "metrics.yaml",
        "lxd-profile.yaml",
        "templates",
        "version",
        "lib",
        "mod",
        "LICENSE",
        "icon.svg",
        "README.md",
        "actions",
    )
)
# endregion

DEPENDENCIES_HASH_FILENAME = "charmcraft-dependencies-hash.txt"

# If Juju doesn't support the dispatch mechanism, it will execute the
# hook, and we'd need sys.argv[0] to be the name of the hook but it's
# getting lost by calling this dispatch, so we fake JUJU_DISPATCH_PATH
# to be the value it would've otherwise been.
DISPATCH_CONTENT = """#!/bin/sh

JUJU_DISPATCH_PATH="${{JUJU_DISPATCH_PATH:-$0}}" PYTHONPATH=lib:venv \\
  exec ./{entrypoint_relative_path}
"""

UBUNTU_LTS_STABLE = frozenset(
    (
        "18.04",
        "20.04",
        "22.04",
        "24.04",
    )
)

# Metadata keys that are defined in the metadata.yaml file, for backwards compatible
METADATA_YAML_KEYS = frozenset(
    (
        "assumes",
        "containers",
        "description",
        "devices",
        "display-name",
        "docs",
        "extra-bindings",
        "issues",
        "maintainers",
        "name",
        "peers",
        "provides",
        "requires",
        "resources",
        "series",
        "storage",
        "subordinate",
        "summary",
        "terms",
        "website",
    )
)

CHARM_METADATA_LEGARY_KEYS_ALIAS = frozenset(
    (
        "display_name",
        "extra_bindings",
    )
)

# Metadata keys that are allowed in the charmcraft.yaml file
CHARM_METADATA_KEYS = frozenset(
    (
        "assumes",
        "containers",
        "description",
        "devices",
        "title",
        "documentation",
        "extra-bindings",
        "links",
        "name",
        "peers",
        "provides",
        "requires",
        "resources",
        "storage",
        "subordinate",
        "summary",
        "terms",
    )
)

CHARM_METADATA_KEYS_ALIAS = frozenset(("extra_bindings",))

METADATA_YAML_MIGRATE_FIELDS = ("name", "summary", "description")
"""Fields that can exist in metadata.yaml or charmcraft.yaml, but not both."""
