# Copyright 2021-2022 Canonical Ltd.
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

import json
import sys
import zipfile
from argparse import ArgumentParser, Namespace

import pytest
from craft_cli import CraftError

from charmcraft import linters
from charmcraft.application.commands.analyse import Analyse
from charmcraft.cmdbase import JSON_FORMAT
from charmcraft.models.lint import LintResult


def test_options_format_possible_values(config):
    """The format option implies a set of validations."""
    cmd = Analyse(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    (action,) = (action for action in parser._actions if action.dest == "format")
    assert action.choices == ["json"]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize("modebits", [0o777, 0o750, 0o444])
def test_expanded_charm_permissions(config, fake_project_dir, monkeypatch, modebits):
    """Check that the expanded charm keeps original permissions."""
    # prepare a fake charm file with some specific content just to check it was used properly
    charm_file = fake_project_dir / "foobar.charm"
    payload_file = fake_project_dir / "payload.txt"
    payload_file.write_bytes(b"123")
    payload_file.chmod(modebits)
    with zipfile.ZipFile(str(charm_file), "w") as zf:
        zf.write(str(payload_file), payload_file.name)

    args = Namespace(filepath=charm_file, force=None, format=None, ignore=None)
    Analyse(config).run(args)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_corrupt_charm(fake_project_dir, config):
    """There was a problem opening the indicated charm."""
    charm_file = fake_project_dir / "foobar.charm"
    charm_file.write_text("this is not a real zip content")

    args = Namespace(filepath=charm_file, force=None, format=None, ignore=None)
    with pytest.raises(CraftError) as cm:
        Analyse(config).run(args)
    assert str(cm.value) == (f"Cannot open charm file '{charm_file}': File is not a zip file")


def create_a_valid_zip(tmp_path):
    """Prepare a simple zip file."""
    zip_file = tmp_path / "foobar.charm"
    with zipfile.ZipFile(str(zip_file), "w") as zf:
        zf.writestr("fake_file", b"fake content")
    return zip_file


def test_integration_linters(fake_project_dir, emitter, config, monkeypatch):
    """Integration test with a real analysis."""
    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    Analyse(config).run(args)

    emitter.assert_progress(
        "language: Charm language unknown (https://juju.is/docs/sdk/charmcraft-analyzers-and-linters#heading--language)",
        permanent=True,
    )


@pytest.mark.parametrize("indicated_format", [None, JSON_FORMAT])
def test_complete_set_of_results(
    check, emitter, service_factory, config, monkeypatch, fake_project_dir, indicated_format
):
    """Show a complete basic case of results."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint-01",
            check_type=linters.CheckType.LINT,
            url="url-01",
            text="text-01",
            result=LintResult.WARNING,
        ),
        linters.CheckResult(
            name="check-lint-02",
            check_type=linters.CheckType.LINT,
            url="url-02",
            text="text-02",
            result=LintResult.OK,
        ),
        linters.CheckResult(
            name="check-lint-03",
            check_type=linters.CheckType.LINT,
            url="url-03",
            text="text-03",
            result=LintResult.ERROR,
        ),
        linters.CheckResult(
            name="check-attribute-04",
            check_type=linters.CheckType.ATTRIBUTE,
            url="url-04",
            text="text-04",
            result="check-result-04",
        ),
        linters.CheckResult(
            name="check-attribute-05",
            check_type=linters.CheckType.ATTRIBUTE,
            url="url-05",
            text="text-05",
            result=LintResult.IGNORED,
        ),
        linters.CheckResult(
            name="check-lint-06",
            check_type=linters.CheckType.LINT,
            url="url-06",
            text="text-06",
            result=LintResult.IGNORED,
        ),
        linters.CheckResult(
            name="check-lint-07",
            check_type=linters.CheckType.LINT,
            url="url-07",
            text="text-07",
            result=LintResult.FATAL,
        ),
    ]

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=indicated_format, ignore=None)
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )
    Analyse(config).run(args)

    if indicated_format is None:
        expected = [
            "check-lint-01: [WARNING] text-01 (url-01)",
            "check-lint-02: [OK] text-02 (url-02)",
            "check-lint-03: [ERROR] text-03 (url-03)",
            "check-attribute-04: [CHECK-RESULT-04] text-04 (url-04)",
            "check-attribute-05: (url-05) ",
            "check-lint-06: (url-06) ",
            "check-lint-07: [FATAL] text-07 (url-07)",
        ]
        for line in expected:
            with check:
                emitter.assert_progress(line, permanent=True)
    else:
        expected = [
            {
                "check_type": "lint",
                "name": "check-lint-01",
                "result": "warning",
                "text": "text-01",
                "url": "url-01",
            },
            {
                "check_type": "lint",
                "name": "check-lint-02",
                "result": "ok",
                "text": "text-02",
                "url": "url-02",
            },
            {
                "check_type": "lint",
                "name": "check-lint-03",
                "result": "error",
                "text": "text-03",
                "url": "url-03",
            },
            {
                "check_type": "attribute",
                "name": "check-attribute-04",
                "result": "check-result-04",
                "text": "text-04",
                "url": "url-04",
            },
            {
                "check_type": "attribute",
                "name": "check-attribute-05",
                "result": "ignored",
                "text": "text-05",
                "url": "url-05",
            },
            {
                "check_type": "lint",
                "name": "check-lint-06",
                "result": "ignored",
                "text": "text-06",
                "url": "url-06",
            },
            {
                "check_type": "lint",
                "name": "check-lint-07",
                "result": "fatal",
                "text": "text-07",
                "url": "url-07",
            },
        ]
        text = emitter.assert_message(r"\[.*\]", regex=True)
        assert expected == json.loads(text)


def test_only_attributes(emitter, service_factory, config, monkeypatch, fake_project_dir):
    """Show only attribute results (the rest may be ignored)."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-attribute",
            check_type=linters.CheckType.ATTRIBUTE,
            url="url",
            text="text",
            result="check-result",
        ),
    ]

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )
    retcode = Analyse(config).run(args)

    emitter.assert_progress("check-attribute: [CHECK-RESULT] text (url)", permanent=True)
    assert retcode == 0


