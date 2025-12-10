.. _release-4.1:

Charmcraft 4.1 release notes
============================

11 December 2025

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

Support for Ubuntu 25.10 and Ubuntu 26.04 LTS bases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.1 adds experimental support for the Ubuntu 25.10 and Ubuntu 26.04 LTS
bases. The purpose of charms built on the Ubuntu 25.10 interim base is to test changes
that will affect the upcoming 26.04 release. As such, minor Charmcraft releases may
change how these charms build. See our
:ref:`Interim bases policy <explanation-bases-lts-and-interim-bases>` for further
information.

12-factor app charm HTTP proxy relation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charms that use a 12-factor app :ref:`extension <extensions>` can now use the
``http_proxy`` relation. The
`Squid Forward Proxy <https://charmhub.io/squid-forward-proxy>`_ charm is an example
provider. To use this relation in your app, add it to the ``requires`` key:

.. code-block:: yaml

    requires:
      http-proxy:
        interface: http_proxy
        optional: true
        limit: 1

The init profiles for 12-factor apps now include this relation.

Support for Spring Boot profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
- `#2493 <https://github.com/canonical/charmcraft/issues/2493>`_ Packing fails when
  using a separate metadata.yaml file and the ``--project-dir`` argument.
- `#2492 <https://github.com/canonical/charmcraft/issues/2492>`_ Internal error when
  uploading a charm outside of a project directory.


.. Fixed bugs and issues
.. ---------------------

Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@aj4ayushjain <https://github.com/aj4ayushjain>`,
:literalref:`@alithethird <https://github.com/alithethird>`,
:literalref:`@dwilding <https://github.com/dwilding>`,
:literalref:`@erinecon <https://github.com/erinecon>`,
:literalref:`@james-garner-canonical <https://github.com/james-garner-canonical>`,
:literalref:`@jahn-junior <https://github.com/jahn-junior>`,
:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@lengau <https://launchpad.net/~lengau>`,
:literalref:`@medubelko <https://github.com/medubelko>`,
:literalref:`@swetha1654 <https://github.com/swetha1654>` and
:literalref:`@tonyandrewmeyer <https://github.com/tonyandrewmeyer>`
