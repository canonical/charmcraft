Changelog
*********

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
  `charm libraries <https://juju.is/docs/sdk/manage-libraries>`_.
* The new, experimental :ref:`ref_commands_test` command is also included in
  Charmcraft 3.1. Please have a go with it. Documentation is fairly minimal
  right now, as the implementation is still in flux.
* The :ref:`ref_commands_upload-resource` command now uses
  `skopeo <https://github.com/containers/skopeo>`_ to upload images. Most notably,
  this means you can enter
  `any skopeo-supported containers-transports URL
  <https://manpages.ubuntu.com/manpages/noble/man5/containers-transports.5.html>`_
  to upload an OCI container to Charmhub.
* New features to experimental
  `extensions <https://juju.is/docs/sdk/manage-extensions>`_:
  ``django-framework`` and ``flask-framework``. These are designed to work with rocks,
  for example, `rocks with the flask-framework extension`_.
* New releases are automatically published to PyPI (thanks @bittner)!

Bug fixes
=========

* flask-framework charms now automatically include the ``rustup`` snap
* Symlinked directories are correctly included in charms (previously only symlinked
  files worked).
* Fixed a crash when using the ``framework`` linter with the ``reactive`` plugin
* ... and several more!

For a complete list of commits, see the `3.1.0`_ release on GitHub.


3.0.0 (2024-03-14)
------------------

Breaking Changes
================

- The ``prime`` keyword no longer adds extra files to a charm. If you need this
  functionality, please refer to this documentation page:
  `Include extra files in a charm`_
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
.. _`Include extra files in a charm`: https://juju.is/docs/sdk/include-extra-files-in-a-charm
.. _`3.0 release announcement`: https://discourse.charmhub.io/t/charmcraft-3-0-in-the-beta-channel/13469
.. _`rocks with the flask-framework extension`: https://documentation.ubuntu.com/rockcraft/en/stable/tutorials/getting-started-with-flask/
.. _2.5.0: https://github.com/canonical/charmcraft/releases/tag/2.5.0
.. _2.5.1: https://github.com/canonical/charmcraft/releases/tag/2.5.1
.. _2.5.2: https://github.com/canonical/charmcraft/releases/tag/2.5.2
.. _2.5.3: https://github.com/canonical/charmcraft/releases/tag/2.5.3
.. _2.5.4: https://github.com/canonical/charmcraft/releases/tag/2.5.4
.. _2.5.5: https://github.com/canonical/charmcraft/releases/tag/2.5.5
.. _2.6.0: https://github.com/canonical/charmcraft/releases/tag/2.6.0
.. _2.7.0: https://github.com/canonical/charmcraft/releases/tag/2.7.0
.. _2.7.1: https://github.com/canonical/charmcraft/releases/tag/2.7.1
.. _3.0.0: https://github.com/canonical/charmcraft/releases/tag/3.0.0
.. _3.1.0: https://github.com/canonical/charmcraft/releases/tag/3.1.0
.. _3.1.1: https://github.com/canonical/charmcraft/releases/tag/3.1.1
.. _3.1.2: https://github.com/canonical/charmcraft/releases/tag/3.1.2
.. _3.2.0: https://github.com/canonical/charmcraft/releases/tag/3.2.0
