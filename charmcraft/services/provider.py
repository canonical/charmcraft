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

"""Service class for creating providers."""
from __future__ import annotations

from craft_application import services
from craft_providers import bases


class ProviderService(services.ProviderService):
    """Business logic for creating packages."""

    def get_base(
        self,
        base_name: bases.BaseName | tuple[str, str],
        *,
        instance_name: str,
        **kwargs: bool | str | None,
    ) -> bases.Base:
        """Get the base. Overridden because of compatibility tag."""
        alias = bases.get_base_alias(base_name)
        base_class = bases.get_base_from_alias(alias)
        kwargs.setdefault("compatibility_tag", f"charmcraft-{base_class.compatibility_tag}.0")
        return super().get_base(base_name, instance_name=instance_name, **kwargs)
