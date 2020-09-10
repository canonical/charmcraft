# Copyright 2020 Canonical Ltd.
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

import os
import subprocess
import sys
from argparse import Namespace

import pytest
import yaml

from charmcraft.cmdbase import CommandError
from charmcraft.commands.init import InitCommand
from charmcraft.commands.utils import S_IXALL
from tests.test_infra import pep8_test, get_python_filepaths


def test_init_pep8(tmp_path, *, author="J Doe"):
    cmd = InitCommand('group')
    cmd.run(Namespace(path=tmp_path, name='my-charm', author=author, series='k8s'))
    paths = get_python_filepaths(
        roots=[str(tmp_path / "src"), str(tmp_path / "tests")],
        python_paths=[])
    pep8_test(paths)


def test_init_non_ascii_author(tmp_path):
    test_init_pep8(tmp_path, author="فلانة الفلانية")


def test_all_the_files(tmp_path):
    cmd = InitCommand('group')
    cmd.run(Namespace(path=tmp_path, name='my-charm', author="ಅಪರಿಚಿತ ವ್ಯಕ್ತಿ", series='k8s'))
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.glob("**/*")) == [
        ".flake8",
        ".jujuignore",
        "LICENSE",
        "README.md",
        "actions.yaml",
        "config.yaml",
        "metadata.yaml",
        "requirements-dev.txt",
        "requirements.txt",
        "run_tests",
        "src",
        "src/charm.py",
        "tests",
        "tests/__init__.py",
        "tests/test_charm.py",
    ]


def test_bad_name(tmp_path):
    cmd = InitCommand('group')
    with pytest.raises(CommandError):
        cmd.run(Namespace(path=tmp_path, name='1234', author="שראלה ישראל", series='k8s'))


def test_executables(tmp_path):
    cmd = InitCommand('group')
    cmd.run(Namespace(path=tmp_path, name='my-charm', author="홍길동", series='k8s'))
    assert (tmp_path / "run_tests").stat().st_mode & S_IXALL == S_IXALL
    assert (tmp_path / "src/charm.py").stat().st_mode & S_IXALL == S_IXALL


def test_tests(tmp_path):
    # fix the PYTHONPATH so the tests in the initted environment use our own
    # virtualenv (if any), as they need one, but we're not creating one for them; note
    # that for CI this normally doesn't run under a venv, so this may fix nothing
    env = os.environ.copy()
    env_paths = [p for p in sys.path if 'env/lib/python' in p]
    if env_paths:
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] += ':' + ':'.join(env_paths)
        else:
            env['PYTHONPATH'] = ':'.join(env_paths)

    cmd = InitCommand('group')
    cmd.run(Namespace(path=tmp_path, name='my-charm', author="だれだれ", series='k8s'))
    subprocess.run(["./run_tests"], cwd=str(tmp_path), check=True, env=env)


def test_series_defaults(tmp_path):
    cmd = InitCommand('group')
    # series default comes from the parsing itself
    cmd.run(Namespace(path=tmp_path, name='my-charm', author="fred", series='k8s'))

    with (tmp_path / "metadata.yaml").open("rt", encoding="utf8") as f:
        metadata = yaml.safe_load(f)
    assert metadata.get("series") == ['k8s']


def test_manual_overrides_defaults(tmp_path):
    cmd = InitCommand('group')
    cmd.run(Namespace(path=tmp_path, name='my-charm', author="fred", series='xenial,precise'))

    with (tmp_path / "metadata.yaml").open("rt", encoding="utf8") as f:
        metadata = yaml.safe_load(f)
    assert metadata.get("series") == ['xenial', 'precise']
