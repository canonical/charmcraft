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

import logging
import os
from unittest.mock import patch

from charmcraft.logsetup import _MessageHandler
from charmcraft.cmdbase import CommandError

import pytest


@pytest.fixture
def create_message_handler(tmp_path):
    """Helper to create a message handler.

    Always in a temp directory, maybe with patched modes.
    """
    temp_log_file = tmp_path / 'test.log'
    patchers = []

    def factory(modes=None):
        p = patch('tempfile.mkstemp', lambda prefix: ('fd', str(temp_log_file)))
        p.start()
        patchers.append(p)

        if modes is not None:
            if 'verbose' not in modes:
                # verbose should always be there, as it's used internally
                modes['verbose'] = (10, "%(message)s")
            p = patch.object(_MessageHandler, '_modes', modes)
            p.start()
            patchers.append(p)

        return _MessageHandler()

    yield factory

    # cleanup
    for p in patchers:
        p.stop()


# --- Tests for the MessageHandler

def test_mode_setting_init(create_message_handler):
    """The internal mode is set on init and logger properly changed."""
    test_level = 123
    test_format = "test:: %(message)s"
    mh = create_message_handler({'foo': (test_level, test_format)})
    mh.init(mh.FOO)

    assert mh.mode == mh.FOO
    assert mh._stderr_handler.formatter._fmt == test_format
    assert mh._stderr_handler.level == test_level


def test_mode_setting_changed(create_message_handler):
    """The internal mode can be set later and logger properly changed."""
    test_level = 123
    test_format = "test:: %(message)s"
    mh = create_message_handler({'foo': (0, ''), 'bar': (test_level, test_format)})
    mh.init(mh.FOO)
    mh.set_mode(mh.BAR)

    assert mh.mode == mh.BAR
    assert mh._stderr_handler.formatter._fmt == test_format
    assert mh._stderr_handler.level == test_level


def test_logfile_all_stored(create_message_handler):
    """All logging levels are dumped to the logfile."""
    mh = create_message_handler()
    mh.init(mh.NORMAL)

    logger = logging.getLogger("charmcraft.test")
    logger.debug("test debug")
    logger.info("test info")
    logger.warning("test warning")
    logger.error("test error")

    with open(mh._log_filepath, 'rt') as fh:
        logcontent = fh.readlines()

    # start checking from pos 1, as in 0 we always have the bootstrap message
    assert 'test debug' in logcontent[1]
    assert 'test info' in logcontent[2]
    assert 'test warning' in logcontent[3]
    assert 'test error' in logcontent[4]


def test_ended_success(caplog, create_message_handler):
    """Reports nothing, removes log file."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    mh = create_message_handler()
    mh.init(mh.NORMAL)
    mh.ended_ok()

    # file is removed, no particular message emitted
    assert not os.path.exists(mh._log_filepath)
    assert not caplog.records


def test_ended_interrupt(caplog, create_message_handler):
    """Reports ^C, removes log file."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    mh = create_message_handler()
    mh.init(mh.NORMAL)
    mh.ended_interrupt()

    # file is removed, no particular message emitted
    assert not os.path.exists(mh._log_filepath)
    # a single None for exc_info means no traceback would be printed
    assert ("ERROR", "Interrupted.", None) in [
        (rec.levelname, rec.message, rec.exc_info) for rec in caplog.records
    ]


def test_ended_verbose_interrupt(caplog, create_message_handler):
    """Reports ^C, including traceback, removes log file."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    mh = create_message_handler()
    mh.init(mh.VERBOSE)
    mh.ended_interrupt()

    # file is removed, no particular message emitted
    assert not os.path.exists(mh._log_filepath)
    # the (None, None, None) here indicates that it'd be printing a traceback
    assert ("ERROR", "Interrupted.", (None, None, None)) in [
        (rec.levelname, rec.message, rec.exc_info) for rec in caplog.records
    ]


def test_ended_commanderror_regular(caplog, create_message_handler):
    """Reports just the message, including the log file (not removed)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    mh = create_message_handler()
    mh.init(mh.NORMAL)
    mh.ended_cmderror(CommandError("test controlled error"))

    expected_msg = "test controlled error (full execution logs in {})".format(mh._log_filepath)

    # file is present, and it has the error
    with open(mh._log_filepath, 'rt', encoding='ascii') as fh:
        log_content = fh.read()
    assert 'ERROR' in log_content
    assert expected_msg in log_content

    # also it shown the error to the user
    assert [expected_msg] == [rec.message for rec in caplog.records]


def test_ended_commanderror_argparsing(capsys, create_message_handler):
    """Reports just the message to stdout."""
    mh = create_message_handler()
    mh.init(mh.NORMAL)
    mh.ended_cmderror(CommandError("test controlled error", argsparsing=True))
    captured = capsys.readouterr()
    assert captured.out == "test controlled error\n"


def test_ended_crash_while_normal(caplog, create_message_handler):
    """Reports the internal crash, including the log file (not removed)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    mh = create_message_handler()
    mh.init(mh.NORMAL)
    try:
        raise ValueError("crazy crash")
    except Exception as err:
        mh.ended_crash(err)  # needs to have an exception "active"

    expected_msg = (
        "charmcraft internal error! ValueError: crazy crash (full execution logs in {})".format(
            mh._log_filepath))

    # file is present, and it has the error and the traceback
    with open(mh._log_filepath, 'rt', encoding='ascii') as fh:
        log_content = fh.read()
    assert 'ERROR' in log_content
    assert expected_msg in log_content
    assert 'Traceback' in log_content

    # also it shown ONLY the error to the user
    (record,) = caplog.records
    assert record.message == expected_msg
    assert record.exc_info is None


def test_ended_crash_while_verbose(caplog, create_message_handler):
    """Reports the internal crash, including the log file (not removed)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    mh = create_message_handler()
    mh.init(mh.VERBOSE)
    try:
        raise ValueError("crazy crash")
    except Exception as err:
        mh.ended_crash(err)  # needs to have an exception "active"

    expected_msg = (
        "charmcraft internal error! ValueError: crazy crash (full execution logs in {})".format(
            mh._log_filepath))

    # file is present, and it has the error and the traceback
    with open(mh._log_filepath, 'rt', encoding='ascii') as fh:
        log_content = fh.read()
    assert 'ERROR' in log_content
    assert expected_msg in log_content
    assert 'Traceback' in log_content

    # also it shown the error to the user AND also the traceback
    (_, record) = caplog.records
    assert record.message == expected_msg
    assert record.exc_info[0] == ValueError
