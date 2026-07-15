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

import abc
from typing import Any

import craft_parts.constraints
import pydantic
from pydantic_core import core_schema
from typing_extensions import Self, override


class _CustomStrictStr(str, metaclass=abc.ABCMeta):
    """Abstract base class for strict string types with custom validation."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: type[Any], _handler: pydantic.GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Get the Pydantic schema."""
        return core_schema.no_info_after_validator_function(
            cls._strict_validate,
            core_schema.str_schema(strict=True),
        )

    @classmethod
    def _strict_validate(cls, value: str) -> Self:
        """Validate and cast the value to this class."""
        return cls(cls.custom_validate(value))

    @classmethod
    @abc.abstractmethod
    def custom_validate(cls, value: str) -> str:
        """Apply custom validation."""
        raise NotImplementedError


class AttributeName(_CustomStrictStr):  # TODO: Turn this into a StrEnum
    """Constrained string that must match a known attribute checker name."""

    @classmethod
    @override
    def custom_validate(cls, value: str) -> str:
        """Validate attribute name."""
        from charmcraft import linters  # noqa: PLC0415  prevent circular imports

        valid_names = [
            checker.name
            for checker in linters.CHECKERS
            if checker.check_type == linters.CheckType.ATTRIBUTE
        ]
        if value not in valid_names:
            raise ValueError(f"Bad attribute name {value!r}")
        return value


class LinterName(_CustomStrictStr):
    """Constrained string that must match a known linter checker name."""

    @classmethod
    @override
    def custom_validate(cls, value: str) -> str:
        """Validate linter name."""
        from charmcraft import linters  # noqa: PLC0415  prevent circular imports

        valid_names = [
            checker.name
            for checker in linters.CHECKERS
            if checker.check_type == linters.CheckType.LINT
        ]
        if value not in valid_names:
            raise ValueError(f"Bad lint name {value!r}")
        return value


RelativePath = craft_parts.constraints.RelativePathStr
