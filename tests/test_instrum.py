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

"""Tests for the instrumentator module."""

import json
from unittest.mock import patch

import pytest

from charmcraft import instrum
from charmcraft.instrum import Timer, _Measurements


@pytest.fixture
def fake_times():
    """Provide times from 5 by 10."""
    with patch("charmcraft.instrum.time", side_effect=list(range(5, 100, 10))):
        yield


# -- tests for the Measurement class


def test_measurement_start_end_cycle(fake_times):
    """Basic start and end cycle."""
    measurements = _Measurements()

    mid = measurements.start("test msg", {"foo": "bar"})
    assert measurements.parents == [None, mid]
    recorded = measurements.measurements[mid]
    assert recorded == {
        "parent": None,
        "msg": "test msg",
        "extra": {"foo": "bar"},
        "tstart": 5,
        "tend": None,
    }

    measurements.end(mid)
    assert measurements.parents == [None]
    recorded = measurements.measurements[mid]
    assert recorded == {
        "parent": None,
        "msg": "test msg",
        "extra": {"foo": "bar"},
        "tstart": 5,
        "tend": 15,
    }


def test_measurement_tree():
    """A tree is built for the measurements."""
    measurements = _Measurements()

    # start first
    mid_1 = measurements.start("test msg", {})
    assert measurements.parents == [None, mid_1]
    assert measurements.measurements[mid_1]["parent"] is None

    # start second
    mid_2 = measurements.start("test msg", {})
    assert measurements.parents == [None, mid_1, mid_2]
    assert measurements.measurements[mid_2]["parent"] == mid_1

    # start third
    mid_3 = measurements.start("test msg", {})
    assert measurements.parents == [None, mid_1, mid_2, mid_3]
    assert measurements.measurements[mid_3]["parent"] == mid_2

    # end them all
    measurements.end(mid_3)
    assert measurements.parents == [None, mid_1, mid_2]
    measurements.end(mid_2)
    assert measurements.parents == [None, mid_1]
    measurements.end(mid_1)
    assert measurements.parents == [None]


def test_measurement_extra_info_complex():
    """No objects are leaked in the extra info."""
    measurements = _Measurements()

    weird_object = object()

    mid = measurements.start("test msg", {"foo": 42, "bar": weird_object})
    assert measurements.measurements[mid]["extra"] == {"foo": "42", "bar": str(weird_object)}


def test_measurement_overlapped_measurements():
    """The instrumentator set up overlapped measurements."""
    measurements = _Measurements()

    # start first and second
    mid_1 = measurements.start("test msg", {})
    measurements.start("test msg", {})

    # end first before second
    with pytest.raises(ValueError):
        measurements.end(mid_1)


def test_measurement_dump(tmp_path, fake_times):
    """Dump the measurements content to a dump file."""
    measurements = _Measurements()
    mid = measurements.start("test msg", {"foo": "bar"})
    measurements.end(mid)

    measures_filepath = tmp_path / "measures.json"
    with patch("charmcraft.instrum._baseline", 3):
        measurements.dump(measures_filepath)

    dumped_content = json.loads(measures_filepath.read_text())
    assert dumped_content == {
        "__meta__": {"baseline": 3},  # patched value
        mid: {
            "extra": {"foo": "bar"},
            "msg": "test msg",
            "parent": None,
            "tstart": 2,  # relative to baseline
            "tend": 12,  # relative to baseline
        },
    }


def test_measurement_merge_simple(tmp_path, fake_times):
    """Merge a simple measurement into current structure."""
    measures_filepath = tmp_path / "measures.json"

    # start the outer measure
    measurements_outer = _Measurements()
    mid_outer = measurements_outer.start("outer msg", {})

    # meanwhile, start the inner measure
    measurements_inner = _Measurements()
    mid_inner = measurements_inner.start("inner msg", {})
    measurements_inner.end(mid_inner)
    with patch("charmcraft.instrum._baseline", 12):
        measurements_inner.dump(measures_filepath)

    # confirm dumped info
    dumped_content = json.loads(measures_filepath.read_text())
    assert dumped_content == {
        "__meta__": {"baseline": 12},  # patched value
        mid_inner: {
            "extra": {},
            "msg": "inner msg",
            "parent": None,
            "tstart": 3,  # relative to baseline
            "tend": 13,  # relative to baseline
        },
    }

    # merge from it and check merged structure
    measurements_outer.merge_from(measures_filepath)
    merged = measurements_outer.measurements[mid_inner]
    assert merged["parent"] == mid_outer  # not None anymore
    assert merged["tstart"] == 15  # back to absolute
    assert merged["tend"] == 25  # back to absolute


