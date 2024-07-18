# Copyright 2023-2024 Canonical Ltd.
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
import os
import pathlib
from dataclasses import dataclass
from typing import overload

import yaml
from craft_cli import CraftError

from charmcraft import const, errors


@dataclass(frozen=True)
class LibData:
    """All data fields for a library, including external ones."""

    lib_id: str | None
    api: int
    patch: int
    content: str | None
    content_hash: str | None
    full_name: str
    path: pathlib.Path
    lib_name: str
    charm_name: str


@dataclass
class LibInternals:
    """All internals from a lib: the metadata fields, the hash and the content itself."""

    lib_id: str
    api: int
    patch: int
    pydeps: list[str]
    content_hash: str
    content: str


def get_name_from_metadata() -> str | None:
    """Return the name if present and plausible in metadata.yaml."""
    try:
        with open(const.METADATA_FILENAME, "rb") as fh:
            metadata = yaml.safe_load(fh)
        charm_name = metadata["name"]
    except (yaml.error.YAMLError, OSError, KeyError):
        return None
    return charm_name


def create_importable_name(charm_name: str) -> str:
    """Convert a charm name to something that is importable in python."""
    return charm_name.replace("-", "_")


def create_charm_name_from_importable(charm_name: str) -> str:
    """Convert a charm name from the importable form to the real form."""
    # _ is invalid in charm names, so we know it's intended to be '-'
    return charm_name.replace("_", "-")


def get_lib_internals(lib_path: pathlib.Path) -> LibInternals:
    """Get content, its hash, and all the metadata fields from a library.

    There are two kind of metadata fields, simple constant fields and PYDEPS. The simple
    constant fields are also the mandatory ones: LIBAPI, LIBPATCH and LIBID.
    """
    content = lib_path.read_text(encoding="utf8")
    try:
        tree = ast.parse(content)
    except Exception:
        raise CraftError(f"Failed to parse Python library {str(lib_path)!r}")

    def _api_patch_validator(value):
        return isinstance(value, int) and value >= 0

    _msg_prefix = f"Library {str(lib_path)!r} metadata field "
    simple_fields = {
        "LIBAPI": (
            _api_patch_validator,
            _msg_prefix + "LIBAPI must be a constant assignment of zero or a positive integer.",
        ),
        "LIBPATCH": (
            _api_patch_validator,
            _msg_prefix + "LIBPATCH must be a constant assignment of zero or a positive integer.",
        ),
        "LIBID": (
            lambda value: isinstance(value, str) and value and value.isascii(),
            _msg_prefix + "LIBID must be a constant assignment of a non-empty ASCII string.",
        ),
    }
    pydeps_error = _msg_prefix + "PYDEPS must be a constant list of non-empty strings"

    # walk the AST "first layer", find assignments to the key fields and validate them
    metadata = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in (n for n in node.targets if isinstance(n, ast.Name)):
                if target.id in simple_fields:
                    validator, error_msg = simple_fields[target.id]
                    if not isinstance(node.value, ast.Constant):
                        raise CraftError(error_msg)
                    real_value = node.value.value
                    if not validator(real_value):
                        raise CraftError(error_msg)
                    metadata[target.id] = real_value
                elif target.id == "PYDEPS":
                    if not isinstance(node.value, ast.List):
                        raise CraftError(pydeps_error)
                    metadata["PYDEPS"] = pydeps = []
                    for item in node.value.elts:
                        if not isinstance(item, ast.Constant):
                            raise CraftError(pydeps_error)
                        value = item.value
                        if not isinstance(value, str) or not value:
                            raise CraftError(pydeps_error)
                        pydeps.append(value)

    # extra verifications for cases that need to consider more than the individual fields
    mandatory_missing = set(simple_fields) - set(metadata)
    if mandatory_missing:
        joined = ", ".join(sorted(mandatory_missing))
        raise CraftError(
            f"Library {str(lib_path)!r} is missing the mandatory metadata fields: {joined}."
        )
    if metadata["LIBAPI"] == 0 and metadata["LIBPATCH"] == 0:
        raise CraftError(
            f"Library {str(lib_path)!r} metadata fields LIBAPI and LIBPATCH cannot both be zero."
        )

    # hash the file excluding those lines where appear keys used for version control
    metadata_vcs_fields = (b"LIBAPI", b"LIBPATCH", b"LIBID")
    hasher = hashlib.sha256()
    with lib_path.open("rb") as fh:
        for line in fh:
            # always use \n as newline for users to have the same
            # file hash both in Linux and Windows
            line = line.replace(b"\r\n", b"\n")
            if not line.startswith(metadata_vcs_fields):
                hasher.update(line)
    content_hash = hasher.hexdigest()

    return LibInternals(
        lib_id=metadata["LIBID"],
        api=metadata["LIBAPI"],
        patch=metadata["LIBPATCH"],
        pydeps=metadata.get("PYDEPS", []),
        content_hash=content_hash,
        content=content,
    )


