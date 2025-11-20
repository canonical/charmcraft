:orphan:
.. _release-4.1:

Charmcraft 4.1 release notes
============================

*Unreleased*

Learn about the new features, changes, and fixes introduced in Charmcraft 4.1.


Requirements and compatibility
------------------------------

For development and testing, Charmcraft requires a host with a minimum of 4GB RAM
running a Linux distribution compatible with systemd.

All versions of Charmcraft require the following software:

- systemd
- `snapd`_
- Either `LXD`_ or `Multipass`_

We recommend you install the `Charmcraft snap <https://snapcraft.io/charmcraft>`_. It
comes bundled with all its dependencies.

Non-snap installations of Charmcraft have the following dependencies:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_

What's new
----------

Charmcraft 4.1 brings the following new features.

Ubuntu 25.10 and 26.04
~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.1 adds experimental support for Ubuntu 25.10 and Ubuntu 26.04 bases.
As an interim base, the behaviour of Charmcraft when packing an Ubuntu 25.10 charm is
not guaranteed to be stable, but is instead consistent with the evolving changes
needed for Ubuntu 26.04. See our `Interim bases policy
<https://github.com/canonical/charmcraft/issues/1821>`_ for further information.

12-factor app charm HTTP proxy integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms that use any of the 12-factor :ref:`extensions` can now integrate by default with
the `Squid Forward Proxy <https://charmhub.io/squid-forward-proxy>`_ charm using the
``http-proxy`` relation.

Spring Boot App Profiles
~~~~~~~~~~~~~~~~~~~~~~~~

Charms that use the :ref:`spring-boot-framework-extension` can now configure active
`Spring Boot profiles
<https://docs.spring.io/spring-boot/reference/features/profiles.html>`_ at runtime.

Known issues
------------

The following issues were reported and are scheduled to be fixed in upcoming
patch releases.

See individual issue links for any mitigations.

- `#2078 <https://github.com/canonical/charmcraft/issues/2078>`_
  ``charmcraft clean`` does not clean all platforms for a charm.
- `#1990 <https://github.com/canonical/charmcraft/issues/1990>`_ Cannot stage
  packages with Charmcraft


Fixed bugs and issues
---------------------

Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@lengau <https://launchpad.net/~lengau>` and
:literalref:`@swetha1654 <https://github.com/swetha1654>`
