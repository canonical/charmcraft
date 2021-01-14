#!/usr/bin/env python3

# Copyright 2020-2021 Canonical Ltd.
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

from pathlib import Path
from textwrap import dedent
from setuptools import setup

import charmcraft


with open("README.md", "rt", encoding='utf8') as fh:
    long_description = fh.read()

with open("requirements.txt", "rt", encoding='utf8') as fh:
    requirements = fh.read().split('\n')

version_path = Path("charmcraft/version.py")
version_backup = Path("charmcraft/version.py~")
version_path.rename(version_backup)
try:
    with version_path.open("wt", encoding="utf8") as fh:
        fh.write(dedent('''
            # this is a generated file

            version = {!r}
            ''').format(charmcraft.__version__))

    setup(
        name="charmcraft",
        version=charmcraft.__version__,
        author="Facundo Batista",
        author_email="facundo.batista@canonical.com",
        description="The main tool to build, upload, and develop in general the Juju charms.",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/canonical/charmcraft",
        license="Apache-2.0",
        packages=['charmcraft', 'charmcraft.commands', 'charmcraft.commands.store'],
        classifiers=[
            "Environment :: Console",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
        ],
        entry_points={
            'console_scripts': ["charmcraft = charmcraft.main:main"],
        },
        python_requires='>=3',
        install_requires=requirements,
        include_package_data=True,  # so we get templates in the wheel
    )

finally:
    version_backup.rename(version_path)
