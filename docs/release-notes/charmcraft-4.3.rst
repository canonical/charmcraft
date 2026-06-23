.. meta::
    :description: Learn about the new features, changes, and fixes introduced in Charmcraft 4.3.

.. _release-4.3:

Charmcraft 4.3 release notes
=============================

23 June 2026

Learn about the new features, changes, and fixes introduced in Charmcraft 4.3.


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

Charmcraft 4.3 brings the following new features.

Ubuntu 26.04 LTS support for the reactive plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :ref:`reactive plugin <reference-charmcraft-yaml-reactive-plugin>` can now build
charms on the Ubuntu 26.04 LTS base. Because the python3-venv package was moved
to the ``universe`` APT repository on Ubuntu 26.04 LTS, the plugin now adds this
repository automatically.

See :ref:`howto-change-to-ubuntu-26-04` for guidance on migrating your
charm to Ubuntu 26.04 LTS.

Part naming constraints
~~~~~~~~~~~~~~~~~~~~~~~

Part names are now validated more
strictly and cannot contain forward slashes (``/``) in charms built on the ``ubuntu@26.04``
base or higher.

Valkey support in 12-factor app init templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The init templates for 12-factor app frameworks (Django, Flask, FastAPI, Express.js,
Go, and Spring Boot) now include a commented-out ``valkey_client`` relation. If you
declare this optional interface in your charm's ``requires``, Charmcraft automatically
injects the necessary dpcharmlibs-interfaces charm Python package.

If the ``valkey_client`` relation is declared, you can make use of the following
environment variables in your app:

- ``VALKEY_HOSTNAME``
- ``VALKEY_PORT``
- ``VALKEY_USERNAME``
- ``VALKEY_PASSWORD``

See :ref:`extensions` for details.

Improved test scaffolding
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``charmcraft init`` command now generates charm project files with improved
test scaffolding:

- Templates now use `pytest-jubilant
  <https://documentation.ubuntu.com/jubilant/>`__ as the test runner for
  integration tests, replacing the previous custom helpers. The
  ``@pytest.mark.juju_setup`` marker is included in integration test scaffolding for
  machine and Kubernetes profiles.
- Integration test templates for machine and Kubernetes profiles have improved comments
  pointing to the canonical guide on writing integration tests.

COS directory structure validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When packing a 12-factor app charm, Charmcraft now validates the structure of any
custom COS (Canonical Observability Stack) directory. If the directory layout is
incorrect, Charmcraft reports an error when packing instead of letting an invalid
structure cause errors at runtime.


Documentation improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.3 includes the following new and updated documentation:

- :doc:`How to migrate your charm to Ubuntu 26.04 </howto/migrate-bases/change-to-ubuntu-2604>`
- Documentation for the ``django-secret-key-id`` configuration option
- Valkey integration reference, including environment variables and integration metadata
- Plugin differences noted in the guide on managing charm icons


Fixed bugs and issues
---------------------

The following issues have been resolved in Charmcraft 4.3:

- `#2600 <https://github.com/canonical/charmcraft/issues/2600>`__
  ``charmcraft pack -p`` and ``-o`` arguments did not work correctly together


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


Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@activus-d <https://github.com/activus-d>`,
:literalref:`@bepri <https://github.com/bepri>`,
:literalref:`@canon-cat <https://github.com/canon-cat>`,
:literalref:`@danielvnguyen <https://github.com/danielvnguyen>`,
:literalref:`@dimaqq <https://github.com/dimaqq>`,
:literalref:`@dwilding <https://github.com/dwilding>`,
:literalref:`@f-atwi <https://github.com/f-atwi>`,
:literalref:`@jahn-junior <https://github.com/jahn-junior>`,
:literalref:`@james-garner-canonical <https://github.com/james-garner-canonical>`,
:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@lengau <https://github.com/lengau>`,
:literalref:`@medubelko <https://github.com/medubelko>`,
:literalref:`@sabaini <https://github.com/sabaini>`,
:literalref:`@steinbro <https://github.com/steinbro>`,
:literalref:`@Thanhphan1147 <https://github.com/Thanhphan1147>`,
and :literalref:`@tonyandrewmeyer <https://github.com/tonyandrewmeyer>`
