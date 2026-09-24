:orphan:

.. meta::
    :description: Learn about the new features, changes, and fixes introduced in Charmcraft 4.5.

.. _release-4.5:

Charmcraft 4.5 release notes
============================

TBD

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


Base-specific init profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``charmcraft init`` command now accepts ``--base`` for profiles that provide
base-specific variants. The 12-factor framework profiles (Django, Flask, FastAPI, Go,
ExpressJS, and Spring Boot) support ``ubuntu@24.04`` and ``ubuntu@26.04``.
They continue to use Ubuntu 24.04 LTS when ``--base`` isn't provided.

Example actions in the machine and Kubernetes profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms created with the ``machine`` profile now declare ``pause`` and ``resume``
actions, which stop and start the workload without removing the unit. Charms created
with the ``kubernetes`` profile now declare a ``restart`` action, which restarts the
workload's Pebble service.

Both profiles scaffold unit and integration tests for the added behavior.

Secret handling in the machine and Kubernetes profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms created with the ``machine`` and ``kubernetes`` profiles now demonstrate both
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

In addition,  ``charmcraft init`` now has a better description of the created files and
how to manage them. For example, if the charm requires uv, the description explains
when to run ``uv lock``.

Other init profile updates
~~~~~~~~~~~~~~~~~~~~~~~~~~

- The dependencies of the ``machine`` and ``kubernetes`` profiles are now bounded to
  their current major version. This reduces the risk of breaking changes if you use
  automated dependency updates.
- The logging configuration of the ``machine`` and ``kubernetes`` profiles now ensure
  that live logs are not emitted from the charm code during unit tests.
- Charms created with the ``kubernetes`` profile now use an Ubuntu image as a
  placeholder for the charm's real image, so that integration tests pass by default.


Backwards-incompatible changes
------------------------------

The following changes are incompatible with previous versions of Charmcraft.


<Removed or disabled feature B>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

<Describe what changed, why, and what users should do next.>


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


Scheduled feature deprecations
------------------------------

The following features will be deprecated in Charmcraft <planned version>.


<Feature D>
~~~~~~~~~~~

<Describe planned deprecations that have been formally announced.>


Fixed bugs and issues
---------------------

The following issues have been resolved in Charmcraft 4.5.

- `#2661 <https://github.com/canonical/charmcraft/issues/2661>`__
  Packing a charm sometimes fails with "Too many levels of symbolic links"
- `#2839 <https://github.com/canonical/charmcraft/issues/2839>`__
  Charm plugins fail to copy source and lib when source-subdir is used


Known issues
------------

The following issues were reported and are scheduled to be fixed in upcoming
patch releases.

See individual issue links for any mitigations.

- No entries yet.


Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release.

Contributor list is pending.
