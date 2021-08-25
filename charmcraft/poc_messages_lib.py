#
# Copyright 2021 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""Support for all messages, ok or after errors, to screen and log file."""

import enum
import itertools
import logging
import math
import os
import queue
import select
import shutil
import sys
import tempfile
import time
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Union, Optional, TextIO

# seconds before putting the spinner to work
SPINNER_THRESHOLD = 2
# seconds between each spinner char
SPINNER_DELAY = 0.1

# the terminal width (in columns)
TERMINAL_WIDTH = shutil.get_terminal_size().columns
# FIXME: we should use this dinamically, to support users resizing their terminals


@dataclass
class MessageInfo:
    stream: Union[TextIO, None]
    text: str
    ephemeral: bool
    bar_progress: Union[int, float, None] = None
    bar_total: Union[int, float, None] = None
    use_timestamp: bool = False
    end_line: bool = False
    created_at: datetime = field(default_factory=datetime.now)


# the different modes the Emitter can be set
EmitterMode = enum.Enum("EmitterMode", "QUIET NORMAL VERBOSE TRACE")


class CraftError(Exception):
    """Signal a program error with a lot of information to report.

    - message: the main message to the user, to be shown as first line (and probably
      only that, according to the different modes); note that in some cases the log
      location will be attached to this message.

    - details: the full error details received from a third party which originated
      the error situation

    - resolution: an extra line indicating to the user how the erorr may be fixed or
      avoided (to be shown together with 'message')

    - docs_url: an URL to point the user to documentation (to be shown together
      with 'message')

    - reportable: if an error report should be sent to some error-handling backend (like
      Sentry)

    - retcode: the code to return when the application finishes
    """

    def __init__(
        self,
        message: str,
        *,
        details: Optional[str] = None,
        resolution: Optional[str] = None,
        docs_url: Optional[str] = None,
        reportable: bool = True,
        retcode: int = 1,
    ):
        super().__init__(message)
        self.details = details
        self.resolution = resolution
        self.docs_url = docs_url
        self.reportable = reportable
        self.retcode = retcode


class _Spinner(threading.Thread):
    def __init__(self, printer: "_Printer"):
        super().__init__()
        self.stop_flag = object()

        # deamon mode, so if the app crashes this thread does not holds everything
        self.daemon = True

        # communication from the printer
        self.queue = queue.Queue()

        # hold the printer, to make it spin
        self.printer = printer

        # a lock to wait the spinner to stop spinning
        self.lock = threading.Lock()

    def run(self) -> None:
        prv_msg = None
        t_init = time.time()
        while prv_msg is not self.stop_flag:
            try:
                new_msg = self.queue.get(timeout=SPINNER_THRESHOLD)
            except queue.Empty:
                # waited too much, start to show a spinner (if have a previous message) until
                # we have further info
                if prv_msg is None:
                    continue
                spinchars = itertools.cycle("-\\|/")
                with self.lock:
                    while True:
                        t_delta = time.time() - t_init
                        spintext = f" {next(spinchars)} ({t_delta:.1f}s)"
                        self.printer.spin(prv_msg, spintext)
                        try:
                            new_msg = self.queue.get(timeout=SPINNER_DELAY)
                        except queue.Empty:
                            # still nothing! keep going
                            continue
                        # got a new message: clean the spinner and exit from the spinning state
                        self.printer.spin(prv_msg, " ")
                        break

            prv_msg = new_msg
            t_init = time.time()

    def supervise(self, message: Optional[MessageInfo]) -> None:
        """Supervise a message to spin it if it remains too long."""
        self.queue.put(message)
        # (maybe) wait for the spinner to exit spinning state (which does some cleaning)
        self.lock.acquire()
        self.lock.release()

    def stop(self) -> None:
        """Stop self."""
        self.queue.put(self.stop_flag)
        self.join()


