Changelog
*********

Newer releases have their own :doc:`/release-notes/index` pages. Please refer
to those.

..
  release template:

  X.Y.Z (YYYY-MM-DD)
  ------------------

  Core
  ====

  # for everything related to the lifecycle of packing a charm

  Bases
  #####

  <distro>@<series>
  """""""""""""""""
  (order from newest base to oldest base)

  Plugins
  #######

  <plugin>
  """"""""

  List plugins
  """"""""""""

  Extensions
  ##########

  <extension>
  """""""""""

  Expand extensions
  """""""""""""""""

  List extensions
  """""""""""""""

  Metadata
  ########

  Sources
  #######

  Components
  ##########

  Command line
  ============

  # for command line and UX changes

  Linter
  ======

  Init
  ====

  Metrics
  =======

  Names
  =====

  Remote build
  ============

  Store
  =====

  Documentation
  =============

  For a complete list of commits, see the `X.Y.Z`_ release on GitHub.

3.3.3 (2025-02-05)
------------------

This release contains some bug fixes for the 3.3 branch.

Core
====

- Charmcraft no longer crashes when setting up a managed instance if ``/root/.cache``
  does not exist in the instance.

3.3.2 (2025-01-27)
------------------

This release contains some bug fixes for the 3.3 branch.

Command line
============

This release removes experimental test templates added to the project when
running ``charmcraft init``. Existing projects will not be affected.

3.3.1 (2025-01-23)
------------------

This release contains some bug fixes for the 3.3 branch.

Command line
============

- The :ref:`ref_commands_publish-lib` command now returns ``0`` if the libraries
  published match the versions already on the store. It also no longer creates a new
  revision on the store in this case.
- The ``test`` command is now correctly marked as experimental.

Documentation
=============

- Add :doc:`reference </reference/platforms>` and a
  :ref:`how-to guide <select-platforms>` for the ``platforms`` key in the
  :ref:`charmcraft-yaml-file`.
- Fix some links to the `Juju`_ documentation.

For a complete list of commits, see the `3.3.1`_ release on GitHub.

3.3.0 (2025-01-13)
------------------

Core
====

Plugins
#######

- New :ref:`craft_parts_poetry_plugin`.
- New :ref:`craft_parts_python_plugin`.
- In the reactive plugin, the ``charm`` command is now run in verbose mode by default.

Reactive
""""""""

Extensions
##########

- New :ref:`fastapi-framework-extension`
- The :ref:`django-framework-extension` is no longer considered experimental.

Command line
============

- The :doc:`commands/pack` command now updates the charm libaries in the project
  directory if they don't meet the requirements in the ``charm-libs`` key of
  ``charmcraft.yaml``.
- New :ref:`ref_commands_create-track` command.

Linter
======

- New linter to check that the entrypoint contains a call to ``ops.main()``

Documentation
=============

How-to guides for migrating to the new plugins:

- :ref:`howto-migrate-to-poetry`
- :ref:`howto-migrate-to-python`

For a complete list of commits, see the `3.3.0`_ release on GitHub.

3.2.2 (2024-10-16)
------------------

- The ``whoami`` command now works with charm-scoped credentials.

For a complete list of commits, see the `3.2.2`_ release on GitHub.

3.2.1 (2024-09-16)
------------------

This is a bugfix release for 3.2, bringing in two fixes:

Core
====

The shared cache directory now gets locked. Builds that run while another copy of
Charmcraft has the cache directory locked will run without a shared cache.

Plugins
#######

