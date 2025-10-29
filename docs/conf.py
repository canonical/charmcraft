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
ogp_site_url = "https://documentation.ubuntu.com/charmcraft/"
ogp_site_name = project
ogp_image = "https://assets.ubuntu.com/v1/253da317-image-document-ubuntudocs.svg"

slug = "charmcraft"

html_context = {
    "product_page": "juju.is",
    "product_tag": "_static/assets/juju-logo-no-text.png",
    "github_url": "https://github.com/canonical/charmcraft",
    "github_issues": "https://github.com/canonical/charmcraft/issues",
    "discourse": "https://discourse.charmhub.io",
    "matrix": "https://matrix.to/#/#charmhub-charmcraft:ubuntu.com",
}

# Target repository for the edit button on pages
html_theme_options = {
    "source_edit_link": "https://github.com/canonical/charmcraft",
}

# Sitemap configuration: https://sphinx-sitemap.readthedocs.io/
html_baseurl = "https://documentation.ubuntu.com/charmcraft/"

if "READTHEDOCS_VERSION" in os.environ:
    version = os.environ["READTHEDOCS_VERSION"]
    sitemap_url_scheme = "{version}{link}"
else:
    sitemap_url_scheme = "latest/{link}"

# Template and asset locations
extensions = [
    "canonical_sphinx",
    "pydantic_kitbash",
    "sphinx_sitemap",
    "sphinx_substitution_extensions",
]

# Copy extra files to the _static dir during build
html_static_path = ["_static"]
templates_path = ["_templates"]

# Files for the cookie banner
html_css_files = [
    'css/cookie-banner.css'
]

html_js_files = [
    'js/bundle.js',
]

# endregion

# region General configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions.extend(
    [
        "sphinx.ext.ifconfig",
        "sphinx.ext.intersphinx",
        "sphinx.ext.viewcode",
        "sphinx.ext.coverage",
        "sphinx.ext.doctest",
        "sphinx_toolbox",
        "sphinx_toolbox.more_autodoc",
        "sphinx.ext.autodoc",  # Must be loaded after more_autodoc
        "sphinxcontrib.details.directive",
        "sphinx_toolbox.collapse",
        "sphinxcontrib.details.directive",
        "sphinx.ext.napoleon",
        "sphinx_autodoc_typehints",  # must be loaded after napoleon
        "sphinxext.rediraffe",
    ]
)

# endregion

exclude_patterns = [
    # Workaround for https://github.com/canonical/pydantic-kitbash/issues/49
    "common/craft-parts/reference/part_properties.rst",

    "_build",
    "Thumbs.db",
    ".DS_Store",
    "env",
    "sphinx-starter-pack",
    # Excluded here because they are either included explicitly in other
    # documents (so they generate "duplicate label" errors) or they aren't
    # used in this documentation at all (so they generate "unreferenced"
    # errors).
    "common/craft-parts/explanation/lifecycle.rst",
    "common/craft-parts/explanation/overlay_parameters.rst",
    "common/craft-parts/explanation/overlays.rst",
    "common/craft-parts/explanation/parts.rst",
    "common/craft-parts/explanation/how_parts_are_built.rst",
    "common/craft-parts/explanation/dump_plugin.rst",
    "common/craft-parts/explanation/file-migration.rst",
    "common/craft-parts/explanation/gradle_plugin.rst",
    "common/craft-parts/explanation/overlay_step.rst",
    "common/craft-parts/how-to/craftctl.rst",
    "common/craft-parts/how-to/customise-the-build-with-craftctl.rst",
    "common/craft-parts/how-to/include_files.rst",
    "common/craft-parts/how-to/use_parts.rst",
    "common/craft-parts/how-to/override_build.rst",
    "common/craft-parts/reference/partition_specific_output_directory_variables.rst",
    "common/craft-parts/reference/step_output_directories.rst",
    "common/craft-parts/reference/plugins/ant_plugin.rst",
    "common/craft-parts/reference/plugins/autotools_plugin.rst",
    "common/craft-parts/reference/plugins/cargo_use_plugin.rst",
    "common/craft-parts/reference/plugins/cmake_plugin.rst",
    "common/craft-parts/reference/plugins/dotnet_plugin.rst",
    "common/craft-parts/reference/plugins/dotnet_v2_plugin.rst",
    "common/craft-parts/reference/plugins/go_plugin.rst",
    "common/craft-parts/reference/plugins/gradle_plugin.rst",
    "common/craft-parts/reference/plugins/jlink_plugin.rst",
    "common/craft-parts/reference/plugins/make_plugin.rst",
    "common/craft-parts/reference/plugins/maven_plugin.rst",
    "common/craft-parts/reference/plugins/maven_use_plugin.rst",
    "common/craft-parts/reference/plugins/meson_plugin.rst",
    "common/craft-parts/reference/plugins/npm_plugin.rst",
    "common/craft-parts/reference/plugins/poetry_plugin.rst",
    "common/craft-parts/reference/plugins/python_plugin.rst",
    "common/craft-parts/reference/plugins/qmake_plugin.rst",
    "common/craft-parts/reference/plugins/rust_plugin.rst",
    "common/craft-parts/reference/plugins/scons_plugin.rst",
    "common/craft-parts/reference/plugins/go_plugin.rst",
    "common/craft-parts/reference/plugins/go_use_plugin.rst",
    "common/craft-parts/reference/plugins/uv_plugin.rst",
    # Extra non-craft-parts exclusions can be added after this comment
    "reuse/reference/extensions/integrations.rst",
    "reuse/reference/extensions/environment_variables.rst",
    "reuse/reference/extensions/environment_variables_spring_boot.rst",
    "reuse/tutorial/*"
]

rst_epilog = """
.. include:: /reuse/links.txt
"""

# MyST-specific settings

suppress_warnings = ["myst.domains"]  # Suppresses false warnings about missing methods
myst_heading_anchors = 4  # Autogenerates anchors for MD headings

autodoc_default_options = {"exclude-members": "model_post_init"}

# region Options for extensions
# Intersphinx extension
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "craft-parts": ("https://canonical-craft-parts.readthedocs-hosted.com/en/latest/", None),
    "juju": ("https://documentation.ubuntu.com/juju/3.6/", None),
    "ops": ("https://documentation.ubuntu.com/ops/latest/", None),
    "rockcraft": ("https://documentation.ubuntu.com/rockcraft/stable/", None),
    "12-factor": ("https://canonical-12-factor-app-support.readthedocs-hosted.com/latest/", None),
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

# Client-side page redirects.
rediraffe_redirects = "redirects.txt"

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
    gen_cli_docs_path = (project_dir / "tools/gen_cli_docs.py").resolve()
    subprocess.run([sys.executable, gen_cli_docs_path, project_dir / "docs"], check=True)


def setup(app):
    app.connect("builder-inited", generate_cli_docs)


# Setup libraries documentation snippets for use in charmcraft docs.
common_docs_path = pathlib.Path(__file__).parent / "common"
craft_parts_docs_path = pathlib.Path(craft_parts_docs.__file__).parent / "craft-parts"
(common_docs_path / "craft-parts").unlink(missing_ok=True)
(common_docs_path / "craft-parts").symlink_to(craft_parts_docs_path, target_is_directory=True)