class _Printer:
    def __init__(self, log_filepath: str):
        # holder of the previous message
        self.prv_msg = None

        # the open log file (will be closed explicitly when the thread ends)
        self.log = open(log_filepath, "wt", encoding="utf8")

        # keep account of output streams with unfinished lines
        self.unfinished_stream = None

        # run the spinner supervisor
        self.spinner = _Spinner(self)
        self.spinner.start()

    def _write_line(self, message: MessageInfo, *, spintext: str = "") -> None:
        """Write a simple line message to the screen."""
        # prepare the text with (maybe) the timestamp
        if message.use_timestamp:
            timestamp_str = message.created_at.isoformat(sep=" ", timespec="milliseconds")
            text = timestamp_str + " " + message.text
        else:
            text = message.text

        if spintext:
            # forced to overwrite the previous message to present the spinner
            maybe_cr = "\r"
        elif self.prv_msg is None or self.prv_msg.end_line:
            # first message, or previous message completed the line: start clean
            maybe_cr = ""
        elif self.prv_msg.ephemeral:
            # the last one was ephemeral, overwrite it
            maybe_cr = "\r"
        else:
            # complete the previous line, leaving that message ok
            maybe_cr = ""
            print(flush=True, file=self.prv_msg.stream)

        # fill with spaces until the very end, on one hand to clear a possible previous message,
        # but also to always have the cursor at the very end
        usable = TERMINAL_WIDTH - len(spintext) - 1  # the 1 is the cursor itself
        if len(text) > usable:
            if message.ephemeral:
                text = text[: usable - 1] + "…"
            elif spintext:
                # we need to rewrite the message with the spintext, use only the last line for
                # multiline messages
                text = text[-(len(text) % TERMINAL_WIDTH):]
        cleaner = " " * (usable - len(text) % TERMINAL_WIDTH)

        line = maybe_cr + text + spintext + cleaner
        print(line, end="", flush=True, file=message.stream)
        if message.end_line:
            assert not message.ephemeral
            # finish the just shown line, as we need a clean terminal for some external thing
            print(flush=True, file=message.stream)
            self.unfinished_stream = None
        else:
            self.unfinished_stream = message.stream

    def _write_bar(self, message: MessageInfo) -> None:
        """Write a progress bar to the screen."""
        if self.prv_msg is None or self.prv_msg.end_line:
            # first message, or previous message completed the line: start clean
            maybe_cr = ""
        elif self.prv_msg.ephemeral:
            # the last one was ephemeral, overwrite it
            maybe_cr = "\r"
        else:
            # complete the previous line, leaving that message ok
            maybe_cr = ""
            print(flush=True, file=self.prv_msg.stream)

        numerical_progress = f"{message.bar_progress}/{message.bar_total}"
        bar_percentage = min(message.bar_progress / message.bar_total, 1)

        # terminal size minus the text and numerical progress, and 5 (the cursor at the end,
        # two spaces before and after the bar, and two surrounding brackets)
        bar_width = TERMINAL_WIDTH - len(message.text) - len(numerical_progress) - 5
        completed_width = math.floor(bar_width * min(bar_percentage, 100))
        completed_bar = "#" * completed_width
        empty_bar = " " * (bar_width - completed_width)
        line = f"{maybe_cr}{message.text} [{completed_bar}{empty_bar}] {numerical_progress}"
        print(line, end="", flush=True, file=message.stream)
        self.unfinished_stream = message.stream

    def _show(self, msg: MessageInfo) -> None:
        """Show the composed message."""
        # show the message in one way or the other only if there is a stream
        if msg.stream is None:
            return

        if msg.bar_progress is None:
            # regular message, send it to the spinner and write it
            self.spinner.supervise(msg)
            self._write_line(msg)
        else:
            # progress bar, send None to the spinner (as it's not a "spinneable" message)
            # and write it
            self.spinner.supervise(None)
            self._write_bar(msg)
        self.prv_msg = msg

    def _log(self, message: MessageInfo) -> None:
        """Write the line message to the log file."""
        # prepare the text with (maybe) the timestamp
        timestamp_str = message.created_at.isoformat(sep=" ", timespec="milliseconds")
        self.log.write(f"{timestamp_str} {message.text}\n")

    def spin(self, msg: MessageInfo, spintext: str) -> None:
        self._write_line(msg, spintext=spintext)

    def show(
        self,
        stream: Optional[TextIO],
        text: str,
        *,
        ephemeral: bool = False,
        use_timestamp: bool = False,
        end_line: bool = False,
        avoid_logging: bool = False,
    ) -> None:
        msg = MessageInfo(
            stream=stream,
            text=text.rstrip(),
            ephemeral=ephemeral,
            use_timestamp=use_timestamp,
            end_line=end_line,
        )
        self._show(msg)
        if not avoid_logging:
            self._log(msg)

    def progress_bar(
        self,
        stream: Optional[TextIO],
        text: str,
        progress: Union[int, float],
        total: Union[int, float],
    ) -> None:
        msg = MessageInfo(
            stream=stream,
            text=text.rstrip(),
            ephemeral=True,
            bar_progress=progress,
            bar_total=total
        )
        self._show(msg)

    def stop(self) -> None:
        """Stop the printing infrastructure.

        In detail:
        - stop the spinner
        - add a new line to the screen (if needed)
        - close the log file
        """
        self.spinner.stop()
        if self.unfinished_stream is not None:
            print(flush=True, file=self.unfinished_stream)
        self.log.close()