def test_only_warnings(emitter, service_factory, config, monkeypatch, fake_project_dir):
    """Show only warning results (the rest may be ignored)."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.LINT,
            url="url",
            text="text",
            result=LintResult.WARNING,
        ),
    ]

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )
    retcode = Analyse(config).run(args)

    emitter.assert_progress("check-lint: [WARNING] text (url)", permanent=True)
    assert retcode == 3


def test_only_errors(emitter, service_factory, config, monkeypatch, fake_project_dir):
    """Show only error results (the rest may be ignored)."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.LINT,
            url="url",
            text="text",
            result=LintResult.ERROR,
        ),
    ]

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )
    retcode = Analyse(config).run(args)

    emitter.assert_progress("check-lint: [ERROR] text (url)", permanent=True)
    assert retcode == 2


def test_both_errors_and_warnings(emitter, service_factory, config, monkeypatch, fake_project_dir):
    """Show error and warnings results."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint-1",
            check_type=linters.CheckType.LINT,
            url="url-1",
            text="text-1",
            result=LintResult.ERROR,
        ),
        linters.CheckResult(
            name="check-lint-2",
            check_type=linters.CheckType.LINT,
            url="url-2",
            text="text-2",
            result=LintResult.WARNING,
        ),
    ]

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )
    retcode = Analyse(config).run(args)

    emitter.assert_progress("check-lint-1: [ERROR] text-1 (url-1)", permanent=True)
    emitter.assert_progress("check-lint-2: [WARNING] text-2 (url-2)", permanent=True)
    assert retcode == 2


def test_only_lint_ok(emitter, service_factory, config, monkeypatch, fake_project_dir):
    """Show only lint results that are ok (the rest may be ignored)."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.LINT,
            url="url",
            text="text",
            result=LintResult.OK,
        ),
    ]

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )
    retcode = Analyse(config).run(args)

    emitter.assert_progress("check-lint: [OK] text (url)", permanent=True)
    assert retcode == 0


def test_only_fatal(emitter, service_factory, config, monkeypatch, fake_project_dir):
    """Show only fatal lint results (the rest may be ignored)."""
    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.LINT,
            url="url",
            text="text",
            result=LintResult.FATAL,
        ),
    ]
    monkeypatch.setattr(
        service_factory.analysis, "lint_directory", lambda *a, **k: linting_results
    )

    fake_charm = create_a_valid_zip(fake_project_dir)
    args = Namespace(filepath=fake_charm, force=None, format=None, ignore=None)
    retcode = Analyse(config).run(args)

    emitter.assert_progress("check-lint: [FATAL] text (url)", permanent=True)
    assert retcode == 1
