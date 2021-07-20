# Copyright 2021 Canonical Ltd.
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

import logging
import os
import pathlib
import zipfile
from argparse import Namespace

import pytest

from charmcraft import linters
from charmcraft.cmdbase import CommandError
from charmcraft.commands.analyze import AnalyzeCommand



def test_expanded_charm(config, tmp_path, monkeypatch):
    """Check that the analyze runs on the temp directory with the extracted charm."""
    # prepare a fake charm file with some specific content just to check it was used properly
    charm_file = tmp_path / "foobar.charm"
    with zipfile.ZipFile(str(charm_file), "w") as zf:  #FIXME
        zf.writestr("fake_file", b"fake content")

    # this is to flag that the fake analyzer was called (otherwise the internal
    # verifications would be "lost")
    fake_analyze_called = False

    def fake_analyze(passed_config, passed_basedir):
        """Verify that the analyzer was called with the proper content.

        As we cannot check the directory itself (is temporal), we validate by content.
        """
        nonlocal fake_analyze_called

        fake_analyze_called = True
        assert passed_config is config
        assert (passed_basedir / "fake_file").read_text() == "fake content"
        return []

    monkeypatch.setattr(linters, "analyze", fake_analyze)
    args = Namespace(filepath=charm_file)
    AnalyzeCommand("group", config).run(args)
    assert fake_analyze_called


def test_corrupt_charm(tmp_path, config):
    """There was a problem opening the indicated charm."""
    charm_file = tmp_path / "foobar.charm"
    charm_file.write_text("this is not a real zip content")

    args = Namespace(filepath=charm_file)
    with pytest.raises(CommandError) as cm:
        AnalyzeCommand("group", config).run(args)
    assert str(cm.value) == (
        "Cannot open the indicated charm file '{}': "
        "FileNotFoundError(2, 'No such file or directory')".format(charm_file))


def test_integration_linters(tmp_path):
    """Integration test with the real linters.analyze function (as other tests fake it)."""
    fixme


def test_complete_set_of_results(caplog, config, monkeypatch):
    """Show a complete basic case of results."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint-01",
            check_type=linters.CheckType.lint,
            url="url-01",
            text="text-01",
            result=linters.WARNINGS,
        ),
        linters.CheckResult(
            name="check-lint-02",
            check_type=linters.CheckType.lint,
            url="url-02",
            text="text-02",
            result=linters.OK,
        ),
        linters.CheckResult(
            name="check-lint-03",
            check_type=linters.CheckType.lint,
            url="url-03",
            text="text-03",
            result=linters.ERRORS,
        ),
        linters.CheckResult(
            name="check-attribute-04",
            check_type=linters.CheckType.attribute,
            url="url-04",
            text="text-04",
            result="check-result-04",
        ),
    ]

    args = Namespace(filepath="somepath")
    monkeypatch.setattr(linters, "analyze", lambda *a: linting_results)
    AnalyzeCommand("group", config).run(args)

    expected = [
        "Attributes:",
        "- check-attribute-04: check-result-04 (url-04)",
        "Lint Warnings:",
        "- check-lint-01: text-01 (url-01)",
        "Lint Errors:",
        "- check-lint-03: text-03 (url-03)",
        "Lint OK:",
        "- check-lint-02: no issues found (url-02)",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_only_attributes(caplog, config, monkeypatch):
    """Show only attribute results (the rest may be ignored)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-attribute",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="check-result",
        ),
    ]

    args = Namespace(filepath="somepath")
    monkeypatch.setattr(linters, "analyze", lambda *a: linting_results)
    AnalyzeCommand("group", config).run(args)

    expected = [
        "Attributes:",
        "- check-attribute: check-result (url)",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_attributes_ignored(caplog, config, monkeypatch):
    """Show an attribute that is ignored in the config."""
    fixme
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-attribute",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result=linters.IGNORED,
        ),
    ]

    args = Namespace(filepath="somepath")
    monkeypatch.setattr(linters, "analyze", lambda *a: linting_results)
    AnalyzeCommand("group", config).run(args)

    expected = [
        "Attributes:",
        "- check-attribute: ignored (url)",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_only_warnings(caplog, config, monkeypatch):
    """Show only warning results (the rest may be ignored)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.lint,
            url="url",
            text="text",
            result=linters.WARNINGS,
        ),
    ]

    args = Namespace(filepath="somepath")
    monkeypatch.setattr(linters, "analyze", lambda *a: linting_results)
    AnalyzeCommand("group", config).run(args)

    expected = [
        "Lint Warnings:",
        "- check-lint: text (url)",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_only_errors(caplog, config, monkeypatch):
    """Show only error results (the rest may be ignored)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.lint,
            url="url",
            text="text",
            result=linters.ERRORS,
        ),
    ]

    args = Namespace(filepath="somepath")
    monkeypatch.setattr(linters, "analyze", lambda *a: linting_results)
    AnalyzeCommand("group", config).run(args)

    expected = [
        "Lint Errors:",
        "- check-lint: text (url)",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_only_lint_ok(caplog, config, monkeypatch):
    """Show only lint results that are ok(the rest may be ignored)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-lint",
            check_type=linters.CheckType.lint,
            url="url",
            text="text",
            result=linters.OK,
        ),
    ]

    args = Namespace(filepath="somepath")
    monkeypatch.setattr(linters, "analyze", lambda *a: linting_results)
    AnalyzeCommand("group", config).run(args)

    expected = [
        "Lint OK:",
        "- check-lint: no issues found (url)",
    ]
    assert expected == [rec.message for rec in caplog.records]