class _Progresser:
    def __init__(
            self, printer: _Printer,
            total: Union[int, float],
            text: str,
            stream: TextIO,
            delta: bool):
        self.printer = printer
        self.total = total
        self.text = text
        self.accumulated = 0
        self.stream = stream
        self.delta = delta

    def __enter__(self) -> "_Progresser":
        return self

    def __exit__(self, *exc_info) -> bool:
        return False  # do not consume any exception

    def advance(self, amount: Union[int, float]) -> None:
        if self.delta:
            self.accumulated += amount
        else:
            self.accumulated = amount
        self.printer.progress_bar(self.stream, self.text, self.accumulated, self.total)


class _PipeReadingThread(threading.Thread):
    def __init__(self, pipe: int, printer: _Printer, stream: TextIO):
        super().__init__()
        self.read_pipe = pipe
        self.quit_flag = False
        self.remaining_content = b""
        self.printer = printer
        self.stream = stream

    def _write(self, data: bytes, force: bool = False) -> None:
        """Write data in intended outputs, converting byte streams to unicode lines."""
        pointer = 0
        data = self.remaining_content + data
        while True:
            # get the position of next newline (find starts in pointer position)
            newline_position = data.find(b"\n", pointer)

            # no more newlines, store the rest of data for the next time and break
            if newline_position == -1:
                self.remaining_content = data[pointer:]
                break

            # get the useful line andd update pointer for next cycle (plus one, to
            # skip the new line itself)
            useful_line = data[pointer:newline_position]
            pointer = newline_position + 1

            # write the useful line to intended outputs
            useful_line = useful_line.decode("utf8")
            text = f":: {useful_line}"
            self.printer.show(self.stream, text, end_line=True, use_timestamp=True)

    def run(self) -> None:
        while True:
            rlist, _, _ = select.select([self.read_pipe], [], [], 0.1)
            if rlist:
                data = os.read(self.read_pipe, 4096)
                self._write(data)
            elif self.quit_flag:
                # only quit when nothing left to read
                break

    def stop(self) -> None:
        """Stop the thread.

        This flag ourselves to quit, but then makes the main thread (which is the one calling
        this method) to wait ourselves to finish.
        """
        self.quit_flag = True
        self.join()


class _StreamContextManager:
    def __init__(self, printer: _Printer, text: str, stream: TextIO):
        # open a pipe; subprocess will write in it, we will read from the other end
        pipe_r, self.pipe_w = os.pipe()

        # show the intended text (explictly asking for a complete line) before passing the
        # output command to the pip-reading thread
        printer.show(stream, text, end_line=True, use_timestamp=True)

        # enable the thread to read and show what comes through the pipe
        self.pipe_reader = _PipeReadingThread(pipe_r, printer, stream)

    def __enter__(self):
        self.pipe_reader.start()
        return self.pipe_w

    def __exit__(self, *exc_info):
        self.pipe_reader.stop()
        return False  # do not consume any exception


class _Handler(logging.Handler):
    """A logging handler that emit the messages through the core Printer."""

    # a table to map which logging messages show to the screen according to the selected mode
    mode_to_log_map = {
        EmitterMode.QUIET: logging.WARNING,
        EmitterMode.NORMAL: logging.INFO,
        EmitterMode.VERBOSE: logging.DEBUG,
        EmitterMode.TRACE: logging.DEBUG,
    }

    def __init__(self, printer: _Printer):
        super().__init__()
        self.printer = printer

        # level is 0 so we get EVERYTHING (as we need to send it all to the log file), and
        # will decide on "emit" if also goes to screen using the custom mode
        self.level = 0
        self.mode = EmitterMode.QUIET

    def emit(self, record: logging.LogRecord) -> None:
        """Send the message to the printer."""
        if self.mode == EmitterMode.QUIET or self.mode == EmitterMode.NORMAL:
            use_timestamp = False
        else:
            use_timestamp = True
        threshold = self.mode_to_log_map[self.mode]
        if record.levelno >= threshold:
            stream = sys.stdout
        else:
            stream = None
        self.printer.show(stream, record.getMessage(), use_timestamp=use_timestamp)


