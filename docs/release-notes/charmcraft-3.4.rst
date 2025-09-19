Charmcraft 3.4 release notes
============================

3 February 2025

Learn about the new features, changes, and fixes introduced in Charmcraft 3.4.


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

Charmcraft 3.4 brings the following features, integrations, and improvements.


``charmcraft promote`` command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In previous releases, switching charm revisions between channels and re-releasing them
was a manual and time-consuming process that involved:

1. Finding all charm revisions currently published on a given channel.
2. Finding the revisions of each resource attached to that charm revision on the
   channel.
3. Releasing each of those charm revisions, with their appropriate resources, to a new
   channel.

Charmcraft 3.4 introduces the :ref:`ref_commands_promote` command, which promotes a
charm on Charmhub from one channel to another. The command runs through this procedure
on your behalf.

If, for example, your charm supports three bases across two architectures, each with its
own resource revision, the ``promote`` command would automatically release all six
revisions to the new channel with the same resources.


Feature deprecations
--------------------

The following features are deprecated in Charmcraft 3.4 and will be removed in
Charmcraft 4.0.


Windows support
~~~~~~~~~~~~~~~

Charmcraft 3.0 deprecated support for Windows, and the upcoming 4.0 major release will
remove support for it (`#1810 <https://github.com/canonical/charmcraft/issues/1810>`_).
Windows users should begin preparing to migrate their workflows to `Windows Subsystem
for Linux <https://ubuntu.com/desktop/wsl>`_.


CentOS 7 support
~~~~~~~~~~~~~~~~

CentOS 7 reached its `end of life
<https://www.redhat.com/en/topics/linux/centos-linux-eol>`_ on 30 June 2024. Charmcraft
3 will continue its current support for CentOS 7, but Charmcraft 4.0 won't support
CentOS 7 (`#1826 <https://github.com/canonical/charmcraft/issues/1826>`_).


Bundle registration
~~~~~~~~~~~~~~~~~~~

New bundle registration `ceased on 1 November 2024
<https://discourse.charmhub.io/t/15344>`_ and the ``register-bundle`` command currently
returns an error. It will be removed in Charmcraft 4.0.0 (`#1858
<https://github.com/canonical/charmcraft/issues/1858>`_).


Scheduled feature deprecations
------------------------------

The following features will be deprecated in Charmcraft 4.0.


Bundle management
~~~~~~~~~~~~~~~~~

In line with the phasing out of bundles, Charmcraft 4.0 will deprecate all bundle
management commands (`#2113 <https://github.com/canonical/charmcraft/issues/2113>`_).
The schedule for removing this feature hasn't been set yet.


``bundle`` plugin
~~~~~~~~~~~~~~~~~

In line with the phasing out of bundles, Charmcraft 4.0 will deprecate the bundle plugin
(`#2114 <https://github.com/canonical/charmcraft/issues/2114>`_). No schedule has been
set yet for this change.


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

Charmcraft 3.4.0
~~~~~~~~~~~~~~~~

- `#2081 <https://github.com/canonical/charmcraft/issues/2081>`_
  ``charmcraft pack`` fails because ``libffi-dev`` is missing.
- `#2058 <https://github.com/canonical/charmcraft/issues/2058>`_ Multi-base charm
  uses the same LXD container for different bases.

Charmcraft 3.4.1
~~~~~~~~~~~~~~~~

- `#2125 <https://github.com/canonical/charmcraft/issues/2125>`_
  ``charmcraft pack`` fails under certain instances when packing in parallel.
- `#264 (craft-store) <https://github.com/canonical/craft-store/issues/264>`_
  ``charmcraft promote`` errors when promoting certain charm/resource combinations.

Charmcraft 3.4.2
~~~~~~~~~~~~~~~~

- `#2149 <https://github.com/canonical/charmcraft/issues/2149>`_ the Charmcraft snap
  does not build on architectures other than amd64.
- Some documentation links were mis-formatted.

Charmcraft 3.4.3
~~~~~~~~~~~~~~~~

- `#2158 <https://github.com/canonical/charmcraft/issues/2158>`_ "Invalid hostname"
  error when packing charm platform with multiple run-on bases.

Charmcraft 3.4.4
~~~~~~~~~~~~~~~~

- `#2194 <https://github.com/canonical/charmcraft/issues/2194>`_ Charmcraft overwrites reactive charm's ``config.yaml``.

Charmcraft 3.4.5
~~~~~~~~~~~~~~~~

- Snap dependencies were updated to resolve `CVE-2025-43859
  <https://www.cve.org/CVERecord?id=CVE-2025-43859>`_.

Charmcraft 3.4.6
~~~~~~~~~~~~~~~~

- The uv plugin was breaking with uv 0.7.
- `#2259 <https://github.com/canonical/charmcraft/issues/2259>`_ Builds fail for 20.04
  in some common circumstances.

Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release.

:literalref:`@bepri<https://github.com/bepri>`,
:literalref:`@dariuszd21<https://github.com/dariuszd21>`,
:literalref:`@lengau<https://launchpad.net/~lengau>` and
:literalref:`@mr-cal<https://github.com/mr-cal>`
