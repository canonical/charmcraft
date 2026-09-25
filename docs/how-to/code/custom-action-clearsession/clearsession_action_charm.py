#!/usr/bin/env python3
# Copyright 2025 root
# See LICENSE file for licensing details.

"""Django Charm entrypoint."""

import logging
import typing

import ops

import paas_charm.django

logger = logging.getLogger(__name__)


class DjangoHelloWorldCharm(paas_charm.django.Charm):
    """Django Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.framework.observe(self.on.clearsession_action,
                               self._on_clearsession_action)

    def _on_clearsession_action(self, event: ops.ActionEvent) -> None:
        """Handle the clearsession action.
        Args:
            event: the action event object.
        """
        if not self.is_ready():
            event.fail("django-app container is not ready")
        try:
            self._container.exec(
                ["python3", "manage.py", "clearsessions"],
                service_context="django",
                combine_stderr=True,
                working_dir=str(self._workload_config.app_dir),
            ).wait_output()
            event.set_results({"result": "session cleared!"})
        except ops.pebble.ExecError as e:
            event.fail(str(e.stdout))

if __name__ == "__main__":
    ops.main(DjangoHelloWorldCharm)
