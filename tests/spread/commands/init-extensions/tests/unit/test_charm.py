# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Smoke scenario test for paas-charm based init templates."""

import os
import pathlib

import charm
import scenario
import scenario.errors


def test_smoke():
    """The purpose of this test is that the charm does not raise on a handled event."""
    os.chdir(pathlib.Path(charm.__file__).parent.parent)
    ctx = scenario.Context(charm.HelloWorldCharm)
    state_in = scenario.State.from_context(ctx)
    out = ctx.run(
        ctx.on.pebble_ready(next(iter(state_in.containers))),
        state_in,
    )
    assert type(out.unit_status) in (scenario.WaitingStatus, scenario.BlockedStatus)
