# Copyright (c) {{ year }} {{ author }}
# See LICENSE file for licensing details.

import unittest
from ops.testing import Harness
from charm import {{ class_name }}


class TestCharm(unittest.TestCase):
    def test_config_changed(self):
        harness = Harness({{ class_name }})
        self.addCleanup(harness.cleanup)
        harness.begin()
        self.assertEqual(list(harness.charm._stored.things), [])
        harness.update_config({"thing": "foo"})
        self.assertEqual(list(harness.charm._stored.things), ["foo"])
