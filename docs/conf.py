import datetime
import os
import pathlib
import subprocess
import sys

import craft_parts_docs

import charmcraft

# Configuration for the Sphinx documentation builder.
# All configuration specific to your project should be done in this file.
#
# A complete list of built-in Sphinx configuration values:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#
# Our starter pack uses the custom Canonical Sphinx extension
# to keep all documentation based on it consistent and on brand:
# https://github.com/canonical/canonical-sphinx


#######################
# Project information #
#######################

# Project name
project = "Charmcraft"
author = "Canonical"

# Sidebar documentation title; best kept reasonably short
# The full version, including alpha/beta/rc tags
release = charmcraft.__version__
# The commit hash in the dev release version confuses the spellchecker
if ".post" in release:
    release = "dev"

html_title = project + " documentation"

# Copyright string; shown at the bottom of the page
copyright = "2023-%s, %s" % (datetime.date.today().year, author)

# Documentation website URL
ogp_site_url = "https://documentation.ubuntu.com/charmcraft/"

# Preview name of the documentation website
ogp_site_name = project

# Preview image URL
#
# TODO: To customise the preview image, update as needed.
ogp_image = "https://assets.ubuntu.com/v1/cc828679-docs_illustration.svg"

# Product favicon; shown in bookmarks, browser tabs, etc.
# html_favicon = '.sphinx/_static/favicon.png'

# Dictionary of values to pass into the Sphinx context for all pages:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_context
html_context = {
    # Product page URL; can be different from product docs URL
    "product_page": "juju.is",
    # Product tag image; the orange part of your logo, shown in the page header
    "product_tag": "_static/assets/juju-logo-no-text.png",
    "discourse": "https://discourse.charmhub.io",
    # Your Mattermost channel URL
    # "mattermost": "https://chat.canonical.com/canonical/channels/documentation",
    # Your Matrix channel URL
    "matrix": "https://matrix.to/#/#charmhub-charmcraft:ubuntu.com",
    # Your documentation GitHub repository URL
    "github_url": "https://github.com/canonical/charmcraft",
    "github_issues": "https://github.com/canonical/charmcraft/issues",
    # Docs branch in the repo; used in links for viewing the source files
    # 'repo_default_branch': 'main',
    # Docs location in the repo; used in links for viewing the source files
    # "repo_folder": "/docs/",
    # List contributors on individual pages
    "display_contributors": False,
    # Required for feedback button
    'github_issues': 'enabled',
}

#html_extra_path = []

# Enable the edit button on pages
# html_theme_options = {
#   'source_edit_link': "https://github.com/canonical/charmcraft",
# }

# Project slug; see https://meta.discourse.org/t/what-is-category-slug/87897
# slug = ''


#########################
# Sitemap configuration #
#########################

# Use RTD canonical URL to ensure duplicate pages have a specific canonical URL
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")

# sphinx-sitemap uses html_baseurl to generate the full URL for each page:
sitemap_url_scheme = '{link}'

# Include `lastmod` dates in the sitemap:
# sitemap_show_lastmod = True

# Exclude generated pages from the sitemap:
sitemap_excludes = [
    '404/',
    'genindex/',
    'search/',
]


################################
# Template and asset locations #
################################

html_static_path = ["_static"]
templates_path = ["_templates"]


#############
# Redirects #
#############

rediraffe_redirects = "redirects.txt"


###########################
# Link checker exceptions #
###########################

# A regex list of URLs that are ignored by 'make linkcheck'
linkcheck_anchors_ignore = [
    "#",
    ":",
    r"https://github\.com/.*",
]
linkcheck_ignore = [
    # Ignore releases, since we'll include the next release before it exists.
    r"^https://github.com/canonical/[a-z]*craft[a-z-]*/releases/.*",
    # Entire domains to ignore due to flakiness or issues
    r"^https://www.gnu.org/",
    r"^https://crates.io/",
    r"^https://([\w-]*\.)?npmjs.org",
    r"^https://rsync.samba.org",
    r"^https://ubuntu.com",
    r"https://github.com/.*#",
    "http://django-hello-world",
    "http://www.inkscape.org",
    "https://matrix.to",
    "https://www.npmjs.com/",
]

