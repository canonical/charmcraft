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

import pathlib
import tempfile

import pytest

from charmcraft import config as config_module


@pytest.fixture(autouse=True, scope="session")
def tmpdir_under_tmpdir(tmpdir_factory):
    tempfile.tempdir = str(tmpdir_factory.getbasetemp())


@pytest.fixture
def tmp_path(tmp_path):
    """Always present a pathlib's Path.

    This is to avoid pytest using pythonlib2 in Python 3.5, which leads
    to several slight differences in the tests.

    This "middle layer fixture" has the same name of the pytest's fixture,
    so when we drop Py 3.5 support we will be able to just remove this,
    and all the tests automatically will use the standard one (no further
    changes needed).
    """
    return pathlib.Path(str(tmp_path))


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
            if name == 'chdir':
                return object.__getattribute__(self, '_chdir')
            else:
                return getattr(monkeypatch, name)

    return Monkeypatcher()


@pytest.fixture
def config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(config_module.Config):
        """The Config, but with a method to set test values."""

        def set(self, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            prime = kwargs.pop('prime', None)
            if prime is not None:
                kwargs['parts'] = config_module.BasicPrime.from_dict({
                    'bundle': {
                        'prime': prime,
                    }
                })

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    return TestConfig(type='bundle', project=config_module.Project(dirpath=tmp_path))
