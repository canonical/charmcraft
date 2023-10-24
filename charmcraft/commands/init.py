# Copyright 2020-2022 Canonical Ltd.
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

"""Infrastructure for the 'init' command."""

import os
import re
from datetime import date
from typing import Optional

from craft_cli import CraftError, emit

from charmcraft.cmdbase import BaseCommand
from charmcraft.utils import get_templates_environment, make_executable

try:
    import pwd
except ImportError:
    pwd = None  # type: ignore[assignment]

# the available profiles and in which directory the template can be found
PROFILES = {
    "simple": "init-simple",
    "kubernetes": "init-kubernetes",
    "machine": "init-machine",
}
DEFAULT_PROFILE = "simple"


_overview = """
Initialize a charm operator package tree and files.

This command will modify the directory to create the necessary files for a
charm operator package. By default it will work in the current directory.

Available profiles are:
    simple:
        A basic kubernetes charm with lot of texts helping the developer
        to navigate their first charm by following the instructions.

    kubernetes:
        A basic Kubernetes charm with example container.

    machine:
        A basic charm but meant to be deployed in machine-based environments,
        without container requirements.

Depending on the profile choice, Charmcraft will setup the following tree of
files and directories:

    .
    ├── charmcraft.yaml        - Charm build configuration
    ├── CONTRIBUTING.md        - Instructions for how to build and develop
    │                             your charm
    ├── LICENSE                - Your charm license, we recommend Apache 2
    ├── pyproject.toml         - Configuration for testing, formatting and
    │                             linting tools
    ├── README.md              - Frontpage for your charmhub.io/charm/
    ├── requirements.txt       - PyPI dependencies for your charm, with `ops`
    ├── src
    │   └── charm.py           - Minimal operator using Python operator framework
    ├── tests
    │   ├── integration
    │   │   └── test_charm.py  - Integration tests
    │   └── unit
    │       └── test_charm.py  - Unit tests
    └── tox.ini                - Configuration for tox, the tool to run all tests

You will need to edit at least charmcraft.yaml and README.md.

Your minimal operator code is in src/charm.py which uses the Python operator
framework from https://github.com/canonical/operator and there are some
example unit and integration tests with a harness to run them.
"""

SUCCESS_MESSAGE = """\
Charmed operator package file and directory tree initialised.

Now edit the following package files to provide fundamental charm metadata
and other information:

charmcraft.yaml
src/charm.py
README.md
"""


def _get_users_full_name_gecos() -> Optional[str]:
    """Get user's full name from Gecos (/etc/passwd)."""
    try:
        return pwd.getpwuid(os.getuid()).pw_gecos.split(",", 1)[0]
    except KeyError:
        return None


class InitCommand(BaseCommand):
    """Initialize a directory to be a charm project."""

    name = "init"
    help_msg = "Initialize a charm operator package tree and files"
    overview = _overview
    common = True

    def fill_parser(self, parser):
        """Specify command's specific parameters."""
        parser.add_argument("--name", help="The name of the charm; defaults to the directory name")
        parser.add_argument(
            "--author",
            help="The charm author; defaults to the current user name per GECOS",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Initialize even if the directory is not empty (will not overwrite files)",
        )
        parser.add_argument(
            "--profile",
            choices=list(PROFILES),
            default=DEFAULT_PROFILE,
            help=f"Use the specified project profile (defaults to '{DEFAULT_PROFILE}')",
        )

    def run(self, args):
        """Execute command's actual functionality."""
        init_dirpath = self.config.project.dirpath
        if not init_dirpath.exists():
            init_dirpath.mkdir(parents=True)
        elif any(init_dirpath.iterdir()) and not args.force:
            tpl = "{!r} is not empty (consider using --force to work on nonempty directories)"
            raise CraftError(tpl.format(str(init_dirpath)))
        emit.debug(f"Using project directory {str(init_dirpath)!r}")

        if args.author is None and pwd is not None:
            args.author = _get_users_full_name_gecos()

        if not args.author:
            raise CraftError(
                "Unable to automatically determine author's name, specify it with --author"
            )

        if not args.name:
            args.name = init_dirpath.name
            emit.debug(f"Set project name to '{args.name}'")

        if not re.match(r"[a-z][a-z0-9-]*[a-z0-9]$", args.name):
            raise CraftError(
                f"{args.name} is not a valid charm name. "
                "The name must start with a lowercase letter "
                "and contain only alphanumeric characters and hyphens."
            )

        context = {
            "name": args.name,
            "author": args.author,
            "year": date.today().year,
            "class_name": "".join(re.split(r"\W+", args.name.title())) + "Charm",
        }

        template_directory = PROFILES[args.profile]
        env = get_templates_environment(template_directory)

        executables = ["run_tests", "src/charm.py"]
        for template_name in env.list_templates():
            if not template_name.endswith(".j2"):
                continue
            template = env.get_template(template_name)
            template_name = template_name[:-3]
            emit.debug(f"Rendering {template_name}")
            path = init_dirpath / template_name
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wt", encoding="utf8") as fh:
                out = template.render(context)
                fh.write(out)
                if template_name in executables and os.name == "posix":
                    make_executable(fh)
                    emit.debug("  made executable")
        for line in SUCCESS_MESSAGE.split("\n"):
            emit.message(line)
