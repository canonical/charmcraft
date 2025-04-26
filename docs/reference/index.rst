.. _reference:

Reference
=========

The following reference material describes all of Charmcraft's key components and
processes. This includes commands, extensions, charm project files, and more.


Command-line reference
----------------------

The following pages document all of Charmcraft's commands, including their usage,
options, and arguments:

.. toctree::
    :maxdepth: 2

    commands/index


Files
-----

In the context of Charmcraft, a *file* refers to any file in a project that can be
initialised or packed. Such files have their contents documented in the following
pages:

.. toctree::
    :maxdepth: 2

    files/index


Plugins and extensions
----------------------

Charmcraft's extensions allow you to initialize your project with template YAML and
Ops-powered Python to remove the boilerplate steps of crafting charms for Django,
FastAPI, Flask, and Go applications.

.. toctree::
    :maxdepth: 2

    profile
    extensions/index
    plugins/index


Platforms
---------

A charm project file's ``platforms`` key defines where the charm will be built and
where it can run.

.. toctree::
    :maxdepth: 2

    platforms


Parts
-----

Parts provide a mechanism for your charm to obtain and process data from various
sources.

.. toctree::
    :maxdepth: 2

    parts/index


Changelog
---------

All changes to Charmcraft prior to version 3.4 are documented in the page below. For any
newer changes, see :ref:`release-notes`.

.. toctree::
    :maxdepth: 1

    changelog


.. toctree::
    :hidden:

    analyzers-and-linters
    models/index
