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

Charmcraft 4.5 brings the following features, integrations, and improvements.


<Important change>
~~~~~~~~~~~~~~~~~~

<Describe the most important change in this release and how it affects users.>


Minor features
--------------

Charmcraft 4.5 brings the following minor changes.


Example actions in the machine and Kubernetes profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms created with the ``machine`` profile now declare ``pause`` and ``resume``
actions, which stop and start the workload without removing the unit. Charms created
with the ``kubernetes`` profile now declare a ``restart`` action, which restarts the
workload's Pebble service.

Both profiles scaffold unit and integration tests for their actions.


<Feature A>
~~~~~~~~~~~

- <Add a short description of a minor change.>


Backwards-incompatible changes
------------------------------

The following changes are incompatible with previous versions of Charmcraft.


<Removed or disabled feature B>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

<Describe what changed, why, and what users should do next.>


Feature deprecations
--------------------

The following features are deprecated in Charmcraft 4.5.


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

The following issues have been resolved in Charmcraft 4.5.

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
