Charmcraft 3.4 release notes
============================

3 February 2025

Learn about the new features, changes, and fixes introduced in Charmcraft 3.4.


Requirements and compatibility
------------------------------

It is recommended that you install Charmcraft from the
`Snap store <https://snapcraft.io/charmcraft>`_, which provides automatic updates
and is the primary environment where it is tested. Most dependencies are included
within the Charmcraft snap, making installation easier.

If installed as a snap, the only external dependency is either `LXD`_ or
`Multipass`_.

Manual installation has the following requirements:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_
- Either `LXD`_ or `Multipass`_

For development and testing, Starcraft requires a modern Linux system or VM
with `Snap`_ and a minimum of 4 GiB RAM.

What's new
----------

Charmcraft 3.4 brings the following features, integrations, and improvements.


``charmcraft promote``
~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 3.4 has a new :ref:`ref_commands_promote` command, which can promote
a charm on Charmhub from one channel to another. The promote command automates the
following steps:

1. Find all charm revisions currently published on a given channel.
2. Find the revisions of each resource attached to that charm revision on the channel.
3. Release each of those charm revisions, with their appropriate resources, to a new
   channel.

This means that if your charm supports three bases on two architectures, each
with its own resource revision, all six revisions will be released to the new
channel with the same resources.

Feature deprecations
--------------------

The following features are deprecated in Starcraft 3.4 and will be removed in
Charmcraft 4.0:

Windows support
~~~~~~~~~~~~~~~

Charmcraft 3 has deprecated support running on Windows, and the upcoming 4.0
release will not have any amount of support for it. Please use
`Ubuntu inside WSL <https://ubuntu.com/desktop/wsl>`_.

CentOS 7 support
~~~~~~~~~~~~~~~~

CentOS 7 reached its `End of life
<https://www.redhat.com/en/topics/linux/centos-linux-eol>`_ on 30 June 2024.
Charmcraft 3 will continue its current support for CentOS 7, but Charmcraft 4
will not support CentOS 7.

Bundle registration
~~~~~~~~~~~~~~~~~~~

New bundle registration `ceased on 1 November 2024
<https://discourse.charmhub.io/t/discontinuing-new-charmhub-bundle-registrations/15344>`_
and Charmcraft's ``register-bundle`` command currently returns an error.
It will be removed entirely in Charmcraft 4.0

Scheduled feature deprecations
------------------------------

The following features will be deprecated in Charmcraft 4.0:


Bundle management
~~~~~~~~~~~~~~~~~

In line with the phasing out of bundles, Charmcraft 4.0 will deprecate all
bundle management commands. The removal versions have not been set.

``bundle`` plugin
~~~~~~~~~~~~~~~~~

In line with the phasing out of bundles, Charmcraft 4.0 will deprecate the
bundle plugin. No schedule has been set for the removal of the bundle plugin.

Known issues
------------

The following issues were reported and are scheduled to be fixed in upcoming
patch releases.

See individual issue links for any mitigations.

- `#2078 <https://github.com/canonical/charmcraft/issues/2078>`_
  ``charmcraft clean`` does not clean all platforms for a charm.
- `#2012 <https://github.com/canonical/charmcraft/issues/2012>`_ Charmcraft uses
  ``/cache`` as the cache directory if snapd doesn't set ``SNAP_USER_COMMON``
- `#1990 <https://github.com/canonical/charmcraft/issues/1990>`_ Cannot stage
  packages with Charmcraft


Fixed bugs and issues
---------------------

The following issues have been resolved in Charmcraft 3.4:

- `#2081 <https://github.com/canonical/charmcraft/issues/2081>`_
  ``charmcraft pack`` fails because ``libffi-dev`` is missing.
- `#2058 <https://github.com/canonical/charmcraft/issues/2058>`_ Multi-base charm
  uses the same LXD container for different bases


Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release.

:literalref:`@bepri <https://github.com/bepri>`,
:literalref:`@dariuszd21 <https://github.com/dariuszd21>`,
:literalref:`@lengau <https://launchpad.net/lengau>`
