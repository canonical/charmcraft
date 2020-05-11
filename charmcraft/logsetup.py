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

"""Set up logging."""

import logging


_MODES = {
    'quiet': (logging.WARNING, "%(message)s"),
    'normal': (logging.INFO, "%(message)s"),
    'verbose': (logging.DEBUG, "%(asctime)s  %(name)-18s %(levelname)-8s %(message)s"),
}

_logger = logging.getLogger('charmcraft')
_logger.setLevel(logging.DEBUG)

_stdout_handler = logging.StreamHandler()
_logger.addHandler(_stdout_handler)


def configure(mode):
    """Set logging in different modes."""
    level, format_string = _MODES[mode]
    _stdout_handler.setFormatter(logging.Formatter(format_string))
    _stdout_handler.setLevel(level)
