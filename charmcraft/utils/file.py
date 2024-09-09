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
"""File-related utilities."""
import io
import os
import pathlib
import zipfile
from _stat import S_IRGRP, S_IROTH, S_IRUSR, S_IXGRP, S_IXOTH, S_IXUSR

from craft_cli import CraftError

# handy masks for execution and reading for everybody
S_IXALL = S_IXUSR | S_IXGRP | S_IXOTH
S_IRALL = S_IRUSR | S_IRGRP | S_IROTH

PathOrString = os.PathLike | str


def make_executable(fh: io.IOBase) -> None:
    """Make open file fh executable.

    :param fh: An open file object.
    """
    fileno = fh.fileno()
    mode = os.fstat(fileno).st_mode
    mode_r = mode & S_IRALL
    mode_x = mode_r >> 2
    mode = mode | mode_x
    os.fchmod(fileno, mode)


def useful_filepath(filepath: PathOrString) -> pathlib.Path:
    """Return a valid Path with username expansion for filepath.

    CraftError is raised if filepath is not a valid file or is not readable.
    """
    filepath = pathlib.Path(filepath).expanduser()
    if not os.access(filepath, os.R_OK):
        raise CraftError(f"Cannot access {str(filepath)!r}.")
    if not filepath.is_file():
        raise CraftError(f"{str(filepath)!r} is not a file.")
    return filepath


def build_zip(zip_path: PathOrString, prime_dir: PathOrString) -> None:
    """Build a zip file from a prime directory.

    :param zip_path: The path to the output zip file
    :param prime_dir: The path to the directory to zip.
    """
    zip_path = pathlib.Path(zip_path).resolve()
    prime_dir = pathlib.Path(prime_dir).resolve()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Using os.walk() because Path.walk() is only added in 3.12
        for dir_path_str, _, filenames in os.walk(prime_dir, followlinks=True):
            for filename in filenames:
                file_path = pathlib.Path(dir_path_str, filename)
                zip_file.write(file_path, file_path.relative_to(prime_dir))
