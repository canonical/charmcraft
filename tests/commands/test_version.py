# Copyright 2020 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft

import logging

from charmcraft.commands.version import VersionCommand


def test_version_result(caplog):
    """Check it produces the right version."""
    # XXX: this is bogus so we build all the infrastructure, but we need to update it
    # when we define how we want to store the version
    caplog.set_level(logging.INFO, logger="charmcraft.commands.version")
    cmd = VersionCommand('group')
    cmd.run([])
    assert ["Version: 0.0.1"] == [rec.message for rec in caplog.records]
