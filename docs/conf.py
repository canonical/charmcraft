# This file is part of charmcraft.
#
# Copyright 2024 Canonical Ltd.
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

import datetime
import os
import pathlib
import subprocess
import sys

import craft_parts_docs

import charmcraft

project_dir = pathlib.Path(__file__).parents[1].resolve()

project = "Charmcraft"
author = "Canonical"
release = charmcraft.__version__
if ".post" in release:
    # The commit hash in the dev release version confuses the spellchecker
    release = "dev"

copyright = "2023-%s, %s" % (datetime.date.today().year, author)

# region Configuration for canonical-sphinx
ogp_site_url = "https://canonical-charmcraft.readthedocs-hosted.com/"
ogp_site_name = project
ogp_image = "https://assets.ubuntu.com/v1/253da317-image-document-ubuntudocs.svg"

html_context = {
    "product_page": "github.com/canonical/charmcraft",
    "github_url": "https://github.com/canonical/charmcraft",
    "discourse": "https://discourse.charmhub.io",
}

extensions = [
    "canonical_sphinx",
]
# endregion

# region General configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions.extend(
    [
        "sphinx.ext.intersphinx",
        "sphinx.ext.viewcode",
        "sphinx.ext.coverage",
        "sphinx.ext.doctest",
        "sphinx-pydantic",
        "sphinx_toolbox",
        "sphinx_toolbox.more_autodoc",
        "sphinx.ext.autodoc",  # Must be loaded after more_autodoc
        "sphinx_autodoc_typehints",  # must be loaded after napoleon
        "sphinxcontrib.details.directive",
        "sphinx_toolbox.collapse",
        "sphinxcontrib.autodoc_pydantic",
    ]
)

# endregion

autodoc_default_options = {"exclude-members": "model_post_init"}

# region Options for extensions
# Intersphinx extension
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "craft-parts": ("https://canonical-craft-parts.readthedocs-hosted.com/en/latest/", None),
}
# See also:
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#confval-intersphinx_disabled_reftypes
intersphinx_disabled_reftypes = ["*"]

# Type hints configuration
set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = True

# Github config
github_username = "canonical"
github_repository = "charmcraft"

html_domain_indices = True

# endregion

# Setup libraries documentation snippets for use in charmcraft docs.
# TODO: This needs a craft-parts update first.
# common_docs_path = pathlib.Path(__file__).parent / "common"
# craft_parts_docs_path = pathlib.Path(craft_parts_docs.__file__).parent / "craft-parts"
# (common_docs_path / "craft-parts").unlink(missing_ok=True)
# (common_docs_path / "craft-parts").symlink_to(
#     craft_parts_docs_path, target_is_directory=True
# )


def generate_cli_docs(nil):
    gen_cli_docs_path = (project_dir / "tools" / "gen_cli_docs.py").resolve()
    subprocess.run([sys.executable, gen_cli_docs_path, project_dir / "docs"], check=True)


def setup(app):
    app.connect("builder-inited", generate_cli_docs)
