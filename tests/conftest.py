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

import contextlib
import datetime
import pathlib
import tempfile
from typing import List, Tuple
from unittest import mock

import pytest
import responses as responses_module
from craft_providers import Executor

from charmcraft import config as config_module
from charmcraft import deprecations, parts
from charmcraft.config import Base
from charmcraft.providers import Provider


@pytest.fixture()
def caplog_filter(caplog):
    """Simplify log checking by filtering for desired module and return list of (lvl,msg)."""

    def filter(logger_name) -> List[Tuple[int, str]]:
        return [(r.levelno, r.message) for r in caplog.records if r.name == logger_name]

    return filter


@pytest.fixture(autouse=True, scope="session")
def tmpdir_under_tmpdir(tmpdir_factory):
    tempfile.tempdir = str(tmpdir_factory.getbasetemp())


@pytest.fixture(autouse=True, scope="session")
def setup_parts():
    parts.setup_parts()


@pytest.fixture
def monkeypatch(monkeypatch):
    """Adapt pytest's monkeypatch to support stdlib's pathlib."""

    class Monkeypatcher:
        """Middle man for chdir."""

        def _chdir(self, value):
            """Change dir, but converting to str first.

            This is because Py35 monkeypatch doesn't support stdlib's pathlib.
            """
            return monkeypatch.chdir(str(value))

        def __getattribute__(self, name):
            if name == "chdir":
                return object.__getattribute__(self, "_chdir")
            else:
                return getattr(monkeypatch, name)

    return Monkeypatcher()


@pytest.fixture
def config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(config_module.Config, frozen=False):
        """The Config, but with a method to set test values."""

        def set(self, prime=None, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            if prime is not None:
                self.parts["charm"] = {"prime": prime}

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    project = config_module.Project(
        dirpath=tmp_path,
        started_at=datetime.datetime.utcnow(),
        config_provided=True,
    )

    # implicit plugin is added by the validator during unmarshal
    parts = {
        "charm": {
            "plugin": "charm",
        }
    }

    return TestConfig(type="charm", parts=parts, project=project)


@pytest.fixture
def bundle_config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(config_module.Config, frozen=False):
        """The Config, but with a method to set test values."""

        def set(self, prime=None, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            if prime is not None:
                self.parts["bundle"] = {"prime": prime}

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    project = config_module.Project(
        dirpath=tmp_path,
        started_at=datetime.datetime.utcnow(),
        config_provided=True,
    )

    return TestConfig(type="bundle", project=project)


@pytest.fixture(autouse=True)
def clean_already_notified():
    """Clear the already-notified structure for each test.

    This is needed as that structure is a module-level one (by design), so otherwise
    it will be dirty between tests.
    """
    deprecations._ALREADY_NOTIFIED.clear()


@pytest.fixture
def responses():
    """Simple helper to use responses module as a fixture, for easier integration in tests."""
    with responses_module.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_instance():
    """Provide a mock instance (Executor)."""
    yield mock.Mock(spec=Executor)


@pytest.fixture(autouse=True)
def fake_provider(mock_instance, monkeypatch):
    """Provide a minimal/fake provider."""

    class FakeProvider(Provider):
        def clean_project_environments(
            self,
            *,
            charm_name: str,
            project_path: pathlib.Path,
        ) -> List[str]:
            return []

        @classmethod
        def ensure_provider_is_available(cls) -> None:
            pass

        @contextlib.contextmanager
        def launched_environment(
            self,
            *,
            charm_name: str,
            project_path: pathlib.Path,
            base: Base,
            bases_index: int,
            build_on_index: int,
        ):
            yield mock_instance

        @classmethod
        def is_provider_available(cls) -> bool:
            """Check if provider is installed and available for use.

            :returns: True if installed.
            """
            return True

    return FakeProvider()


@pytest.fixture
def create_config(tmp_path):
    """Helper to create a config file in disk."""

    def create_config(text):
        test_file = tmp_path / "charmcraft.yaml"
        test_file.write_text(text)
        return tmp_path

    return create_config
