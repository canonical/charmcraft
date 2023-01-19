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

"""Collection of creation functions for normally used objects for testing."""

import pathlib
import textwrap

from charmcraft.commands.store import create_importable_name, get_lib_info


def create_lib_filepath(charm_name, lib_name, api=0, patch=1, lib_id="test-lib-id"):
    """Helper to create the structures on disk for a given lib."""
    charm_name = create_importable_name(charm_name)
    base_dir = pathlib.Path("lib")
    lib_file = base_dir / "charms" / charm_name / "v{}".format(api) / "{}.py".format(lib_name)
    lib_file.parent.mkdir(parents=True, exist_ok=True)

    # save the content to that specific file under custom structure
    template = textwrap.dedent(
        """
        # test content for a library
        LIBID = "{lib_id}"
        LIBAPI = {api}
        LIBPATCH = {patch}

        # more text and python code...
    """
    )
    content = template.format(lib_id=lib_id, api=api, patch=patch)
    lib_file.write_text(content)

    # use get_lib_info to get the hash of the file, as the used hash is WITHOUT the metadata
    # files (no point in duplicating that logic here)
    libdata = get_lib_info(lib_path=lib_file)
    return content, libdata.content_hash
