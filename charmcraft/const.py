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

METADATA_FILENAME = "metadata.yaml"
IMAGE_INFO_ENV_VAR = "CHARMCRAFT_IMAGE_INFO"

WORK_DIRNAME = "work_dir"
BUILD_DIRNAME = "build"
VENV_DIRNAME = "venv"
STAGING_VENV_DIRNAME = "staging-venv"

DEPENDENCIES_HASH_FILENAME = "charmcraft-dependencies-hash.txt"

# The file name and template for the dispatch script
DISPATCH_FILENAME = "dispatch"

# If Juju doesn't support the dispatch mechanism, it will execute the
# hook, and we'd need sys.argv[0] to be the name of the hook but it's
# getting lost by calling this dispatch, so we fake JUJU_DISPATCH_PATH
# to be the value it would've otherwise been.
DISPATCH_CONTENT = """#!/bin/sh

JUJU_DISPATCH_PATH="${{JUJU_DISPATCH_PATH:-$0}}" PYTHONPATH=lib:venv \\
  exec ./{entrypoint_relative_path}
"""

# The minimum set of hooks to be provided for compatibility with old Juju
MANDATORY_HOOK_NAMES = {"install", "start", "upgrade-charm"}
HOOKS_DIRNAME = "hooks"

# The minimum set of files for a charm to be considered valid
CHARM_FILES = [
    DISPATCH_FILENAME,
    HOOKS_DIRNAME,
]

# Optional files that can be present in a charm
CHARM_OPTIONAL = [
    METADATA_FILENAME,
    "config.yaml",
    "metrics.yaml",
    "actions.yaml",
    "lxd-profile.yaml",
    "templates",
    "version",
    "lib",
    "mod",
    "LICENSE",
    "icon.svg",
    "README.md",
    "actions",
]

CHARM_METADATA_KEYS = {
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
}
