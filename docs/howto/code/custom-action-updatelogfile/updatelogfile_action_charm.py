#!/usr/bin/env python3
# Copyright 2025 Ubuntu
# See LICENSE file for licensing details.

"""Flask Charm entrypoint."""

import logging
import typing

import ops

import paas_charm.flask

import requests

logger = logging.getLogger(__name__)


class FlaskHelloWorldCharm(paas_charm.flask.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.framework.observe(self.on.updatelogfile_action,
                               self._on_updatelogfile_action)

    def _on_updatelogfile_action(self, event: ops.ActionEvent) -> None:
        """Handle the updatelogfile action.

        Args:
            event: the action event object.
            logfile: the output logfile in the container
        """
        if not self.is_ready():
            event.fail("flask-app container is not ready")
        try:
            response = requests.get(
                    f"http://127.0.0.1:{self._workload_config.port}", timeout=5
                    )
            response.raise_for_status()
            self._container.push(event.params["logfile"], response.text)
            output = response.text
            output += " written to file " + event.params["logfile"]
            event.set_results({"result": output})
        except ops.pebble.ExecError as e:
            event.fail(str(e.stderr))
        except requests.exceptions.RequestException as e:
            # if it failed with http bad status code or the connection failed
            event.fail(str(e.stderr))

if __name__ == "__main__":
    ops.main(FlaskHelloWorldCharm)
