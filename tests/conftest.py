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
import os
import pathlib
import re
import tempfile
from typing import List
from unittest.mock import Mock, call

import pytest
import responses as responses_module
from craft_cli import messages
from craft_providers import Executor

from charmcraft import config as config_module
from charmcraft import deprecations, parts
from charmcraft.config import Base
from charmcraft.providers import Provider


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
                if self.parts is None:
                    self.parts = {}
                self.parts["charm"] = {"plugin": "charm", "prime": prime}

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    project = config_module.Project(
        dirpath=tmp_path,
        started_at=datetime.datetime.utcnow(),
        config_provided=True,
    )

    return TestConfig(type="charm", project=project)


@pytest.fixture
def bundle_config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(config_module.Config, frozen=False):
        """The Config, but with a method to set test values."""

        def set(self, prime=None, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            if prime is not None:
                if self.parts is None:
                    self.parts = {}
                self.parts["bundle"] = {"plugin": "bundle", "prime": prime}

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
    yield Mock(spec=Executor)


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


class RegexComparingText(str):
    """A string that compares for equality using regex.match."""

    def __eq__(self, other):
        return bool(re.match(self, other, re.DOTALL))

    def __hash__(self):
        return str.__hash__(self)


class RecordingEmitter:
    """Record what is shown using the emitter and provide a nice API for tests."""

    def __init__(self):
        self.interactions = []

    def record(self, method_name, args, kwargs):
        """Record the method call and its specific parameters."""
        self.interactions.append(call(method_name, *args, **kwargs))

    def _check(self, expected_text, method_name, regex, **kwargs):
        """Really verify messages."""
        if regex:
            expected_text = RegexComparingText(expected_text)
        expected_call = call(method_name, expected_text, **kwargs)
        for stored_call in self.interactions:
            if stored_call == expected_call:
                return stored_call.args[1]
        raise AssertionError(f"Expected call {expected_call} not found in {self.interactions}")

    def assert_message(self, expected_text, intermediate=None, regex=False):
        """Check the 'message' method was properly used."""
        if intermediate is None:
            return self._check(expected_text, "message", regex)
        else:
            return self._check(expected_text, "message", regex, intermediate=intermediate)

    def assert_progress(self, expected_text, regex=False):
        """Check the 'progress' method was properly used."""
        return self._check(expected_text, "progress", regex)

    def assert_trace(self, expected_text, regex=False):
        """Check the 'trace' method was properly used."""
        return self._check(expected_text, "trace", regex)

    def assert_messages(self, texts):
        """Check the list of messages (this is helper for a common case of commands results)."""
        self.assert_interactions([call("message", text) for text in texts])

    def assert_interactions(self, expected_call_list):
        """Check that the expected call list happen at some point between all stored calls.

        If None is passed, asserts that no message was emitted.
        """
        if expected_call_list is None:
            if self.interactions:
                raise AssertionError(f"Expected no call but really got {self.interactions}")
            return

        for pos, stored_call in enumerate(self.interactions):
            if stored_call == expected_call_list[0]:
                break
        else:
            raise AssertionError(f"Initial expected call not found in {self.interactions}")

        stored = self.interactions[pos : pos + len(expected_call_list)]
        assert stored == expected_call_list


@pytest.fixture(autouse=True)
def init_emitter():
    """Ensure emit is always clean, and initted (in test mode).

    Note that the `init` is done in the current instance that all modules already
    acquired.
    """
    # init with a custom log filepath so user directories are not involved here; note that
    # we're not using pytest's standard tmp_path as Emitter would write logs there, and in
    # effect we would be polluting that temporary directory (potentially messing with
    # tests, that may need that empty), so we use another one.
    temp_fd, temp_logfile = tempfile.mkstemp(prefix="emitter-logs")
    os.close(temp_fd)
    temp_logfile = pathlib.Path(temp_logfile)

    messages.TESTMODE = True
    messages.emit.init(
        messages.EmitterMode.QUIET, "test-emitter", "Hello world", log_filepath=temp_logfile
    )
    yield
    # end machinery (just in case it was not ended before; note it's ok to "double end")
    messages.emit.ended_ok()
    temp_logfile.unlink()


class RecordingProgresser:
    def __init__(self, recording_emitter):
        self.recording_emitter = recording_emitter

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False  # do not consume any exception

    def advance(self, *a, **k):
        """Record the advance usage."""
        self.recording_emitter.record("advance", a, k)


@pytest.fixture
def emitter(monkeypatch):
    """Helper to test everything that was shown using craft-cli Emitter."""
    recording_emitter = RecordingEmitter()
    for method_name in ("message", "progress", "trace"):
        monkeypatch.setattr(
            messages.emit,
            method_name,
            lambda *a, method_name=method_name, **k: recording_emitter.record(method_name, a, k),
        )

    # progress bar is special, because it also needs to return a context manager with
    # something that will record progress calls
    def fake_progress_bar(*a, **k):
        recording_emitter.record("progress_bar", a, k)
        return RecordingProgresser(recording_emitter)

    monkeypatch.setattr(messages.emit, "progress_bar", fake_progress_bar)

    return recording_emitter
