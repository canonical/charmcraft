# Copyright 2024 Canonical Ltd.
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
"""Module for helping with creating a dispatch script for charms."""

import pathlib

import craft_cli

from charmcraft import const

DISPATCH_SCRIPT_TEMPLATE = """\
#!/bin/sh
dispatch_path="$(dirname $(realpath $0))"
venv_bin_path="${{dispatch_path}}/venv/bin"
python_path="${{venv_bin_path}}/python"
if [ ! -e "${{python_path}}" ]; then
    mkdir -p "${{venv_bin_path}}"
    ln -s $(which python3) "${{python_path}}"
fi

# Add charm lib and source directories to PYTHONPATH so the charm can import
# libraries and its own modules as expected.
export PYTHONPATH="${{dispatch_path}}/lib:${{dispatch_path}}/src"

# Add the charm's lib and usr/lib directories to LD_LIBRARY_PATH, allowing
# staged packages to be discovered by the dynamic linker.
export LD_LIBRARY_PATH="${{dispatch_path}}/usr/lib:${{dispatch_path}}/lib:${{dispatch_path}}/usr/lib/$(uname -m)-linux-gnu"

exec "${{python_path}}" "${{dispatch_path}}/{entrypoint}"
"""


def create_dispatch(
    *, prime_dir: pathlib.Path, entrypoint: str = "src/charm.py"
) -> bool:
    """If the charm has no hooks or dispatch, create a dispatch file.

    :param prime_dir: the prime directory to inspect and create the file in.
    :returns: True if the file was created, False otherwise.
    """
    dispatch_path = prime_dir / const.DISPATCH_FILENAME
    hooks_path = prime_dir / const.HOOKS_DIRNAME

    if hooks_path.is_dir() or dispatch_path.is_file():
        return False

    if not (prime_dir / entrypoint).exists():
        return False

    craft_cli.emit.progress("Creating dispatch file")
    dispatch_path.write_text(DISPATCH_SCRIPT_TEMPLATE.format(entrypoint=entrypoint))
    dispatch_path.chmod(mode=0o755)

    return True
