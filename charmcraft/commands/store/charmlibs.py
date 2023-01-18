# Copyright 2023 Canonical Ltd.
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
"""General purpose library functions for charmcraft."""
import ast
import hashlib
import pathlib
from collections import namedtuple
from typing import AnyStr, Optional

import yaml
from craft_cli import CraftError, emit

from charmcraft.errors import BadLibraryPathError, BadLibraryNameError

LibData = namedtuple(
    "LibData",
    "lib_id api patch content content_hash full_name path lib_name charm_name",
)


def get_positive_int(raw_value: AnyStr) -> int:
    """Convert the raw value for api/patch into a positive integer."""
    value = int(raw_value)
    if value < 0:
        raise ValueError("Version numbers cannot be negative.")
    return value


def get_name_from_metadata() -> Optional[str]:
    """Return the name if present and plausible in metadata.yaml."""
    try:
        with open("metadata.yaml", "rb") as fh:
            metadata = yaml.safe_load(fh)
        charm_name = metadata["name"]
    except (yaml.error.YAMLError, OSError, KeyError):
        return
    return charm_name


def create_importable_name(charm_name: str) -> str:
    """Convert a charm name to something that is importable in python."""
    return charm_name.replace("-", "_")


def create_charm_name_from_importable(charm_name: str) -> str:
    """Convert a charm name from the importable form to the real form."""
    # _ is invalid in charm names, so we know it's intended to be '-'
    return charm_name.replace("_", "-")


def get_lib_info(*, full_name=None, lib_path=None):
    """Get the whole lib info from the path/file.

    This will perform mutation of the charm name to create importable paths.
    * `charm_name` and `libdata.charm_name`: `foo-bar`
    * `full_name` and `libdata.full_name`: `charms.foo_bar.v0.somelib`
    * paths, including `libdata.path`: `lib/charms/foo_bar/v0/somelib`

    """
    if full_name is None:
        # get it from the lib_path
        try:
            libsdir, charmsdir, importable_charm_name, v_api = lib_path.parts[:-1]
        except ValueError:
            raise BadLibraryPathError(lib_path)
        if libsdir != "lib" or charmsdir != "charms" or lib_path.suffix != ".py":
            raise BadLibraryPathError(lib_path)
        full_name = ".".join((charmsdir, importable_charm_name, v_api, lib_path.stem))

    else:
        # build the path! convert a lib name with dots to the full path, including lib
        # dir and Python extension.
        #    e.g.: charms.mycharm.v4.foo -> lib/charms/mycharm/v4/foo.py
        try:
            charmsdir, charm_name, v_api, libfile = full_name.split(".")
        except ValueError:
            raise BadLibraryNameError(full_name)

        # the lib full_name includes the charm_name which might not be importable (dashes)
        importable_charm_name = create_importable_name(charm_name)

        if charmsdir != "charms":
            raise BadLibraryNameError(full_name)
        path = pathlib.Path("lib")
        lib_path = path / charmsdir / importable_charm_name / v_api / (libfile + ".py")

    # charm names in the path can contain '_' to be importable
    # these should be '-', so change them back
    charm_name = create_charm_name_from_importable(importable_charm_name)

    if v_api[0] != "v" or not v_api[1:].isdigit():
        raise CraftError("The API version in the library path must be 'vN' where N is an integer.")
    api_from_path = int(v_api[1:])

    lib_name = lib_path.stem
    if not lib_path.exists():
        return LibData(
            lib_id=None,
            api=api_from_path,
            patch=-1,
            content_hash=None,
            content=None,
            full_name=full_name,
            path=lib_path,
            lib_name=lib_name,
            charm_name=charm_name,
        )

    # parse the file and extract metadata from it, while hashing
    metadata_fields = (b"LIBAPI", b"LIBPATCH", b"LIBID")
    metadata = dict.fromkeys(metadata_fields)
    hasher = hashlib.sha256()
    with lib_path.open("rb") as fh:
        for line in fh:
            if line.startswith(metadata_fields):
                try:
                    field, value = [x.strip() for x in line.split(b"=")]
                except ValueError:
                    raise CraftError(
                        "Bad metadata line in {!r}: {!r}".format(str(lib_path), line)
                    ) from None
                metadata[field] = value
            else:
                hasher.update(line)

    missing = [k.decode("ascii") for k, v in metadata.items() if v is None]
    if missing:
        raise CraftError(
            "Library {!r} is missing the mandatory metadata fields: {}.".format(
                str(lib_path), ", ".join(sorted(missing))
            )
        )

    bad_api_patch_msg = "Library {!r} metadata field {} is not zero or a positive integer."
    try:
        libapi = get_positive_int(metadata[b"LIBAPI"])
    except ValueError:
        raise CraftError(bad_api_patch_msg.format(str(lib_path), "LIBAPI"))
    try:
        libpatch = get_positive_int(metadata[b"LIBPATCH"])
    except ValueError:
        raise CraftError(bad_api_patch_msg.format(str(lib_path), "LIBPATCH"))

    if libapi == 0 and libpatch == 0:
        raise CraftError(
            "Library {!r} metadata fields LIBAPI and LIBPATCH cannot both be zero.".format(
                str(lib_path)
            )
        )

    if libapi != api_from_path:
        raise CraftError(
            "Library {!r} metadata field LIBAPI is different from the version in the path.".format(
                str(lib_path)
            )
        )

    bad_libid_msg = "Library {!r} metadata field LIBID must be a non-empty ASCII string."
    try:
        libid = ast.literal_eval(metadata[b"LIBID"].decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        raise CraftError(bad_libid_msg.format(str(lib_path)))
    if not libid or not isinstance(libid, str):
        raise CraftError(bad_libid_msg.format(str(lib_path)))

    content_hash = hasher.hexdigest()
    content = lib_path.read_text()

    return LibData(
        lib_id=libid,
        api=libapi,
        patch=libpatch,
        content_hash=content_hash,
        content=content,
        full_name=full_name,
        path=lib_path,
        lib_name=lib_name,
        charm_name=charm_name,
    )


def get_libs_from_tree(charm_name=None):
    """Get library info from the directories tree (for a specific charm if specified).

    It only follows/uses the directories/files for a correct charmlibs
    disk structure.

    This can take charm_name as both importable and normal form.
    """
    local_libs_data = []

    if charm_name is None:
        base_dir = pathlib.Path("lib") / "charms"
        charm_dirs = sorted(base_dir.iterdir()) if base_dir.is_dir() else []
    else:
        importable_charm_name = create_importable_name(charm_name)
        base_dir = pathlib.Path("lib") / "charms" / importable_charm_name
        charm_dirs = [base_dir] if base_dir.is_dir() else []

    for charm_dir in charm_dirs:
        for v_dir in sorted(charm_dir.iterdir()):
            if v_dir.is_dir() and v_dir.name[0] == "v" and v_dir.name[1:].isdigit():
                for libfile in sorted(v_dir.glob("*.py")):
                    local_libs_data.append(get_lib_info(lib_path=libfile))

    found_libs = [lib_data.full_name for lib_data in local_libs_data]
    emit.debug(f"Libraries found under {str(base_dir)!r}: {found_libs}")
    return local_libs_data
