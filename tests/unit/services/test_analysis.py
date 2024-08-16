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
"""Unit tests for analysis service."""
import pathlib
import tempfile
import zipfile
from unittest import mock

import pytest
import pytest_check

from charmcraft import application, linters
from charmcraft.models.lint import CheckResult, CheckType, LintResult
from charmcraft.services import analysis


class StubAttributeChecker(linters.AttributeChecker):
    def __init__(self, name, url, text, result):
        self.name = name
        self.url = url
        self.text = text
        self.result = result

    def __call__(self):
        return self

    def run(self, basedir: pathlib.Path) -> str:
        return self.result


class StubLinter(linters.Linter):
    def __init__(self, name, result):
        self.name = name
        self.url = f"http://example.org/{name}"
        self.text = f"returns {name}"
        self.result = result

    def __call__(self):
        return self

    def run(self, basedir: pathlib.Path) -> str:
        return self.result


STUB_ATTRIBUTE_CHECKERS = [
    StubAttributeChecker(
        "unknown_attribute", "https://example.com/unknown", "returns unknown", LintResult.UNKNOWN
    ),
    StubAttributeChecker("says_python", "https://python.org", "returns python", "python"),
]
STUB_CHECKER_RESULTS = [
    CheckResult(linter.name, linter.result, linter.url, CheckType.ATTRIBUTE, linter.text)
    for linter in STUB_ATTRIBUTE_CHECKERS
]
ATTRIBUTE_CHECKER_NAMES = frozenset(checker.name for checker in STUB_ATTRIBUTE_CHECKERS)
STUB_LINTERS = [
    StubLinter("success", LintResult.OK),
    StubLinter("warn", LintResult.WARNING),
    StubLinter("error", LintResult.ERROR),
    StubLinter("fatal", LintResult.FATAL),
    StubLinter("ignore", LintResult.IGNORED),
    StubLinter("???", LintResult.UNKNOWN),
    StubLinter("N/A", LintResult.NONAPPLICABLE),
]
STUB_LINTER_RESULTS = [
    CheckResult(linter.name, linter.result, linter.url, CheckType.LINT, linter.text)
    for linter in STUB_LINTERS
]
LINTER_NAMES = frozenset(linter.name for linter in STUB_LINTERS)
ALL_CHECKER_NAMES = ATTRIBUTE_CHECKER_NAMES | LINTER_NAMES


@pytest.fixture
def mock_temp_dir(monkeypatch):
    mock_obj = mock.MagicMock(spec=tempfile.TemporaryDirectory)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", mock.Mock(return_value=mock_obj))
    return mock_obj


@pytest.fixture
def mock_zip_file(monkeypatch):
    mock_obj = mock.MagicMock(spec=zipfile.ZipFile)
    monkeypatch.setattr(zipfile, "ZipFile", mock.Mock(return_value=mock_obj))
    return mock_obj


@pytest.fixture
def analysis_service():
    return analysis.AnalysisService(app=application.APP_METADATA, services=None)


@pytest.mark.parametrize(
    ("checkers", "expected"),
    [(STUB_ATTRIBUTE_CHECKERS, STUB_CHECKER_RESULTS), (STUB_LINTERS, STUB_LINTER_RESULTS)],
)
def test_lint_directory_results(monkeypatch, analysis_service, checkers, expected):
    monkeypatch.setattr(linters, "CHECKERS", checkers)

    assert list(analysis_service.lint_directory(pathlib.Path())) == expected


@pytest.mark.parametrize("checkers", [STUB_ATTRIBUTE_CHECKERS + STUB_LINTERS])
@pytest.mark.parametrize(
    "ignore", [set(), {"success"}, ATTRIBUTE_CHECKER_NAMES, LINTER_NAMES, ALL_CHECKER_NAMES]
)
def test_lint_directory_ignores(monkeypatch, analysis_service, checkers, ignore):
    monkeypatch.setattr(linters, "CHECKERS", checkers)
    checker_names = {checker.name for checker in checkers}

    results = list(
        analysis_service.lint_directory(pathlib.Path(), ignore=ignore, include_ignored=False)
    )
    checkers_run = {r.name for r in results}

    pytest_check.is_true(checkers_run.isdisjoint(ignore), f"{checkers_run & ignore}")
    pytest_check.is_true(checkers_run.issubset(checker_names), str(checkers_run - checker_names))


def test_lint_file_results(fs, mock_temp_dir, mock_zip_file, monkeypatch, analysis_service):
    fake_charm = pathlib.Path("/fake/charm.charm")
    fs.create_file(fake_charm)
    mock_checker = mock.Mock()
    monkeypatch.setattr(linters, "CHECKERS", [mock.Mock(return_value=mock_checker)])
    fake_temp_path = pathlib.Path(mock_temp_dir.__enter__.return_value)

    results = list(analysis_service.lint_file(fake_charm))

    with pytest_check.check:
        mock_zip_file.__enter__.return_value.extractall.assert_called_once_with(fake_temp_path)
    with pytest_check.check:
        mock_checker.get_result.assert_called_once_with(fake_temp_path)
    pytest_check.equal(results, [mock_checker.get_result.return_value])
