# Copyright 2020-2024 Canonical Ltd.
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

import argparse
import os
import pathlib
import re
from datetime import date

from craft_cli import CraftError, emit

from charmcraft.application.commands import base
from charmcraft.utils import get_templates_environment, make_executable

try:
    import pwd
except ImportError:
    pwd = None  # type: ignore[assignment]

# the available profiles and in which directory the template can be found
PROFILES = {
    "kubernetes": "init-kubernetes",
    "machine": "init-machine",
    "flask-framework": "init-flask-framework",
    "django-framework": "init-django-framework",
    "go-framework": "init-go-framework",
    "fastapi-framework": "init-fastapi-framework",
    "expressjs-framework": "init-expressjs-framework",
    "spring-boot-framework": "init-spring-boot-framework",
    "test-kubernetes": "test-kubernetes",
    "test-machine": "test-machine",
}
DEFAULT_PROFILE = "kubernetes"


_overview = """
Initialize a charm operator package tree and files.

This command will modify the directory to create the necessary files for a
charm operator package. By default it will work in the current directory.

Available profiles are:
    kubernetes:
        A basic Kubernetes charm with example container.

    machine:
        A basic charm but meant to be deployed in machine-based environments,
        without container requirements.

    django-framework:
        A basic Kubernetes charm for a 12-factor Django app.

    fastapi-framework:
        A basic Kubernetes charm for a 12-factor FastAPI app.

    flask-framework:
        A basic Kubernetes charm for a 12-factor Flask app.

    go-framework:
        A basic Kubernetes charm for a 12-factor Go app.

    spring-boot-framework:
        A basic Kubernetes charm for a 12-factor Spring Boot app.

Depending on the profile choice, Charmcraft will setup the following tree of
files and directories::

    .
    ├── charmcraft.yaml            - Charm build configuration
    ├── CONTRIBUTING.md            - Instructions for how to build and develop
    │                                your charm
    ├── LICENSE                    - Your charm license, we recommend Apache 2
    ├── pyproject.toml             - Configuration for testing, formatting and
    │                                linting tools. Specifies Python dependencies for
    │                                your charm if profile is 'kubernetes' or 'machine'
    ├── README.md                  - Frontpage for your charmhub.io/charm/
    ├── requirements.txt           - Python dependencies for your charm, with Ops,
    │                                created for 12-factor app profiles only
    ├── src
    │   ├── charm.py               - Python code that operates your charm's workload
    │   └── <workload>.py          - Standalone module for workload-specific logic,
    │                                created if profile is 'kubernetes' or 'machine'
    ├── tests
    │   ├── integration
    │   │   └── test_charm.py      - Integration tests
    │   └── unit
    │       └── test_charm.py      - Unit tests
    ├── tox.ini                    - Configuration for tox, the tool to run all tests
    ├── uv.lock                    - Specifies exact versions of Python dependencies,
    │                                created if profile is 'kubernetes' or 'machine'

You will need to edit at least charmcraft.yaml and README.md.

Your minimal operator code is in src/charm.py, which uses the 'ops' Python framework.
See https://documentation.ubuntu.com/ops/latest/. There are also some sample unit and
integration tests, which you can run using 'tox -e unit' and 'tox -e integration'.
"""


def _make_success_message(src_files: list[str]) -> str:
    src_files_str = "\n".join(src_files)
    return f"""\
Charmed operator package file and directory tree initialised.

Now edit the following package files to provide fundamental charm metadata
and other information:

charmcraft.yaml
{src_files_str}
README.md
"""


def _make_workload_module_name(charm_name: str) -> str:
    module_name = charm_name.replace("-", "_")
    generic_names = [  # put names with more components at the beginning of the list
        "k8s_charm",
        "k8s_operator",
        "machine_charm",
        "machine_operator",
        "vm_charm",
        "vm_operator",
        "charm",
        "operator",
        "k8s",
        "machine",
        "vm",
    ]
    if module_name in generic_names:
        return "workload"
    for generic_name in generic_names:
        generic_suffix = f"_{generic_name}"
        if module_name.endswith(generic_suffix):
            return module_name[: -len(generic_suffix)]
    return module_name


def _get_users_full_name_gecos() -> str | None:
    """Get user's full name from Gecos (/etc/passwd)."""
    try:
        return pwd.getpwuid(os.getuid()).pw_gecos.split(",", 1)[0]
    except KeyError:
        return None


class InitCommand(base.CharmcraftCommand):
    """Initialize a directory to be a charm project."""

    name = "init"
    help_msg = "Initialize a charm operator package tree and files"
    overview = _overview
    common = True

    def fill_parser(self, parser):
        """Specify command's specific parameters."""
        parser.add_argument(
            "--name", help="The name of the charm; defaults to the directory name"
        )
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
        parser.add_argument(
            "-p",
            "--project-dir",
            type=pathlib.Path,
            default=pathlib.Path.cwd(),
            help="Specify the project's directory (defaults to current)",
        )

    def run(self, parsed_args: argparse.Namespace):
        """Execute command's actual functionality."""
        init_dirpath = parsed_args.project_dir.resolve()
        if not init_dirpath.exists():
            init_dirpath.mkdir(parents=True)
        elif any(init_dirpath.iterdir()) and not parsed_args.force:
            tpl = "{!r} is not empty (consider using --force to work on nonempty directories)"
            raise CraftError(tpl.format(str(init_dirpath)))
        emit.debug(f"Using project directory {str(init_dirpath)!r}")

        if parsed_args.author is None and pwd is not None:
            parsed_args.author = _get_users_full_name_gecos()

        if not parsed_args.author:
            raise CraftError(
                "Unable to automatically determine author's name, specify it with --author"
            )

        if not parsed_args.name:
            parsed_args.name = init_dirpath.name
            emit.debug(f"Set project name to '{parsed_args.name}'")

        if not re.match(r"[a-z][a-z0-9-]*[a-z0-9]$", parsed_args.name):
            raise CraftError(
                f"{parsed_args.name} is not a valid charm name. "
                "The name must start with a lowercase letter "
                "and contain only alphanumeric characters and hyphens."
            )

        context = {
            "name": parsed_args.name,
            "author": parsed_args.author,
            "year": date.today().year,
            "class_name": "".join(re.split(r"\W+", parsed_args.name.title())) + "Charm",
            "workload_module": _make_workload_module_name(parsed_args.name),
        }

        template_directory = PROFILES[parsed_args.profile]
        env = get_templates_environment(template_directory)

        executables = [
            "run_tests",
            "src/charm.py",
            "tests/spread/lib/tools/retry",
            "spread/.extension",
        ]
        src_files = ["src/charm.py"]
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
            if path.name == "workload.py" and path.parent.name == "src":
                workload_module = context["workload_module"]
                workload_module_path = path.with_name(f"{workload_module}.py")
                path.rename(workload_module_path)
                src_files.append(f"src/{workload_module}.py")
        for line in _make_success_message(src_files).split("\n"):
            emit.message(line)
