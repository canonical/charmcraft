# Copyright 2021 Canonical Ltd.
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

"""Build environment provider support for charmcraft."""

import pathlib
import tempfile

from craft_providers import Executor

from charmcraft.env import get_managed_environment_log_path
from charmcraft.poc_messages_lib import emit


def capture_logs_from_instance(instance: Executor) -> None:
    """Retrieve logs from instance.

    :param instance: Instance to retrieve logs from.

    :returns: String of logs.
    """
    # FIXME: bad docstring
    _, tmp_path = tempfile.mkstemp(prefix="charmcraft-")
    local_log_path = pathlib.Path(tmp_path)
    instance_log_path = get_managed_environment_log_path()

    try:
        instance.pull_file(source=instance_log_path, destination=local_log_path)
    except FileNotFoundError:
        emit.trace("No logs found in instance.")
        return

    logs = local_log_path.read_text()
    local_log_path.unlink()

    emit.trace(f"Logs captured from managed instance:\n{logs}")  # FIXME: don't like the \n here
