#!/usr/bin/env python3
"""Test charm 1."""

import ops


class TestCharm(ops.CharmBase):
    """Test charm class."""

    def __init__(self, *args):
        super().__init__(*args)


if __name__ == "__main__":
    ops.main(TestCharm)