def test_measurement_merge_complex(tmp_path, fake_times):
    """Merge a complex measurements tree into current structure."""
    measures_filepath = tmp_path / "measures.json"

    # start two outer measures
    measurements_outer = _Measurements()
    measurements_outer.start("outer msg 1", {})  # fake time: 5
    mid_outer_2 = measurements_outer.start("outer msg 2", {})  # fake time: 15

    # in the inner measurement start two root ones, one with a "child"
    measurements_inner = _Measurements()
    mid_inner_1 = measurements_inner.start("inner msg 1", {})  # fake time: 25
    mid_inner_2 = measurements_inner.start("inner msg 2", {})  # fake time: 35
    measurements_inner.end(mid_inner_2)  # fake time: 45
    measurements_inner.end(mid_inner_1)  # fake time: 55
    mid_inner_3 = measurements_inner.start("inner msg 3", {})  # fake time: 65
    measurements_inner.end(mid_inner_3)  # fake time: 75

    # dump it all
    with patch("charmcraft.instrum._baseline", 20):
        measurements_inner.dump(measures_filepath)

    # confirm dumped info
    dumped_content = json.loads(measures_filepath.read_text())
    assert dumped_content == {
        "__meta__": {"baseline": 20},  # patched value
        mid_inner_1: {
            "extra": {},
            "msg": "inner msg 1",
            "parent": None,
            "tstart": 5,  # relative to baseline
            "tend": 35,  # relative to baseline
        },
        mid_inner_2: {
            "extra": {},
            "msg": "inner msg 2",
            "parent": mid_inner_1,
            "tstart": 15,  # relative to baseline
            "tend": 25,  # relative to baseline
        },
        mid_inner_3: {
            "extra": {},
            "msg": "inner msg 3",
            "parent": None,
            "tstart": 45,  # relative to baseline
            "tend": 55,  # relative to baseline
        },
    }

    # merge from it and check merged structure
    measurements_outer.merge_from(measures_filepath)
    merged_1 = measurements_outer.measurements[mid_inner_1]
    assert merged_1["parent"] == mid_outer_2  # the parent is the "current" outer measure
    assert merged_1["tstart"] == 25  # back to absolute
    assert merged_1["tend"] == 55  # back to absolute
    merged_2 = measurements_outer.measurements[mid_inner_2]
    assert merged_2["parent"] == mid_inner_1  # inside the structure, parent respected
    assert merged_2["tstart"] == 35  # back to absolute
    assert merged_2["tend"] == 45  # back to absolute
    merged_3 = measurements_outer.measurements[mid_inner_3]
    assert merged_3["parent"] == mid_outer_2  # the parent is the "current" outer measure
    assert merged_3["tstart"] == 65  # back to absolute
    assert merged_3["tend"] == 75  # back to absolute


# -- tests for the Timer class


def test_timer_as_context_manager(fake_times, monkeypatch):
    """Use test as a context manager."""
    measurements = _Measurements()
    monkeypatch.setattr(instrum, "_measurements", measurements)
    assert measurements.measurements == {}

    with Timer("test message", foo=42):
        pass

    (recorded,) = measurements.measurements.values()
    assert recorded == {
        "parent": None,
        "msg": "test message",
        "extra": {"foo": "42"},
        "tstart": 5,
        "tend": 15,
    }


def test_timer_as_context_manager_with_mark(fake_times, monkeypatch):
    """Use test as a context manager, hitting marks in the code block."""
    measurements = _Measurements()
    monkeypatch.setattr(instrum, "_measurements", measurements)

    @Timer("test message", foo=42)
    def test_function(a, b):
        assert a == 17
        assert b == 35

    assert measurements.measurements == {}
    test_function(17, b=35)

    (recorded,) = measurements.measurements.values()
    assert recorded == {
        "parent": None,
        "msg": "test message",
        "extra": {"foo": "42"},
        "tstart": 5,
        "tend": 15,
    }


def test_timer_as_decorator(fake_times, monkeypatch):
    """Use test as a decorator."""
    measurements = _Measurements()
    monkeypatch.setattr(instrum, "_measurements", measurements)
    assert measurements.measurements == {}

    with Timer("test message", foo=42) as timer:
        timer.mark("middle 1")
        timer.mark("middle 2")

    (recorded_1, recorded_2, recorded_3) = measurements.measurements.values()

    # first we have the context manager itself, that starts at the very
    # beginning and ends on the first mark
    assert recorded_1 == {
        "parent": None,
        "msg": "test message",
        "extra": {"foo": "42"},
        "tstart": 5,
        "tend": 15,
    }

    # then the measure between both marks
    assert recorded_2 == {
        "parent": None,
        "msg": "middle 1",
        "extra": {},
        "tstart": 25,
        "tend": 35,
    }

    # finally the measure between second mark and the end of the context manager
    assert recorded_3 == {
        "parent": None,
        "msg": "middle 2",
        "extra": {},
        "tstart": 45,
        "tend": 55,
    }
