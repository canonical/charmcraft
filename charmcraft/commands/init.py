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

from datetime import date
import logging
import os
from pathlib import Path
import pwd
import re

from jinja2 import Environment, PackageLoader, StrictUndefined

from charmcraft.cmdbase import BaseCommand, CommandError
from ._utils import make_executable

logger = logging.getLogger(__name__)


class InitCommand(BaseCommand):
    """Initialize a directory to be a charm project."""
    name = "init"
    help_msg = "initialize a directory to be a charm project"

    def fill_parser(self, parser):
        parser.add_argument(
            "-d", "--directory", type=Path, default=Path("."),
            help="the directory to initialize. Must not exist or be empty; defaults to '.'")
        parser.add_argument(
            "--name", type=str,
            help="the name of the project; defaults to the directory name")

        parser.add_argument(
            "--author", type=str,
            help="the author of the project; defaults to the directory name;"
            " defaults to the current user's name as present in the GECOS field.")

    def run(self, args):
        args.directory = args.directory.resolve()
        if args.directory.exists():
            if not args.directory.is_dir():
                raise CommandError("{} is not a directory".format(args.directory))
            for _ in args.directory.iterdir():
                raise CommandError("{} is not empty".format(args.directory))
            logger.debug("Using existing project directory '%s'", args.directory)
        else:
            logger.debug("Creating project directory '%s'", args.directory)
            args.directory.mkdir()

        if args.author is None:
            gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(',', 1)[0]
            if not gecos:
                raise CommandError("Author not given, and nothing in GECOS field")
            logger.debug("Setting author to %r from GECOS field", gecos)
            args.author = gecos

        if not args.name:
            args.name = args.directory.name
            logger.debug("Set project name to '%s'", args.name)

        context = {
            "name": args.name,
            "author": args.author,
            "year": date.today().year,
            "class_name": "".join(re.split(r"\W+", args.name.title())) + "Charm",
        }

        env = Environment(
            loader=PackageLoader('charmcraft', 'templates/init'),
            autoescape=False,            # no need to escape things here :-)
            keep_trailing_newline=True,  # they're not text files if they don't end in newline!
            optimized=False,             # optimization doesn't make sense for one-offs
            undefined=StrictUndefined)   # fail on undefined

        # bare minimum:
        #  🗷 a req.txt w/ops,
        #  ☐ src/charm.py w/structure & xxx & a minimum hook & stored state
        #  ☐ a basic fixme test which pulls in the harness and tests that the minimum thing works
        #  🗷 a run_tests script & flake8
        #  🗷 a req-dev.txt w/flake8 (etc?)
        # maybe a templates directory, later :-)

        _xxx_rx = re.compile("XXX: (.*)")
        executables = ["run_tests", "src/charm.py"]
        for template_name in env.list_templates():
            if template_name.endswith(".pyc") or template_name.endswith("~"):
                # would be nice if we could stop from shipping these 🤷
                continue
            logger.debug("Rendering %s", template_name)
            template = env.get_template(template_name)
            path = args.directory / template_name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wt", encoding="utf8") as fh:
                out = template.render(context)
                fh.write(out)
                for xxx in _xxx_rx.findall(out):
                    logger.warning("%s: %s", template_name, xxx)
                if template_name in executables:
                    make_executable(fh)
                    logger.debug("  made executable")
