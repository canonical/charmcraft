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

"""Charmcraft basic pydantic model."""
import craft_application.models
import pydantic


class ModelConfigDefaults(
    craft_application.models.CraftBaseModel,
    frozen=True,  # pyright: ignore[reportGeneralTypeIssues]
    validate_all=True,
    allow_population_by_field_name=False,
    alias_generator=pydantic.BaseConfig.alias_generator,
):
    """Define Charmcraft's defaults for the BaseModel configuration."""


class CustomStrictStr(pydantic.StrictStr):
    """Generic class to create custom strict strings validated by pydantic."""

    @classmethod
    # TODO[pydantic]: We couldn't refactor `__get_validators__`, please create the `__get_pydantic_core_schema__` manually.
    # Check https://docs.pydantic.dev/latest/migration/#defining-custom-types for more information.
    def __get_validators__(cls):
        """Yield the relevant validators."""
        yield from super().__get_validators__()
        yield cls.custom_validate


class RelativePath(CustomStrictStr):
    """Constrained string which must be a relative path."""

    @classmethod
    def custom_validate(cls, value: str) -> str:
        """Validate relative path.

        Check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
        config is independent of the platform where charmcraft is running.
        """
        if not value:
            raise ValueError(f"{value!r} must be a valid relative path (cannot be empty)")

        if value[0] == "/":
            raise ValueError(f"{value!r} must be a valid relative path (cannot start with '/')")

        return value


class AttributeName(CustomStrictStr):
    """Constrained string that must match the name of an attribute from linters.CHECKERS."""

    @classmethod
    def custom_validate(cls, value: str) -> str:
        """Validate attribute name."""
        from charmcraft import linters  # import here to avoid cyclic imports

        valid_names = [
            checker.name
            for checker in linters.CHECKERS
            if checker.check_type == linters.CheckType.ATTRIBUTE
        ]
        if value not in valid_names:
            raise ValueError(f"Bad attribute name {value!r}")
        return value


class LinterName(CustomStrictStr):
    """Constrained string that must match the name of a linter from linters.CHECKERS."""

    @classmethod
    def custom_validate(cls, value: str) -> str:
        """Validate attribute name."""
        from charmcraft import linters  # import here to avoid cyclic imports

        valid_names = [
            checker.name
            for checker in linters.CHECKERS
            if checker.check_type == linters.CheckType.LINT
        ]
        if value not in valid_names:
            raise ValueError(f"Bad lint name {value!r}")
        return value
