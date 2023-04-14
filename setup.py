#!/usr/bin/env python3

# Copyright 2020-2022 Canonical Ltd.
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

from tools.version import determine_version

from setuptools import find_packages, setup

import charmcraft

with open("README.md", "rt", encoding="utf8") as fh:
    long_description = fh.read()

install_requires = [
    "craft-cli",
    "craft-parts",
    "craft-providers",
    "craft-store",
    "humanize>=2.6.0",
    "jsonschema",
    "jinja2",
    "pydantic",
    "python-dateutil",
    "pyyaml",
    "requests",
    "requests-toolbelt",
    "requests-unixsocket",
    "snap-helpers",
    "tabulate",
]

dev_requires = [
    "black",
    "coverage",
    "flake8",
    "pydocstyle",
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "pytest-check",
    "responses",
    "tox",
]

extras_require = {
    "dev": dev_requires,
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
