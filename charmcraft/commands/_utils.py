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

import os
from stat import S_IXUSR, S_IXGRP, S_IXOTH

S_IXALL = S_IXUSR | S_IXGRP | S_IXOTH


def make_executable(fh):
    """make open file fh executable"""
    fileno = fh.fileno()
    os.fchmod(fileno, os.fstat(fileno).st_mode | S_IXALL)