def get_lib_path(charm: str, lib_name: str, api: int) -> pathlib.Path:
    """Get a relative path for a library based on its home charm, name and API version.

    :param charm: The name of the charm that owns this library
    :param lib_name: The name of the library
    :param api: The API version of the library
    :returns: A relative path to the library python file.
    """
    return (
        pathlib.Path("lib/charms") / create_importable_name(charm) / f"v{api}" / f"{lib_name}.py"
    )


def get_lib_module_name(charm: str, lib_name: str, api: int) -> str:
    """Get a Python module path for a library based on its home charm, name and API version.

    :param charm: The name of the charm that owns this library
    :param lib_name: The name of the library
    :param api: The API version of the library
    :returns: A string of the full path to the charm.
    """
    return f"charms.{create_importable_name(charm)}.v{api}.{lib_name}"


@overload
def get_lib_info(*, full_name: str) -> LibData: ...
@overload
def get_lib_info(*, lib_path: pathlib.Path) -> LibData: ...
def get_lib_info(*, full_name: str | None = None, lib_path: pathlib.Path | None = None) -> LibData:
    """Get the whole lib info from the path/file.

    This will perform mutation of the charm name to create importable paths.
    * `charm_name` and `libdata.charm_name`: `foo-bar`
    * `full_name` and `libdata.full_name`: `charms.foo_bar.v0.somelib`
    * paths, including `libdata.path`: `lib/charms/foo_bar/v0/somelib`

    This function needs to be called standing on the root directory of the project.
    """
    if lib_path:
        # get it from the lib_path
        try:
            libsdir, charmsdir, importable_charm_name, v_api = lib_path.parts[:-1]
        except ValueError:
            raise errors.BadLibraryPathError(lib_path)
        if libsdir != "lib" or charmsdir != "charms" or lib_path.suffix != ".py":
            raise errors.BadLibraryPathError(lib_path)
        full_name = ".".join((charmsdir, importable_charm_name, v_api, lib_path.stem))
    elif full_name:
        # build the path! convert a lib name with dots to the full path, including lib
        # dir and Python extension.
        #    e.g.: charms.mycharm.v4.foo -> lib/charms/mycharm/v4/foo.py
        try:
            charmsdir, charm_name, v_api, libfile = full_name.split(".")
        except ValueError:
            raise errors.BadLibraryNameError(full_name)

        # the lib full_name includes the charm_name which might not be importable (dashes)
        importable_charm_name = create_importable_name(charm_name)

        if charmsdir != "charms":
            raise errors.BadLibraryNameError(full_name)
        path = pathlib.Path("lib")
        lib_path = path / charmsdir / importable_charm_name / v_api / (libfile + ".py")
    else:
        raise TypeError("get_lib_info needs either a full name or a lib path")

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

    internals = get_lib_internals(lib_path)

    # validate internal API matches with what was used in the path
    if internals.api != api_from_path:
        raise CraftError(
            f"Library {str(lib_path)!r} metadata field LIBAPI is different from the version in the path."
        )

    return LibData(
        lib_id=internals.lib_id,
        api=internals.api,
        patch=internals.patch,
        content_hash=internals.content_hash,
        content=internals.content,
        full_name=full_name,
        path=lib_path,
        lib_name=lib_name,
        charm_name=charm_name,
    )


def get_libs_from_tree(
    charm_name: str | None = None, root: pathlib.Path | None = None
) -> list[LibData]:
    """Get library info from the directories tree (for a specific charm if specified).

    It only follows/uses the directories/files for a correct charmlibs
    disk structure.

    This can take charm_name as both importable and normal form.
    """
    local_libs_data = []

    current_directory = os.getcwd()
    if root is not None:
        os.chdir(root)
    try:
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
    finally:
        os.chdir(current_directory)
    return local_libs_data


def collect_charmlib_pydeps(basedir: pathlib.Path) -> set[str]:
    """Collect the Python dependencies from all the project's charm libraries."""
    all_libs_data = get_libs_from_tree(root=basedir)
    charmlib_deps = set()
    for libdata in all_libs_data:
        internals = get_lib_internals(basedir / libdata.path)
        charmlib_deps.update(internals.pydeps)
    return charmlib_deps
