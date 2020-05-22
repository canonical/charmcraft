#!/usr/bin/env python3

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

import ast
import setuptools


def get_version():
    """Extract the version string from project's init."""
    with open("charmcraft/__init__.py", "rt", encoding='utf8') as fh:
        for line in fh:
            if '__version__' in line:
                return ast.literal_eval(line.split('=', 1)[1].strip())


with open("README.md", "rt", encoding='utf8') as fh:
    long_description = fh.read()

with open("requirements.txt", "rt", encoding='utf8') as fh:
    requirements = fh.read().split('\n')

setuptools.setup(
    name="charmcraft",
    version=get_version(),
    author="Facundo Batista",
    author_email="facundo.batista@canonical.com",
    description="The main tool to build, upload, and develop in general the Juju charms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/canonical/charmcraft",
    license="Apache-2.0",
    packages=["charmcraft"],
    package_data={'': ["LICENSE", "README.md", "requirements.txt"]},
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    entry_points={
        'console_scripts': ["charmcraft = charmcraft:main"],
    },
    python_requires='>=3',
    install_requires=requirements,
)
