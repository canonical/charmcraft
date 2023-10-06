# Copyright 2020-2022 Canonical Ltd.
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

"""Collection of utilities for charmcraft."""

from charmcraft.utils.charmlibs import (
    LibData,
    LibInternals,
    get_name_from_metadata,
    create_charm_name_from_importable,
    create_importable_name,
    get_lib_internals,
    get_lib_info,
    get_libs_from_tree,
    collect_charmlib_pydeps,
)
from charmcraft.utils.cli import (
    SingleOptionEnsurer,
    ResourceOption,
    confirm_with_user,
    format_timestamp,
    humanize_list,
)
from charmcraft.utils.platform import (
    ARCH_TRANSLATIONS,
    OSPlatform,
    get_host_architecture,
    get_os_platform,
)
from charmcraft.utils.file import S_IRALL, S_IXALL, make_executable, useful_filepath, build_zip
from charmcraft.utils.package import (
    get_pypi_packages,
    PACKAGE_LINE_REGEX,
    get_package_names,
    exclude_packages,
    get_pip_command,
    get_pip_version,
    get_requirements_file_package_names,
    validate_strict_dependencies,
)
from charmcraft.utils.project import (
    find_charm_sources,
    get_charm_name_from_path,
    get_templates_environment,
)
from charmcraft.utils.store import ChannelData, Risk
from charmcraft.utils.yaml import load_yaml

__all__ = [
    "LibData",
    "LibInternals",
    "get_name_from_metadata",
    "create_charm_name_from_importable",
    "create_importable_name",
    "get_lib_internals",
    "get_lib_info",
    "get_libs_from_tree",
    "collect_charmlib_pydeps",
    "ARCH_TRANSLATIONS",
    "OSPlatform",
    "get_os_platform",
    "get_host_architecture",
    "S_IRALL",
    "S_IXALL",
    "make_executable",
    "useful_filepath",
    "build_zip",
    "PACKAGE_LINE_REGEX",
    "format_timestamp",
    "get_pypi_packages",
    "get_package_names",
    "exclude_packages",
    "get_pip_command",
    "get_pip_version",
    "get_requirements_file_package_names",
    "validate_strict_dependencies",
    "ChannelData",
    "Risk",
    "SingleOptionEnsurer",
    "ResourceOption",
    "confirm_with_user",
    "humanize_list",
    "find_charm_sources",
    "get_charm_name_from_path",
    "get_templates_environment",
    "load_yaml",
]
