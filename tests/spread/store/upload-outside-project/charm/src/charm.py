#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for testing upload outside project directory."""

import logging

from ops.charm import CharmBase
from ops.main import main

logger = logging.getLogger(__name__)


class TestCharm(CharmBase):
    """Charm for testing upload outside project directory."""

    def __init__(self, *args):
        super().__init__(*args)


if __name__ == "__main__":  # pragma: nocover
    main(TestCharm)
