# Copyright 2020-2023 Canonical Ltd.
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

"""Manage the charmcraft tool versioning."""

import fileinput
import pathlib
import subprocess
import sys


def determine_version():
    # Examples (git describe -> python package version):
    # 4.1.1-0-gad012482d -> 4.1.1
    # 4.1.1-16-g2d8943dbc -> 4.1.1.post16+g2d8943dbc
    #
    # For shallow clones or repositories missing tags:
    # 0ae7c04

    desc = (
        subprocess.run(
            ["git", "describe", "--always", "--long"],
            check=True,
            stdout=subprocess.PIPE,
        )
        .stdout.decode()
        .strip()
    )

    split_desc = desc.split("-")
    assert (
        len(split_desc) == 3
    ), f"Failed to parse Charmcraft git version description {desc!r}. Confirm that git repository is present and has the required tags/history."

    version = split_desc[0]
    distance = split_desc[1]
    commit = split_desc[2]

    if distance == "0":
        return version

    return f"{version}.post{distance}+git{commit[1:]}"


def set_charmcraft_iss():
    charmcraft_iss_path = pathlib.Path("windows/charmcraft.iss")
    assert (
        charmcraft_iss_path.exists()
    ), f"Run from project root and ensure {charmcraft_iss_path!s} exists."
    with fileinput.input(str(charmcraft_iss_path), inplace=True) as iss_file:
        for line in iss_file:
            if line.startswith("AppVersion="):
                print(f"AppVersion={determine_version()}")
            else:
                print(line, end="")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "set-charmcraft-iss":
        set_charmcraft_iss()
    else:
        print(determine_version())
