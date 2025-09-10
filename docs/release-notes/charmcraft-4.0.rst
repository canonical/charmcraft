Charmcraft 4.0 release notes
============================

23 September 2025

Learn about the new features, changes, and fixes introduced in Charmcraft 4.0.


Requirements and compatibility
------------------------------

For development and testing, Charmcraft requires a host with a minimum of 4GB RAM
running a Linux distribution compatible with systemd.

All versions of Charmcraft require the following software:

- systemd
- `snapd`_
- Either `LXD`_ or `Multipass`_

We recommend you install the `Charmcraft snap <https://snapcraft.io/charmcraft>`_. It
comes comes bundled with all its dependencies.

Non-snap installations of Charmcraft have the following dependencies:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_


What's new
----------

Charmcraft 4.0 brings only a few new features.

OpenID Connect integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

The App charm extensions now include OpenID Connect integration for app charms.
This applies automatically to any charm using the
:ref:`Django <django-framework-extension>`,
:ref:`Express <expressjs-framework-extension>`,
:ref:`FastAPI <fastapi-framework-extension>`,
:ref:`Flask <flask-framework-extension>`, and
:ref:`Go <go-framework-extension>` framework extensions when packing a charm with
Charmcraft 4.

``init`` profile changes
~~~~~~~~~~~~~~~~~~~~~~~~

The profiles for use with the :ref:`ref_commands_init` command have been modernised.
The ``static`` and ``lint`` tox environments are no longer separate.

Test profiles
^^^^^^^^^^^^^

Two new init profiles are also available for better integration with the
:ref:`ref_commands_test` command. These profiles are experimental, but are provided
for early adopters who want to try the experimental test command.

Spring Boot framework extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Apps that use the Spring Boot framework can now use the
:ref:`spring-boot-framework-extension` for charming the app. A new
:ref:`tutorial <write-your-first-kubernetes-charm-for-a-spring-boot-app>` is also
included to walk a first-time charmer through charming their Spring Boot app.

Feature removals
----------------

The following features are removed in Charmcraft 4.0. Anyone needing these features
can continue to use

Windows support
~~~~~~~~~~~~~~~

Charmcraft 4.0 is no longer tested at all on Windows. Windows users use
`Windows Subsystem for Linux <https://ubuntu.com/desktop/wsl>`_ to run Charmcraft.


CentOS 7 support
~~~~~~~~~~~~~~~~

CentOS 7 reached its `end of life
<https://www.redhat.com/en/topics/linux/centos-linux-eol>`_ on 30 June 2024, and
support has been removed from Charmcraft 4.0.


Bundle management commands
~~~~~~~~~~~~~~~~~~~~~~~~~~

Bundle management commands are being removed from Charmcraft 4.0. Charmcraft 3 will
continue to support bundles for those who still need them.


``bundle`` plugin
~~~~~~~~~~~~~~~~~

Charmcraft 4 does not pack bundles. Users who need to pack bundles can use Charmcraft 3
for this purpose.


``simple`` profile
~~~~~~~~~~~~~~~~~~

The ``simple`` profile of ``charmcraft init`` has been removed from Charmcraft 4.
The default profile is now ``kubernetes``, which is a minimal profile with scaffolding
for a Kubernetes charm. We have transferred the ``simple`` profile to an
`example charm <https://github.com/canonical/operator/tree/main/examples/httpbin-demo>`_
in the Ops repository.

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

Charmcraft 4.0.0
~~~~~~~~~~~~~~~~

- `#2431 <https://github.com/canonical/charmcraft/issues/2431>`_ — Charmcraft now
  errors if a relation name is invalid.

Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@jahn-junior<https://github.com/jahn-junior>`,
:literalref:`@lengau<https://launchpad.net/~lengau>`,
:literalref:`@medubelko<https://github.com/medubelko>`,
