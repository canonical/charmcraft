:orphan:

.. meta::
    :description: Learn about the new features, changes, and fixes introduced in Charmcraft 4.6.

.. _release-4.6:

Charmcraft 4.6 release notes
============================

TBD

Learn about the new features, changes, and fixes introduced in Charmcraft 4.6.


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

Charmcraft 4.6 brings the following features, integrations, and improvements.


<Important change>
~~~~~~~~~~~~~~~~~~

<Describe the most important change in this release and how it affects users.>


Minor features
--------------

Charmcraft 4.6 brings the following minor changes.


A new github-ci profile
~~~~~~~~~~~~~~~~~~~~~~~

- The new ``github-ci`` profile adds a ``.github`` directory with GitHub Actions and
  Dependabot configuration to charms created with the ``machine`` and ``kubernetes``
  profiles.
- The ``pyproject.toml`` file of the ``machine`` and ``kubernetes`` profiles now has a
  ``ci`` dependency group with the tools that the ``github-ci`` workflows use.
- The integration workflow takes a ``concierge-preset`` input, ``k8s`` or ``machine``.
  By default, ``ci.yaml`` passes ``k8s``; for a machine charm, change it to ``machine``.
  The publish workflow resolves the resource to attach in its own step and uses the
  step's output in the upload; remove the step and the ``--resource`` option if your
  charm doesn't have any resources. See :ref:`the workflows reference
  <github-workflows-directory>` for details.

Minor init profile improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The ``machine`` and ``kubernetes`` profiles now include a ``SECURITY.md`` file, as a
  placeholder security policy for the charm.
- The pytest configuration of the ``machine`` and ``kubernetes`` profiles now writes
  debug-level logs to a file when you invoke pytest with the ``--log-file`` option. The
  integration test workflow in the ``github-ci`` profile uses this option to save the
  logs.


Backwards-incompatible changes
------------------------------

The following changes are incompatible with previous versions of Charmcraft.


<Removed or disabled feature B>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

<Describe what changed, why, and what users should do next.>


Feature deprecations
--------------------

The following features are deprecated in Charmcraft 4.6.


<Deprecated feature C>
~~~~~~~~~~~~~~~~~~~~~~

<Describe the deprecation status, alternatives, and migration guidance.>


Scheduled feature deprecations
------------------------------

The following features will be deprecated in Charmcraft <planned version>.


<Feature D>
~~~~~~~~~~~

<Describe planned deprecations that have been formally announced.>


Fixed bugs and issues
---------------------

The following issues have been resolved in Charmcraft 4.6.

- No entries yet.


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
