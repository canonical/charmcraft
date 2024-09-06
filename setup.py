#!/usr/bin/env python3

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
#
# For further info, check https://github.com/canonical/charmcraft

"""Setup script for Charmcraft."""

import subprocess

from setuptools import find_packages, setup


def determine_version():
    """Get the version of Charmcraft.

    Examples (git describe -> python package version):
    4.1.1-0-gad012482d -> 4.1.1
    4.1.1-16-g2d8943dbc -> 4.1.1.post16+g2d8943dbc

    For shallow clones or repositories missing tags:
    0ae7c04
    This was copied from tools/version.py to fix #1472
    """
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
    assert (  # noqa: S101
        len(split_desc) == 3
    ), f"Failed to parse Charmcraft git version description {desc!r}. Confirm that git repository is present and has the required tags/history."

    version = split_desc[0]
    distance = split_desc[1]
    commit = split_desc[2]

    if distance == "0":
        return version

    return f"{version}.post{distance}+git{commit[1:]}"


with open("README.md", encoding="utf8") as fh:
    long_description = fh.read()

install_requires = [
    "craft-cli>=2.3.0",
    "craft-parts>=1.18",
    "craft-providers",
    "craft-store>=2.4",
    "distro>=1.3.0",
    "humanize>=2.6.0",
    "jsonschema",
    "jinja2",
    "pydantic>=1.10,<2.0",
    "python-dateutil",
    "pyyaml",
    "requests",
    "requests-toolbelt",
    "requests-unixsocket",
    "snap-helpers",
    "tabulate",
    # Needed until requests-unixsocket supports urllib3 v2
    # https://github.com/msabramo/requests-unixsocket/pull/69
    "urllib3<2.0",
]

lint_requires = [
    "black>=23.10.1,<24.0.0",
    "codespell[tomli]>=2.2.6,<3.0.0",
    "ruff~=0.1.1",
    "yamllint>=1.32.0,<2.0.0",
]

type_requires = [
    "mypy[reports]~=1.5",
    "pyright==1.1.377",
    "types-python-dateutil",
    "types-requests",
    "types-setuptools",
    "types-tabulate",
    "types-urllib3",
]

dev_requires = [
    "coverage",
    "flake8",
    "pydocstyle",
    "pyfakefs",
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "pytest-check",
    "pytest-subprocess",
    "responses",
    "tox",
]
dev_requires += lint_requires + type_requires

extras_require = {
    "dev": dev_requires,
    "lint": lint_requires,
    "type": type_requires,
}


setup(
    name="charmcraft",
    version=determine_version(),
    author="Facundo Batista",
    author_email="facundo.batista@canonical.com",
    description="The main tool to build, upload, and develop in general the Juju charms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/canonical/charmcraft",
    license="Apache-2.0",
    packages=find_packages(include=["charmcraft", "charmcraft.*"]),
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    entry_points={
        "console_scripts": ["charmcraft = charmcraft.main:main"],
    },
    python_requires=">=3",
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,  # so we get templates in the wheel
)
