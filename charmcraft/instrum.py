# Copyright 2022 Canonical Ltd.
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

"""Provide utilities to measure performance in different parts of the app."""

import json
import uuid
from time import time
from typing import Any

# the base time of the started process: all the recorded times will be relative to
# this one (they will be easier to read and simple to understand the time passed since
# the process started until we started measuring)
_baseline = time()


class _Measurements:
    """Hold the measurements done and provide utilities around that structure."""

    def __init__(self):
        # ancestors list when a measure starts (last item is direct parent); the
        # first value is special, None, to reflect the "root", the rest are
        # measurement ids
        self.parents = [None]  # start with a unique "root"

        # simple dict to hold measurements information; the key is the measurement
        # id and each value holds all it info
        self.measurements = {}

    def start(self, msg: str, extra_info: dict[str, Any]):
        """Start a measurement."""
        this_id = uuid.uuid4().hex
        parent_id = self.parents[-1]
        self.parents.append(this_id)

        extra_info = {k: str(v) for k, v in extra_info.items()}
        self.measurements[this_id] = {
            "parent": parent_id,
            "msg": msg,
            "extra": extra_info,
            "tstart": time(),
            "tend": None,
        }
        return this_id

    def end(self, measurement_id):
        """Finish the indicated measurement."""
        if measurement_id != self.parents[-1]:
            raise ValueError("Overlapped measurements.")

        self.measurements[measurement_id]["tend"] = time()
        self.parents.pop()

    def dump(self, filename: str) -> None:
        """Dump the ongoing measurements to the specified file in a JSON format."""
        measurements = self.measurements.copy()
        for m in measurements.values():
            m["tstart"] -= _baseline
            m["tend"] -= _baseline
        measurements["__meta__"] = {"baseline": _baseline}
        with open(filename, "w") as fh:
            json.dump(measurements, fh, indent=4)

    def merge_from(self, filename: str) -> None:
        """Merge measurements from a file to the current ongoing structure."""
        with open(filename) as fh:
            to_merge = json.load(fh)

        # add the measurements from the file to this process ones, and while doing that
        # hook "root" measurements to current one and shift times
        current_id = self.parents[-1]
        sublayer_baseline = to_merge.pop("__meta__")["baseline"]

        for mid, data in to_merge.items():
            data["tstart"] += sublayer_baseline
            data["tend"] += sublayer_baseline
            if data["parent"] is None:
                data["parent"] = current_id
            self.measurements[mid] = data


# unique _Measurements object and external api
_measurements = _Measurements()
dump = _measurements.dump
merge_from = _measurements.merge_from


class Timer:
    """Get the timing of a block of code.

    It can work as a context manager that generates a measurement of the block of code inside
    its context, or as a decorator to get the timing of the whole decorated function.

    Usage as a context manager::

        with timer("some message", more="stuff", answer=42):
            ...

    Usage as a decorator::

        @timer("some message", foo="bar")
        def foo(...):
            ...

    In both cases the message is mandatory and the extra info optional.

    Also this class provides a `mark` method to sub-divide the context manager code
    block. How to use it::

        with timer("some message") as cm:
            ...
            cm.mark("first half done!")
            ...
    """

    def __init__(self, msg: str, **extra_info: dict[str, Any]):
        self.msg = msg
        self.extra_info = extra_info
        self.measurement_id = None

    def __enter__(self):
        self.measurement_id = _measurements.start(self.msg, self.extra_info)
        return self

    def __exit__(self, *exc):
        _measurements.end(self.measurement_id)

    def mark(self, msg: str, **extra_info: dict[str, Any]):
        """Mark middle measurements inside a contextual one."""
        # close the previous one, and start a new measure
        _measurements.end(self.measurement_id)
        self.measurement_id = _measurements.start(msg, extra_info)

    def __call__(self, func):
        """Decorate a function with self class to measure its execution."""

        def _f(*args, **kwargs):
            with self.__class__(self.msg, **self.extra_info):
                return func(*args, **kwargs)

        return _f
