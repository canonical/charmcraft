# Copyright 2021-2022 Canonical Ltd.
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

from craft_cli import emit
from craft_providers import Executor

from charmcraft.env import get_managed_environment_log_path


def capture_logs_from_instance(instance: Executor) -> None:
    """Retrieve logs from instance.

    :param instance: Instance to retrieve logs from.

    :returns: String of logs.
    """
    # Get a temporary file path (placing it in current directory as it's the most predictible
    # place where a strictly-snapped app could write)
    tmp_file = tempfile.NamedTemporaryFile(
        delete=False, prefix="charmcraft-", suffix="-temporary.log", dir="."
    )
    tmp_file.close()

    local_log_path = pathlib.Path(tmp_file.name)
    instance_log_path = get_managed_environment_log_path()

    try:
        instance.pull_file(source=instance_log_path, destination=local_log_path)
    except FileNotFoundError:
        local_log_path.unlink()
        emit.debug("No logs found in instance.")
        return

    emit.debug("Logs captured from managed instance:")
    with open(local_log_path, "rt", encoding="utf8") as fh:
        for line in fh:
            emit.debug(f":: {line.rstrip()}")
    local_log_path.unlink()
