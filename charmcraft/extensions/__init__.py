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

"""Extension processor and related utilities."""

from charmcraft.extensions._utils import apply_extensions
from charmcraft.extensions.app import DjangoFramework, FlaskFramework, GoFramework
from charmcraft.extensions.extension import Extension
from charmcraft.extensions.registry import (
    get_extension_class,
    get_extension_names,
    get_extensions,
    register,
    unregister,
)

__all__ = [
    "DjangoFramework",
    "Extension",
    "FlaskFramework",
    "get_extension_class",
    "get_extension_names",
    "get_extensions",
    "apply_extensions",
    "register",
    "unregister",
]

register("flask-framework", FlaskFramework)
register("django-framework", DjangoFramework)
register("go-framework", GoFramework)
