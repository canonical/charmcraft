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
import os
from stat import S_IXUSR, S_IXGRP, S_IXOTH, S_IRUSR, S_IRGRP, S_IROTH

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined

logger = logging.getLogger('charmcraft.commands')


# handy masks for execution and reading for everybody
S_IXALL = S_IXUSR | S_IXGRP | S_IXOTH
S_IRALL = S_IRUSR | S_IRGRP | S_IROTH


def make_executable(fh):
    """make open file fh executable"""
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
        logger.error("Failed to read/parse config file %s (got %r)", fpath, err)
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
