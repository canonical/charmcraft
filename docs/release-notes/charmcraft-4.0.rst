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
comes bundled with all its dependencies.

Non-snap installations of Charmcraft have the following dependencies:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_


What's new
----------

Charmcraft 4.0 brings the following new features.

New Documentation Domain
~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft is an important member of the Canonical community and ecosystem, and all its
site names should demonstrate that. With this release, we gave the docs a new home at
the Ubuntu domain. You can now reach it at:

`documentation.ubuntu.com/charmcraft <https://documentation.ubuntu.com/charmcraft>`_

We put redirects in place to handle links to the old ReadTheDocs domain.

With this change, we also removed the language subdirectory (/en) in the URL, to
shave a few characters off all links.

OpenID Connect integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenID Connect is now available in all 12-factor app charm extensions.
It's available in any charm using the
:ref:`Django <django-framework-extension>`,
:ref:`Express <expressjs-framework-extension>`,
:ref:`FastAPI <fastapi-framework-extension>`,
:ref:`Flask <flask-framework-extension>`, and
:ref:`Go <go-framework-extension>` extensions and packed with Charmcraft 4.

``init`` profile changes
~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.0 has much more modern ``machine`` and ``kubernetes``
:ref:`ref_commands_init` profiles. Changes include:

- The ``static`` and ``lint`` tox environments are now united.
- The charm is packed with the :ref:`craft_parts_uv_plugin`.
- Dependencies are now managed with `uv <https://docs.astral.sh/uv>`_.
- The reusable integration tests now use `Jubilant
  <https://documentation.ubuntu.com/jubilant/>`_.

Test profiles
^^^^^^^^^^^^^

We introduced two new init profiles, ``test-machine`` and ``test-kubernetes``. They
provide a framework for using the :literalref:`charmcraft test <ref_commands_test>`
command.
These profiles are experimental, so we can't guarantee their stability.

Spring Boot framework extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Apps that use the Spring Boot framework can now use the
:ref:`spring-boot-framework-extension` for charming the app. A new
:ref:`tutorial <write-your-first-kubernetes-charm-for-a-spring-boot-app>` is also
included to walk a first-time charmer through charming their Spring Boot app.

Feature removals
----------------

The following features are removed in Charmcraft 4.0. If you need these features, they
are still available in Charmcraft 3.

Windows support
~~~~~~~~~~~~~~~

Charmcraft 4.0 has ceased support for Windows. To continue on the platform, we
encourage Windows users to run Charmcraft in `Windows Subsystem for Linux
<https://ubuntu.com/desktop/wsl>`_.


CentOS 7 support
~~~~~~~~~~~~~~~~

CentOS 7 reached its `end of life
<https://www.redhat.com/en/topics/linux/centos-linux-eol>`_ on 30 June 2024, and
support for it has ended with Charmcraft 4.0.


Bundle removal
~~~~~~~~~~~~~~

As scheduled, all charm bundle features are removed with Charmcraft 4.0. Charmcraft 3
will continue support for packing bundles and the ``register-bundle`` and
``promote-bundle`` commands. This follows the `discontinuation of new bundle
registrations <https://discourse.charmhub.io/t/15344>`_ in Nov 2024.


``simple`` profile
~~~~~~~~~~~~~~~~~~

The ``simple`` init profile is removed from Charmcraft 4.0.
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

- `#2431 <https://github.com/canonical/charmcraft/issues/2431>`_ Charmcraft now
  errors if a relation name is invalid.

Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@ade555 <https://github.com/ade555>`,
:literalref:`@alithethird <https://github.com/alithethird>`,
:literalref:`@bepri <https://github.com/bepri>`,
:literalref:`@dimaqq <https://github.com/dimaqq>`,
:literalref:`@dwilding <https://github.com/dwilding>`,
:literalref:`@erinecon <https://github.com/erinecon>`,
:literalref:`@jahn-junio r<https://github.com/jahn-junior>`,
:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@lengau <https://launchpad.net/~lengau>`,
:literalref:`@m7mdisk <https://github.com/m7mdisk>`,
:literalref:`@marcusboden <https://github.com/marcusboden>`,
:literalref:`@medubelko <https://github.com/medubelko>`,
:literalref:`@mr-cal <https://github.com/mr-cal>` and
:literalref:`@tonyandrewmeyer <https://github.com/tonyandrewmeyer>`
