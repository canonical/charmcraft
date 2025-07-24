Platforms
=========

Platforms
---------

The project's ``platforms`` key determines where charms are
built and where they run.

For more information on how to build charms for specific bases and
architectures, see the :doc:`Platforms how-to </howto/build-guides/select-platforms>`
page.

Standard notation
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   platforms:
     <platform-name>:
       build-on:
        - <my-arch>
        - <your-arch>
        ...
       build-for:
        - <our-arch>

The platform name is an arbitrary string that describes the platform. The
recommended platform name is the ``build-for`` arch.

See :ref:`build-on <reference-build-on>` and
:ref:`build-for <reference-build-for>` for information on the ``build-on``
and ``build-for`` keys.

.. _reference-platforms-shorthand:

Shorthand notation
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   platforms:
     <arch>:

Shorthand notation is a simple way to describe charms that build on and build
for the same architecture. Shorthand notation requires the platform name to be
a :ref:`valid debian architecture <reference-architectures>`.

.. _reference-platforms-multi-base:

Multi-base notation
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   platforms:
     <platform-name>:
       build-on:
        - <base>:<some-arch>
        - <base>:<another-arch>
       build-for:
        - <base>:<arch>

Multi-base charms define a :ref:`base <reference-bases>` in each platform entry
instead of the top-level ``base`` and ``build-base`` keys. Within each platform
entry, the base must be the same for all ``build-on`` and ``build-for`` entries.

The recommended platform name is ``<distribution>-<series>-<build-for-arch>``
(for example, ``ubuntu-24.04-riscv64``).

.. _reference-platforms-multi-base-shorthand:

Multi-base shorthand notation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   platforms:
     <base>:<arch>:

Multi-base charms can also use shorthand notation when the platform builds on
and builds for the same architecture. This shorthand notation is a YAML dictionary
that contains the shorthand name as a key and a null value. The platform name must be a
:ref:`valid base <reference-bases>` and
:ref:`debian architecture <reference-architectures>` formatted as
``<base>:<arch>``.

.. _reference-build-on:

``build-on``
~~~~~~~~~~~~

``build-on`` is a list of architectures and optional bases that describes the
environments where the platform can build. Entries can be formatted either as only
the architecture (``<arch>``), or as base and architecture (``<base>:<arch>``).

Example ``build-on`` values with only architectures include:

.. code:: yaml

    build-on:
      - amd64
      - riscv64

Example ``build-on`` values containing both a base and an architecture include:

.. code:: yaml

    build-on:
      - ubuntu@24.04:riscv64

.. code:: yaml

    build-on:
      - ubuntu@22.04:amd64

.. _reference-build-for:

``build-for``
~~~~~~~~~~~~~

``build-for`` is a single-element list containing an architecture and optional
base that describes the environment where the resulting charm can run. Each
entry is formatted with an optional base and a mandatory architecture, using the
same structure as ``build-on``.

``build-for: [all]`` is a special key to denote an architecture-independent
charm.

.. _reference-architectures:

Architectures
-------------

Charmcraft uses `Debian's naming convention`_ for architectures and supports several
architectures:

.. list-table::
    :header-rows: 1

    * - Debian name
      - Description
    * - ``amd64``
      - `64-bit x86 <https://en.wikipedia.org/wiki/X86-64>`_
    * - ``arm64``
      - `64-bit ARMv8 <https://en.wikipedia.org/wiki/AArch64>`_
    * - ``armhf``
      - `32-bit ARMv7 with hardware floating point
        <https://en.wikipedia.org/wiki/ARM_architecture_family#VFP>`_
    * - ``ppc64el``
      - `Little-endian 64-bit PowerPC <https://en.wikipedia.org/wiki/Ppc64>`_
    * - ``s390x``
      - `IBM Z-series Linux <https://en.wikipedia.org/wiki/Linux_on_IBM_Z>`_

.. important::

    While Charmcraft will build on or for each of these architectures, not all
    architectures are supported by all Juju versions, and not all clouds support
    all architectures.

.. _reference-bases:

Bases
-----

.. important::

   The bases described in this section are a different concept than the
   deprecated ``bases`` key in a project.

The ``base`` and ``build-base`` keys determine the environments where the charm
is built and where it is run.

``base`` and ``build-base`` can't be defined for multi-base charms. Instead,
the base is defined in the ``platforms`` key.

``base``
~~~~~~~~

.. code-block:: yaml

    base: <base>

``base`` determines the runtime environment for the charm. It's formatted as
``<distribution>@<series>`` where ``distribution`` is the name of a Linux
distribution and ``series`` is the release series name.

Supported bases are:

* ``ubuntu@22.04``
* ``ubuntu@24.04``
* ``ubuntu@24.10``
* ``ubuntu@25.04``
* ``almalinux@9``

``build-base``
~~~~~~~~~~~~~~

.. code-block:: yaml

    build-base: <base>

``build-base`` determines the environment where the charm is built. If
``build-base`` is not defined, it defaults to the value of ``base``.

Supported build-bases are the same as the supported bases listed above.
Additionally, ``devel`` can be used to build a charm using the upcoming Ubuntu
release in development.

Build plans
-----------

A build plan is a list of what charms Charmcraft will build, the environments
where the charms will build, and the environments where the charms will run.
Build plans are determined by the ``platforms``, ``base``, and ``build-base``
keys in a project. The build plan can be filtered with
command-line arguments or environment variables.

Consider the following snippet:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     amd64:
       build-on: [amd64]
       build-for: [amd64]
     amd64-debug:
       build-on: [amd64]
       build-for: [amd64]
     riscv64-cross:
       build-on: [amd64, riscv64]
       build-for: [riscv64]

This snippet generates a build plan with 4 items:

+--------+---------------+---------------+-----------------+----------------+--------------+
| number | platform name | build-on arch | build-time base | build-for arch | runtime base |
+========+===============+===============+=================+================+==============+
| 1      | amd64         | amd64         | Ubuntu 24.04    | amd64          | Ubuntu 24.04 |
+--------+---------------+---------------+-----------------+----------------+--------------+
| 2      | amd64-debug   | amd64         | Ubuntu 24.04    | amd64          | Ubuntu 24.04 |
+--------+---------------+---------------+-----------------+----------------+--------------+
| 3      | riscv64-cross | amd64         | Ubuntu 24.04    | riscv64        | Ubuntu 24.04 |
+--------+---------------+---------------+-----------------+----------------+--------------+
| 4      | riscv64-cross | riscv64       | Ubuntu 24.04    | riscv64        | Ubuntu 24.04 |
+--------+---------------+---------------+-----------------+----------------+--------------+

If Charmcraft executes on a RISC-V system, it filters the build plan to
only builds with a ``build-on`` of ``riscv64``. This means Charmcraft will only
pack the fourth binary.

If Charmcraft executes on an AMD64 system, it will build charms one, two and three.
This can be further filtered with the ``--platform`` argument or the
``CRAFT_PLATFORM`` environment variable. For example, running
``charmcraft pack --platform amd64-debug`` on an ``amd64`` system would pack
only the second binary.

.. _Debian's naming convention: https://wiki.debian.org/SupportedArchitectures
