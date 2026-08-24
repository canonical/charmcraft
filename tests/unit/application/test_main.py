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
from charmcraft.application.main import create_app


def test_experimental_monorepo_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(const.EXPERIMENTAL_MONOREPO_ENV_VAR, "1")

    app = create_app()
    app._configure_early_services()
    app._configure_services(None)

    assert app.services.get("config").get("experimental_monorepo") is True
    assert app.services.get("provider")._use_git_build_root is True
