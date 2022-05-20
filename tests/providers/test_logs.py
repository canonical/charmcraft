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

import pathlib
from unittest import mock

import pytest

from charmcraft import providers


@pytest.fixture()
def mock_namedtemporaryfile(tmp_path):
    with mock.patch(
        "charmcraft.providers._logs.tempfile.NamedTemporaryFile"
    ) as mock_namedtemporaryfile:
        mock_namedtemporaryfile.return_value.name = str(tmp_path / "fake.file")
        yield mock_namedtemporaryfile


def test_capture_logs_from_instance(emitter, mock_instance, mock_namedtemporaryfile, tmp_path):
    fake_log = pathlib.Path(mock_namedtemporaryfile.return_value.name)
    fake_log_data = "some\nlog data\nhere"
    fake_log.write_text(fake_log_data)

    providers.capture_logs_from_instance(mock_instance)

    assert mock_instance.mock_calls == [
        mock.call.pull_file(source=pathlib.Path("/tmp/charmcraft.log"), destination=fake_log),
    ]
    emitter.assert_interactions(
        [
            mock.call("trace", "Logs captured from managed instance:"),
            mock.call("trace", ":: some"),
            mock.call("trace", ":: log data"),
            mock.call("trace", ":: here"),
        ]
    )
    assert mock_namedtemporaryfile.mock_calls == [
        mock.call(delete=False, prefix="charmcraft-", suffix="-temporary.log", dir="."),
        mock.call().close(),
    ]
    assert not fake_log.exists()


def test_capture_logs_from_instance_not_found(
    emitter, mock_instance, mock_namedtemporaryfile, tmp_path
):
    fake_log = pathlib.Path(mock_namedtemporaryfile.return_value.name)
    fake_log.touch()  # temp file is created when NamedTemporaryFile called
    mock_instance.pull_file.side_effect = FileNotFoundError()

    providers.capture_logs_from_instance(mock_instance)

    assert mock_instance.mock_calls == [
        mock.call.pull_file(source=pathlib.Path("/tmp/charmcraft.log"), destination=fake_log),
    ]
    emitter.assert_trace("No logs found in instance.")
    assert not fake_log.exists()
