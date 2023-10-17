# Copyright 2020-2021 Canonical Ltd.
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

"""Expose needed names at main package level."""

from importlib.metadata import version, PackageNotFoundError
import os


def _get_version() -> str:
    if os.getenv("SNAP_NAME") == "charmcraft":
        return os.getenv("SNAP_VERSION", "")
    try:
        return version("charmcraft")
    except PackageNotFoundError:
        return "devel"


__version__ = _get_version()
