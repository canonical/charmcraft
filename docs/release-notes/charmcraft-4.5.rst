.. meta::
    :description: Learn about the new features, changes, and fixes introduced in Charmcraft 4.5.

.. _release-4.5:

Charmcraft 4.5 release notes
============================

21 October 2026

Learn about the new features, changes, and fixes introduced in Charmcraft 4.5.


Requirements and compatibility
------------------------------

For development and testing, Charmcraft requires a host with a minimum of 4GB RAM
running a Linux distribution compatible with systemd.

All versions of Charmcraft require the following software:

- systemd
- `snapd`_
- Either `LXD`_ or `Multipass`_

We recommend you install the `Charmcraft snap <https://snapcraft.io/charmcraft>`__. It
comes bundled with all its dependencies.

Non-snap installations of Charmcraft have the following dependencies:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_


What's new
----------

Charmcraft 4.5 brings the following new features.

Monorepo support
~~~~~~~~~~~~~~~~

Charmcraft now supports packing charms located within monorepos when the
``CHARMCRAFT_EXPERIMENTAL_MONOREPO`` environment variable is enabled. In this mode,
Charmcraft mounts the root of the enclosing Git repository into the build instance.
Charms can then access shared dependencies located in parent or sibling directories.
The necessary project file changes and commands to enable this feature are
described in :ref:`pack-a-charm-in-a-monorepo`.


Minor features
--------------

Charmcraft 4.5 brings the following minor changes.


Skip repacking unchanged charms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft now mediates the generation of ``actions.yaml``, ``config.yaml``,
``manifest.yaml``, and ``metadata.yaml``, allowing Charmcraft to skip repacking
when no project files or metadata have changed.


Base-specific init profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``charmcraft init`` command now accepts ``--base`` for profiles that provide
base-specific variants. The 12-factor framework profiles (Django, Flask, FastAPI, Go,
ExpressJS, and Spring Boot) support ``ubuntu@24.04`` and ``ubuntu@26.04``.
All profiles use Ubuntu 24.04 LTS when ``--base`` isn't provided.

Example actions in the machine and Kubernetes profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms created with the ``machine`` profile now declare ``pause`` and ``resume``
actions, which stop and start the workload without removing the unit. Charms created
with the ``kubernetes`` profile now declare a ``restart`` action, which restarts the
workload's Pebble service.

Both profiles scaffold unit and integration tests for the added behavior.

Secret handling in the machine and Kubernetes profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms created with the ``machine`` and ``kubernetes`` profiles now implement both
sides of Juju secrets.

For a user-provided secret, the charm declares an ``api-token`` config option of type
``secret``, resolves it, and re-reads it when the operator adds a new revision.

For an app-managed secret, the leader creates a workload password with a rotation
policy and an expiry, replaces it when Juju asks for rotation or reports expiry, and
removes unused revisions.

Both profiles scaffold unit and integration tests for the added behavior.

Removed lockfile from machine and Kubernetes profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``machine`` and ``kubernetes`` profiles no longer include a ``uv.lock`` file. You
need to run ``uv lock`` after creating a charm with ``charmcraft init``.

Minor init profile improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The dependencies of the ``machine`` and ``kubernetes`` profiles are now bound to
  their current major version. This reduces the risk of breaking changes if you use
  automated dependency updates.
- The logging configuration of the ``machine`` and ``kubernetes`` profiles now ensure
  that live logs are not emitted from the charm code during unit tests.
- Charms created with the ``kubernetes`` profile now use an Ubuntu image as a
  placeholder for the charm's real image, so that integration tests pass by default.
- Charms created with the 12-factor framework profiles targeting Ubuntu 26.04 now default
  to ``charm-user: non-root``.


Feature deprecations
--------------------

The following features are deprecated in Charmcraft 4.5.


Library registration
~~~~~~~~~~~~~~~~~~~~

Charmhub no longer accepts the registration of new libraries, so the ``charmcraft
create-lib`` command now exits with an error that points to the `Charmhub-hosted charm
libraries deprecation notice <https://ubu.link/charmhub-libraries-deprecation>`__, which
explains what to do instead. New and existing charm libraries should now be distributed
as Python packages.


Fixed bugs and issues
---------------------

The following issues have been resolved in Charmcraft 4.5.

- `#2661 <https://github.com/canonical/charmcraft/issues/2661>`__
  Packing a charm sometimes fails with "Too many levels of symbolic links"
- `#2839 <https://github.com/canonical/charmcraft/issues/2839>`__
  Charm plugins fail to copy source and lib when source-subdir is used
- `#2909 <https://github.com/canonical/charmcraft/issues/2909>`__
  Regression in ``charmcraft pack`` when there are multiple bases
- `#2889 <https://github.com/canonical/charmcraft/issues/2889>`__
  ``make setup`` fails on Apple Silicon due to hard-coded ``/usr/local`` libgit2 path
- Experimental V2 12-factor extensions now generate the paas-charm 2.x peer,
  secret, configuration, and dependency contracts while preserving V1 output. The V2
  profiles rely on ``paas-charm`` for the PyPI OAuth, OpenFGA, and tracing interfaces
  instead of fetching the corresponding libraries from Charmhub. V2 profiles no longer
  generate the obsolete Redis relation or library and retain Valkey support.
- The Spring Boot extension on Ubuntu 24.04 LTS is experimental, matching Rockcraft.
- Experimental V2 12-factor extensions no longer generate the ``app-port``,
  ``webserver-port``, ``metrics-port``, and ``metrics-path`` configuration options.
  Configure them in ``paas-config.yaml`` instead.


Spring Boot extension
~~~~~~~~~~~~~~~~~~~~~
In prior versions of Charmcraft, the Spring Boot extension was mistakenly marked
as stable for Ubuntu 24.04 LTS. Charmcraft 4.5 corrects its state to experimental,
matching Rockcraft.


Known issues
------------

The following issues were reported and are scheduled to be fixed in upcoming
patch releases.

See individual issue links for any mitigations.

- `#2078 <https://github.com/canonical/charmcraft/issues/2078>`__
  ``charmcraft clean`` does not clean all platforms for a charm
- `#1990 <https://github.com/canonical/charmcraft/issues/1990>`__ Cannot stage
  packages with Charmcraft
- `#2492 <https://github.com/canonical/charmcraft/issues/2492>`__ Internal error when
  uploading a charm outside of a project directory
- `#2788 <https://github.com/canonical/charmcraft/issues/2788>`__
  uv plugin fails on core26: dispatch script uses system Python instead of venv


Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@alithethird <https://github.com/alithethird>`,
:literalref:`@canon-cat <https://github.com/canon-cat>`,
:literalref:`@cmatsuoka <https://github.com/cmatsuoka>`,
:literalref:`@dwilding <https://github.com/dwilding>`,
:literalref:`@erinecon <https://github.com/erinecon>`,
:literalref:`@jahn-junior <https://github.com/jahn-junior>`,
:literalref:`@james-garner-canonical <https://github.com/james-garner-canonical>`,
:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@lengau <https://github.com/lengau>`,
:literalref:`@medubelko <https://github.com/medubelko>`,
:literalref:`@Omjaiswal26 <https://github.com/Omjaiswal26>`,
:literalref:`@swetha1654 <https://github.com/swetha1654>`,
:literalref:`@Thanhphan1147 <https://github.com/Thanhphan1147>`,
:literalref:`@tonyandrewmeyer <https://github.com/tonyandrewmeyer>`,
and :literalref:`@tromai <https://github.com/tromai>`
