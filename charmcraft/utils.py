# Copyright 2020-2021 Canonical Ltd.
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

"""Collection of utilities for charmcraft."""

import logging
import os
import pathlib
from stat import S_IXUSR, S_IXGRP, S_IXOTH, S_IRUSR, S_IRGRP, S_IROTH

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined

logger = logging.getLogger('charmcraft.commands')


# handy masks for execution and reading for everybody
S_IXALL = S_IXUSR | S_IXGRP | S_IXOTH
S_IRALL = S_IRUSR | S_IRGRP | S_IROTH


def make_executable(fh):
    """Make open file fh executable."""
    fileno = fh.fileno()
    mode = os.fstat(fileno).st_mode
    mode_r = mode & S_IRALL
    mode_x = mode_r >> 2
    mode = mode | mode_x
    os.fchmod(fileno, mode)


def load_yaml(fpath):
    """Return the content of a YAML file."""
    if not fpath.is_file():
        logger.debug("Couldn't find config file %s", fpath)
        return
    try:
        with fpath.open('rb') as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        logger.error("Failed to read/parse config file %s: %r", fpath, err)
        return
    return content


def get_templates_environment(templates_dir):
    """Create and return a Jinja environment to deal with the templates."""
    env = Environment(
        loader=PackageLoader('charmcraft', 'templates/{}'.format(templates_dir)),
        autoescape=False,            # no need to escape things here :-)
        keep_trailing_newline=True,  # they're not text files if they don't end in newline!
        optimized=False,             # optimization doesn't make sense for one-offs
        undefined=StrictUndefined)   # fail on undefined
    return env


class SingleOptionEnsurer:
    """Argparse helper to ensure that the option is specified only once, converting it properly.

    Receives a callable to convert the string from command line to the desired object.

    Example of use:

        parser.add_argument('-n', '--number',  type=SingleOptionEnsurer(int), required=True)

    No lower limit is checked, that is verified with required=True in the argparse definition.
    """

    def __init__(self, converter):
        self.converter = converter
        self.count = 0

    def __call__(self, value):
        """Run by argparse to validate and convert the given argument."""
        self.count += 1
        if self.count > 1:
            raise ValueError("the option can be specified only once")
        return self.converter(value)


def useful_filepath(filepath):
    """Convert the string to Path and verify that is a useful file path.

    It checks that the file exists and it's readable, and that it's actually a
    file. Also the `~` is expanded to the user's home.
    """
    filepath = pathlib.Path(filepath).expanduser()
    if not os.access(str(filepath), os.R_OK):  # access doesn't support pathlib in 3.5
        raise ValueError("Cannot access {!r}.".format(str(filepath)))
    if not filepath.is_file():
        raise ValueError("{!r} is not a file.".format(str(filepath)))
    return filepath
