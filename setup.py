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

from setuptools import find_packages, setup

from tools.version import determine_version

with open("README.md", encoding="utf8") as fh:
    long_description = fh.read()

install_requires = [
    "craft-application@git+https://github.com/canonical/craft-application.git@4c3162b6ec5bdc1b85227bd777dc0005415604d7",
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
    "pyright==1.1.332",
    "types-python-dateutil",
    "types-requests",
    "types-setuptools",
    "types-tabulate",
    "types-urllib3",
]

dev_requires = [
    "coverage",
    "flake8",
    "freezegun",
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
        "console_scripts": ["charmcraft = charmcraft.application.main:main"],
    },
    python_requires=">=3",
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,  # so we get templates in the wheel
)
