(file-tests-unit-test-charm-py)=
# File 'tests/unit/test_charm.py'

> <small> {ref}`List of files in the charm project <list-of-files-in-a-charm-project>` > `tests/test_charm.py` </small>
>
> See also: {ref}`How to test a charm <how-to-write-unit-tests-for-a-charm>`

The `tests/unit/test_charm.py` file is the companion to `src/charm.py` for unit testing. It is pre-populated with standard constructs used by `unittest` and Harness.

This file is created automatically by `charmcraft init` and it is pre-populated with standard constructs used by `unittest` and `Harness`, along the lines below:

```text

# Copyright 2023 Ubuntu
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

import ops
import ops.testing
from charm import MyK8SCharmCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = ops.testing.Harness(MyK8SCharmCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_pebble_ready(self):
        # Simulate the container coming up and emission of pebble-ready event
        self.harness.container_pebble_ready("some-container")
        # Ensure we set an ActiveStatus with no message
        self.assertEqual(self.harness.model.unit.status, ops.ActiveStatus())
```