# Give linkcheck multiple tries on failure
linkcheck_retries = 20


########################
# Configuration extras #
########################

# Custom Sphinx extensions; see
# https://www.sphinx-doc.org/en/master/usage/extensions/index.html
# NOTE: The canonical_sphinx extension is required for the starter pack.
extensions = [
    "canonical_sphinx",
    "notfound.extension",
    "sphinx_design",
    # "sphinx_tabs.tabs",
    # "sphinxcontrib.jquery"
    "sphinxext.opengraph",
    # "sphinx_config_options",
    # "sphinx_contributor_listing",
    # "sphinx_filtered_toctree",
    "sphinx_related_links",
    "sphinx_roles",
    "sphinx_terminal",
    # "sphinx_ubuntu_images",
    # "sphinx_youtube_links",
    # "sphinxcontrib.cairosvgconverter",
    # "sphinx_last_updated_by_git",
    "sphinx.ext.intersphinx",
    "sphinx_sitemap",
    # Custom Craft extensions
    "pydantic_kitbash",
    "sphinxext.rediraffe",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
]

# Excludes files or directories from processing
exclude_patterns = [
    "README.md",  # Docs README
    "reuse",
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
    "common/craft-parts/reference/plugins/colcon_plugin.rst",
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
    "common/craft-parts/reference/plugins/python_v2_plugin.rst",
    "common/craft-parts/reference/plugins/qmake_plugin.rst",
    "common/craft-parts/reference/plugins/ruby_plugin.rst",
    "common/craft-parts/reference/plugins/rust_plugin.rst",
    "common/craft-parts/reference/plugins/scons_plugin.rst",
    "common/craft-parts/reference/plugins/go_plugin.rst",
    "common/craft-parts/reference/plugins/go_use_plugin.rst",
    "common/craft-parts/reference/plugins/uv_plugin.rst",
]

# Adds custom CSS files, located under 'html_static_path'
html_css_files = [
    'css/cookie-banner.css'
]

# Adds custom JavaScript files, located under 'html_static_path'
html_js_files = [
    'js/bundle.js',
]

# Specifies a reST snippet to be appended to each .rst file
rst_epilog = """
.. include:: /reuse/links.txt
"""

# Feedback button at the top; enabled by default
# disable_feedback_button = True

# Your manpage URL
# manpages_url = 'https://manpages.ubuntu.com/manpages/{codename}/en/' + \
#     'man{section}/{page}.{section}.html'

# Specifies a reST snippet to be prepended to each .rst file
# This defines a :center: role that centers table cell content.
# This defines a :h2: role that styles content for use with PDF generation.
rst_prolog = """
.. role:: center
   :class: align-center
.. role:: h2
    :class: hclass2
.. role:: woke-ignore
    :class: woke-ignore
.. role:: vale-ignore
    :class: vale-ignore
"""

# Workaround for https://github.com/canonical/canonical-sphinx/issues/34
if "discourse_prefix" not in html_context and "discourse" in html_context:
    html_context["discourse_prefix"] = f"{html_context['discourse']}/t/"

# Add configuration for intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "craft-parts": ("https://canonical-craft-parts.readthedocs-hosted.com/latest/", None),
    "juju": ("https://documentation.ubuntu.com/juju/3.6/", None),
    "ops": ("https://documentation.ubuntu.com/ops/latest/", None),
    "rockcraft": ("https://documentation.ubuntu.com/rockcraft/stable/", None),
    "12-factor": ("https://canonical-12-factor-app-support.readthedocs-hosted.com/latest/", None),
    "charmlibs": ("https://documentation.ubuntu.com/charmlibs/", None),
}


##############################
# Custom Craft configuration #
##############################

# Type hints configuration
set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = True

# Autodoc settings
autodoc_default_options = {"exclude-members": "model_post_init"}


# Automated documentation
project_dir = pathlib.Path(__file__).parents[1].resolve()

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