class Emitter:
    """Main interface to all the messages emitting functionality.

    This handling everything that goes to screen and to the log file, even interfacing
    with the formal logging infrastructure to get messages from it.
    """

    def init(self, mode: EmitterMode, greeting: str):
        self.greeting = greeting

        # create a log file, bootstrap the printer, and before anything else send the greeting
        # to the file
        _, self.log_filepath = tempfile.mkstemp(prefix="charmcraft-log-")
        self.printer = _Printer(self.log_filepath)
        self.printer.show(None, greeting)
        # FIXME: manage the log files
        # - save the current one in
        #       appdirs.user_log_dir() / appname / "appname-<timestamp with microseconds>.log"
        # - rotate them!

        # hook into the logging system
        logger = logging.getLogger("")
        self._log_handler = _Handler(self.printer)
        logger.addHandler(self._log_handler)

        self.set_mode(mode)

    def set_mode(self, mode: EmitterMode) -> None:
        self.mode = mode
        self._log_handler.mode = mode

        if self.mode == EmitterMode.VERBOSE or self.mode == EmitterMode.TRACE:
            # send the greeting to the screen before any further messages
            self.printer.show(
                sys.stderr, self.greeting, use_timestamp=True, avoid_logging=True, end_line=True)
            # FIXME: also show here the log filepath

    def message(self, text: str, intermediate: bool = False) -> None:
        """Show an important message to the user.

        Normally used as the final message, to show the result of a command, but it can
        also be used for important messages during the command's execution,
        with intermediate=True (which will include timestamp in verbose/trace mode).
        """
        if intermediate and (self.mode == EmitterMode.VERBOSE or self.mode == EmitterMode.TRACE):
            use_timestamp = True
        else:
            use_timestamp = False
        self.printer.show(sys.stdout, text, use_timestamp=use_timestamp)

    def trace(self, text: str) -> None:
        """Trace/debug information.

        This is to record everything that the user may not want to normally see, but it's
        useful for postmortem analysis.
        """
        if self.mode == EmitterMode.TRACE:
            stream = sys.stderr
        else:
            stream = None
        self.printer.show(stream, text, use_timestamp=True)

    def progress(self, text: str) -> None:
        """Progress information for a multi-step command.

        This is normally to present several separated text messages.

        These messages will be truncated to the terminal's width, and overwritten by the next
        line (unless verbose/trace mode).
        """
        if self.mode == EmitterMode.QUIET:
            # will not be shown in the screen (always logged to the file)
            stream = None
            use_timestamp = False
            ephemeral = True
        elif self.mode == EmitterMode.NORMAL:
            # show to stderr, just the indicated message, respecting the "ephemeral" indication
            stream = sys.stderr
            use_timestamp = False
            ephemeral = True
        else:
            # show to stderr, with timestamp, always permanent
            stream = sys.stderr
            use_timestamp = True
            ephemeral = False

        self.printer.show(stream, text, ephemeral=ephemeral, use_timestamp=use_timestamp)

    def progress_bar(self, text: str, total: Union[int, float], delta: bool = True) -> _Progresser:
        """Progress information for a potentially long-running single step of a command.

        E.g. a download or provisioning step.

        Returns a context manager with a `.advance` method to call on each progress (passing the
        delta progress, unless delta=False here, which implies that the calls to `.advance` should
        pass the total so far).
        """
        # don't show progress if quiet
        if self.mode == EmitterMode.QUIET:
            stream = None
        else:
            stream = sys.stderr
        self.printer.show(stream, text, ephemeral=True)
        return _Progresser(self.printer, total, text, stream, delta)

    def open_stream(self, text: str):
        """Open a stream context manager to get messages from subprocesses."""
        # don't show strems if quit or normal
        if self.mode == EmitterMode.QUIET or self.mode == EmitterMode.NORMAL:
            stream = None
        else:
            stream = sys.stderr
        return _StreamContextManager(self.printer, text, stream)

    def ended_ok(self) -> None:
        """Finish the messaging system gracefully."""
        self.printer.stop()

    def _get_traceback_lines(self, exc: Exception):
        """Get the traceback lines (if any) from an exception."""
        tback_lines = traceback.format_exception(exc, exc, exc.__traceback__)
        for tback_line in tback_lines:
            for real_line in tback_line.rstrip().split("\n"):
                yield real_line

    def _report_error(self, error: CraftError) -> None:
        """Report the different message lines from a CraftError."""
        if self.mode == EmitterMode.QUIET or self.mode == EmitterMode.NORMAL:
            use_timestamp = False
            full_stream = None
        else:
            use_timestamp = True
            full_stream = sys.stderr

        # the initial message
        self.printer.show(sys.stderr, str(error), use_timestamp=use_timestamp, end_line=True)

        # detailed information and/or original exception
        if error.details:
            text = f"Detailed information: {error.details}"
            self.printer.show(full_stream, text, use_timestamp=use_timestamp, end_line=True)
        if error.__cause__:
            for line in self._get_traceback_lines(error.__cause__):
                self.printer.show(full_stream, line, use_timestamp=use_timestamp, end_line=True)

        # hints for the user to know more
        if error.resolution:
            text = f"Recommended resolution: {error.resolution}"
            self.printer.show(sys.stderr, text, use_timestamp=use_timestamp, end_line=True)
        if error.docs_url:
            text = f"For more information, check out: {error.docs_url}"
            self.printer.show(sys.stderr, text, use_timestamp=use_timestamp, end_line=True)

        text = f"Full execution log: {str(self.log_filepath)!r}"
        self.printer.show(sys.stderr, text, use_timestamp=use_timestamp, end_line=True)

    def error(self, error: CraftError) -> None:
        """Handle the system's indicated error and stop machinery."""
        self._report_error(error)
        self.printer.stop()


emit = Emitter()
