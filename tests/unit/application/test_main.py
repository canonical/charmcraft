# Copyright 2026 Canonical Ltd.
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
"""Unit tests for Charmcraft main application entry point and metadata."""

import pytest

from charmcraft import const
from charmcraft.application.main import APP_METADATA, create_app


def test_app_metadata_allows_git_build_root() -> None:
    assert APP_METADATA.allow_git_build_root is True


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        (None, False),
        ("0", False),
        ("false", False),
        ("no", False),
        ("n", False),
        ("1", True),
        ("true", True),
        ("yes", True),
        ("y", True),
    ],
)
def test_experimental_monorepo_config(
    monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected: bool
) -> None:
    if env_value is None:
        monkeypatch.delenv(const.EXPERIMENTAL_MONOREPO_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(const.EXPERIMENTAL_MONOREPO_ENV_VAR, env_value)

    app = create_app()
    app._configure_early_services()
    app._configure_services(None)

    assert app.services.get("config").get("experimental_monorepo") is expected
    assert app.services.get("provider")._use_git_build_root is expected
