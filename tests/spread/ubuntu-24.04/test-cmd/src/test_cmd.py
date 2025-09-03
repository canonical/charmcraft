"""Functions for managing and interacting with the workload.

The intention is that this module could be used outside the context of a charm.
"""

import logging

logger = logging.getLogger(__name__)


# Functions for managing the workload process on the local machine:


def install() -> None:
    """Install the workload (by installing a snap, for example)."""
    # You'll need to implement this function.


def start() -> None:
    """Start the workload (by running a command, for example)."""
    # You'll need to implement this function.
    # Ideally, this function should only return once the workload is ready to use.


# Functions for interacting with the workload, for example over HTTP:


def get_version() -> str | None:
    """Get the running version of the workload."""
    # You'll need to implement this function (or remove it if not needed).
    return None
