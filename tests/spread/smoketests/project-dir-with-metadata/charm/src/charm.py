#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for testing --project-dir with metadata.yaml."""

import logging

import ops

logger = logging.getLogger(__name__)


class TestCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.install, self._on_install)

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":
    ops.main(TestCharm)