charm
"""""

The charm plugin will now force-install pip if the installed venv version is older
than the minimum version, guaranteeing that pip gets updated correctly.

For a complete list of commits, see the `3.2.1`_ release on GitHub.

2.7.4 (2024-10-07)
------------------

This release bumps some dependencies to fix a security issue with requests.

For a complete list of commits, see the `2.7.4`_ release on GitHub.

2.7.3 (2024-09-16)
------------------

Core
====

The shared cache directory now gets locked. Builds that run while another copy of
Charmcraft has the cache directory locked will run without a shared cache.

The charm plugin now force-reinstalls pip when necessary, guaranteeing a correct
version of pip.

For a complete list of commits, see the `2.7.3`_ release on GitHub.

2.7.2 (2024-09-09)
------------------

We've backported some 3.x bugfixes to the 2.7 series.

Store
=====

Skopeo now uses an insecure policy when copying OCI images, allowing it to run
even when the user hasn't set up OCI image policies.

Meta
====

Build fixes to the published version

For a complete list of commits, see the `2.7.2`_ release on GitHub.


3.2.0 (2024-08-28)
------------------

We have some fixes to the 3.1 series, as well as the features below.
The most notable under-the-hood work is that Charmcraft now uses pydantic 2.

Core
====

You can now set ``charm-user`` in ``charmcraft.yaml`` to set what user Juju 3.6.0+ will
use for running a kubernetes charm.

Plugins
#######

reactive
""""""""

Fix: ``actions.yaml`` is no longer overwritten.

Extensions
##########

go-framework
""""""""""""

New ``go-framework`` extension for easily charming go applications.

Documentation
=============

The changelog is now included in the Charmcraft documentation. For completeness, we've
back-filled the log with all the important changes from previous releases documented
on GitHub.

For a complete list of commits, see the `3.2.0`_ release on GitHub.

3.1.2 (2024-08-07)
------------------

* fix(app): clarify wording on 'prime' change
* fix(strict-deps): fail if venv is inconsistent
* fix(application): exclude files from charm
* fix(package): Limit the bases in manifest.yaml


3.1.1 (2024-07-24)
------------------

* fix(ci): fix tox ensure_version_matches
* fix(metadata): allow long summaries in output
* tests(spread): temporarily disable failing test


3.1.0 (2024-07-23)
------------------

New Features
============

* Charmcraft has a new :ref:`ref_commands_fetch-libs` command, which, when
  combined with a ``charm-libs`` key in ``charmcraft.yaml``, allows the
  automatic fetching and updating of multiple
  :doc:`charm libraries </howto/manage-libraries>`.
* The new, experimental :ref:`ref_commands_test` command is also included in
  Charmcraft 3.1. Please have a go with it. Documentation is fairly minimal
  right now, as the implementation is still in flux.
* The :ref:`ref_commands_upload-resource` command now uses
  :literalref:`skopeo` to upload images. Most notably,
  this means you can enter
  `any skopeo-supported containers-transports URL
  <https://manpages.ubuntu.com/manpages/noble/man5/containers-transports.5.html>`_
  to upload an OCI container to Charmhub.
* New features to experimental :ref:`extensions <manage-extensions>`:
  ``django-framework`` and ``flask-framework``. These are designed to work with
  :external+rockcraft:doc:`rocks <index>`, for example,
  :external+rockcraft:doc:`rocks with the flask-framework extension <tutorial/flask>`.
* New releases are automatically published to PyPI (thanks @bittner)!

Bug fixes
=========

* flask-framework charms now automatically include the ``rustup`` snap
* Symlinked directories are correctly included in charms (previously only symlinked
  files worked).
* Fixed a crash when using the ``framework`` linter with the ``reactive`` plugin
* ... and several more!

For a complete list of commits, see the `3.1.0`_ release on GitHub.

.. _release-3.0.0:

3.0.0 (2024-03-14)
------------------

Breaking Changes
================

- The ``prime`` keyword no longer adds extra files to a charm. If you need this
  functionality, use the :ref:`craft_parts_dump_plugin`
- All new bases, starting with ``ubuntu@24.04``, must use the ``base`` and
  ``platforms`` keywords.
- The ``--bases-index`` parameter is deprecated.
  Please start using the new ``--platform`` parameter instead

For more information, see the `3.0 release announcement`_.

For a complete list of commits, see the `3.0.0`_ release on GitHub.


2.7.1 (2024-07-18)
------------------

- Bump minimum pip version to 24
- set ``--no-binary=:all:`` in strict mode if no binary deps are declared

For a complete list of commits, see the `2.7.1`_ release on GitHub.

.. _release-2.7.0:

2.7.0 (2024-06-18)
------------------

- enable riscv64 support
- upload rocks using skopeo

For a complete list of commits, see the `2.7.0`_ release on GitHub.


2.6.0 (2024-04-12)
------------------

- support ``type:secret`` in ``config.options``
- works with LXD 5.21

For a complete list of commits, see the `2.6.0`_ release on GitHub.


2.5.5 (2024-02-27)
------------------

- fix(templates): put example config sections on all templates
- fix(linters): ensure CheckResult text isn't None
- fix(builder): don't rely on part names

For a complete list of commits, see the `2.5.5`_ release on GitHub.


2.5.4 (2024-02-27)
------------------

- Bumped minimum pip version to 23

For a complete list of commits, see the `2.5.4`_ release on GitHub.


2.5.3 (2023-12-07)
------------------

- Clearing the shared cache can cause errors
- Internal error when running from outside of a charm repository
- Typo in overview for the :ref:`ref_commands_expand-extensions` command

For a complete list of commits, see the `2.5.3`_ release on GitHub.


2.5.2 (2023-12-01)
------------------

* fix: ignore empty requirements lines

For a complete list of commits, see the `2.5.2`_ release on GitHub.


2.5.1 (2023-12-01)
------------------

* fix: make snap build on all architectures.

For a complete list of commits, see the `2.5.1`_ release on GitHub.


2.5.0 (2023-10-24)
------------------

* ``charmcraft init`` now uses the new unified ``charmcraft.yaml``
* Opt-in strict dependency management
* Shared wheel cache between build environments on the same host
* Add support for Ubuntu mantic based charms (not for production use :-) )

For a complete list of commits, see the `2.5.0`_ release on GitHub.


Earlier than 2.5.0
------------------

For the changes from releases before 2.5.0, please consult the `GitHub Releases`_
page.

.. _`GitHub Releases`: https://github.com/canonical/charmcraft/releases
.. _`3.0 release announcement`: https://discourse.charmhub.io/t/charmcraft-3-0-in-the-beta-channel/13469

.. _2.5.0: https://github.com/canonical/charmcraft/releases/tag/2.5.0
.. _2.5.1: https://github.com/canonical/charmcraft/releases/tag/2.5.1
.. _2.5.2: https://github.com/canonical/charmcraft/releases/tag/2.5.2
.. _2.5.3: https://github.com/canonical/charmcraft/releases/tag/2.5.3
.. _2.5.4: https://github.com/canonical/charmcraft/releases/tag/2.5.4
.. _2.5.5: https://github.com/canonical/charmcraft/releases/tag/2.5.5
.. _2.6.0: https://github.com/canonical/charmcraft/releases/tag/2.6.0
.. _2.7.0: https://github.com/canonical/charmcraft/releases/tag/2.7.0
.. _2.7.1: https://github.com/canonical/charmcraft/releases/tag/2.7.1
.. _2.7.2: https://github.com/canonical/charmcraft/releases/tag/2.7.2
.. _2.7.3: https://github.com/canonical/charmcraft/releases/tag/2.7.3
.. _2.7.4: https://github.com/canonical/charmcraft/releases/tag/2.7.4
.. _3.0.0: https://github.com/canonical/charmcraft/releases/tag/3.0.0
.. _3.1.0: https://github.com/canonical/charmcraft/releases/tag/3.1.0
.. _3.1.1: https://github.com/canonical/charmcraft/releases/tag/3.1.1
.. _3.1.2: https://github.com/canonical/charmcraft/releases/tag/3.1.2
.. _3.2.0: https://github.com/canonical/charmcraft/releases/tag/3.2.0
.. _3.2.1: https://github.com/canonical/charmcraft/releases/tag/3.2.1
.. _3.2.2: https://github.com/canonical/charmcraft/releases/tag/3.2.2
.. _3.3.0: https://github.com/canonical/charmcraft/releases/tag/3.3.0
.. _3.3.1: https://github.com/canonical/charmcraft/releases/tag/3.3.1
