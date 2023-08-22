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

import re
from unittest.mock import call, patch

import pytest

from charmcraft import deprecations
from charmcraft.deprecations import _DEPRECATION_MESSAGES, notify_deprecation


def test_notice_ok(monkeypatch, emitter):
    """Present proper messages to the user."""
    monkeypatch.setitem(_DEPRECATION_MESSAGES, "dn666", "Test message for the user.")
    monkeypatch.setattr(deprecations, "_DEPRECATION_URL_FMT", "http://docs.com/#{deprecation_id}")

    notify_deprecation("dn666")
    emitter.assert_interactions(
        [
            call("progress", "DEPRECATED: Test message for the user.", permanent=True),
            call("progress", "See http://docs.com/#dn666 for more information.", permanent=True),
        ]
    )


def test_notice_skipped_in_managed_mode(monkeypatch, emitter):
    """Present proper messages to the user."""
    monkeypatch.setitem(_DEPRECATION_MESSAGES, "dn666", "Test message for the user.")
    monkeypatch.setattr(deprecations, "_DEPRECATION_URL_FMT", "http://docs.com/#{deprecation_id}")

    with patch(
        "charmcraft.deprecations.is_charmcraft_running_in_managed_mode",
        return_value=True,
    ):
        notify_deprecation("dn666")

    emitter.assert_interactions(None)


@pytest.mark.parametrize("deprecation_id", _DEPRECATION_MESSAGES.keys())
def test_check_real_deprecation_ids(deprecation_id):
    """Verify all the real IDs used have the correct form."""
    assert re.match(r"dn\d\d", deprecation_id)


@pytest.mark.parametrize("message", _DEPRECATION_MESSAGES.values())
def test_check_real_deprecation_messages(message):
    """Verify all the real messages conform some rules."""
    assert message[0].isupper()
    assert message[-1] == "."


def test_log_deprecation_only_once(monkeypatch, emitter):
    """Show the message only once even if it was called several times."""
    monkeypatch.setitem(_DEPRECATION_MESSAGES, "dn666", "Test message for the user.")
    monkeypatch.setattr(deprecations, "_DEPRECATION_URL_FMT", "http://docs.com/#{deprecation_id}")

    # call twice, log once
    notify_deprecation("dn666")
    notify_deprecation("dn666")
    emitter.assert_interactions(
        [
            call("progress", "DEPRECATED: Test message for the user.", permanent=True),
            call("progress", "See http://docs.com/#dn666 for more information.", permanent=True),
        ]
    )
