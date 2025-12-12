# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Smoke scenario test for paas-charm based init templates."""

import os
import pathlib

import charm
from ops import testing


def test_smoke():
    """The purpose of this test is that the charm does not raise on a handled event."""
    os.chdir(pathlib.Path(charm.__file__).parent.parent)
    ctx = testing.Context(charm.HelloWorldCharm)
    state_in = testing.State.from_context(ctx)
    container = next(iter(state_in.containers))
    state_out = ctx.run(ctx.on.pebble_ready(container), state_in)
    assert type(state_out.unit_status) in (testing.WaitingStatus, testing.BlockedStatus)
