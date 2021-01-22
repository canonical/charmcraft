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

import os
import subprocess
import sys
from argparse import Namespace

import pytest
import yaml

from charmcraft.cmdbase import CommandError
from charmcraft.commands.init import InitCommand
from charmcraft.utils import S_IXALL
from tests.test_infra import pep8_test, get_python_filepaths, pep257_test


def test_init_pep257(tmp_path, config):
    cmd = InitCommand('group', config)
    cmd.run(Namespace(name='my-charm', author='J Doe', series='k8s', force=False))
    paths = get_python_filepaths(roots=[str(tmp_path / "src")], python_paths=[])
    pep257_test(paths)


def test_init_pep8(tmp_path, config, *, author="J Doe"):
    cmd = InitCommand('group', config)
    cmd.run(Namespace(name='my-charm', author=author, series='k8s', force=False))
    paths = get_python_filepaths(
        roots=[str(tmp_path / "src"), str(tmp_path / "tests")],
        python_paths=[])
    pep8_test(paths)


def test_init_non_ascii_author(tmp_path, config):
    test_init_pep8(tmp_path, config, author="فلانة الفلانية")


def test_all_the_files(tmp_path, config):
    cmd = InitCommand('group', config)
    cmd.run(Namespace(name='my-charm', author="ಅಪರಿಚಿತ ವ್ಯಕ್ತಿ", series='k8s', force=False))
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


def test_force(tmp_path, config):
    cmd = InitCommand('group', config)
    tmp_file = tmp_path / 'README.md'
    with tmp_file.open('w') as f:
        f.write('This is a nonsense readme')
    cmd.run(Namespace(name='my-charm', author="ಅಪರಿಚಿತ ವ್ಯಕ್ತಿ", series='k8s', force=True))

    # Check that init ran
    assert (tmp_path / 'LICENSE').exists()

    # Check that init did not overwrite files
    with tmp_file.open('r') as f:
        assert f.read() == 'This is a nonsense readme'


def test_bad_name(config):
    cmd = InitCommand('group', config)
    with pytest.raises(CommandError):
        cmd.run(Namespace(name='1234', author="שראלה ישראל", series='k8s', force=False))


def test_executables(tmp_path, config):
    cmd = InitCommand('group', config)
    cmd.run(Namespace(name='my-charm', author="홍길동", series='k8s', force=False))
    assert (tmp_path / "run_tests").stat().st_mode & S_IXALL == S_IXALL
    assert (tmp_path / "src/charm.py").stat().st_mode & S_IXALL == S_IXALL


def uncomment(filepath, token):
    """Uncomment a file after and including the line with the given token."""
    new_content = []
    with filepath.open('rt', encoding='utf8') as fh:
        comment = None
        for line in fh:
            if token in line:
                comment = line.index(token)
            if comment is not None:
                line = line[comment:]
            new_content.append(line)
    with filepath.open('wt', encoding='utf8') as fh:
        fh.writelines(new_content)


def test_tests(tmp_path, config):
    # fix the PYTHONPATH and PATH so the tests in the initted environment use our own
    # virtualenv libs and bins (if any), as they need them, but we're not creating a
    # venv for the local tests (note that for CI doesn't use a venv)
    env = os.environ.copy()
    env_paths = [p for p in sys.path if 'env/lib/python' in p]
    if env_paths:
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] += ':' + ':'.join(env_paths)
        else:
            env['PYTHONPATH'] = ':'.join(env_paths)
        for path in env_paths:
            bin_path = path[:path.index('env/lib/python')] + 'env/bin'
            env['PATH'] = bin_path + ':' + env['PATH']

    cmd = InitCommand('group', config)
    cmd.run(Namespace(name='my-charm', author="だれだれ", series='k8s', force=False))

    # uncomment the project YAMLs that we just created from the templates, so tests run ok
    # (those files are commented out to avoid the developer pushing valid-but-fake config
    # and actions files to the Store)
    uncomment(tmp_path / 'actions.yaml', "fortune:")
    uncomment(tmp_path / 'config.yaml', "options:")

    subprocess.run(["./run_tests"], cwd=str(tmp_path), check=True, env=env)


def test_series_defaults(tmp_path, config):
    cmd = InitCommand('group', config)
    # series default comes from the parsing itself
    cmd.run(Namespace(name='my-charm', author="fred", series='k8s', force=False))

    with (tmp_path / "metadata.yaml").open("rt", encoding="utf8") as f:
        metadata = yaml.safe_load(f)
    assert metadata.get("series") == ['k8s']


def test_manual_overrides_defaults(tmp_path, config):
    cmd = InitCommand('group', config)
    cmd.run(Namespace(name='my-charm', author="fred", series='xenial,precise', force=False))

    with (tmp_path / "metadata.yaml").open("rt", encoding="utf8") as f:
        metadata = yaml.safe_load(f)
    assert metadata.get("series") == ['xenial', 'precise']
