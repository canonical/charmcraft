.. _select-platforms:

Select charm platforms
======================

The ``platforms`` and ``base`` keys in a charm's :ref:`charmcraft-yaml-file` select
both the OS releases and silicon architectures on which the charm
can build and run.

See the :doc:`Platforms reference </reference/platforms>` for more information.

Select an OS
------------

The project's :ref:`charmcraft-yaml-base` key defines the operating
system and version on which a charm can build and run. Supported OSs
vary by both the version of Charmcraft and the version of `Juju`_.

The general syntax for defining a distribution and series is to use
``base: <distribution>@<series>``. For example, a charm that runs on Ubuntu
24.04 LTS may be defined with the following ``base`` key:

.. code-block:: yaml

    base: ubuntu@24.04

Select one build and one target architecture
--------------------------------------------

The following snippet defines a charm that both builds and runs on Ubuntu 24.04 LTS,
only on an AMD64 architecture:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     amd64:
       build-on: [amd64]
       build-for: [amd64]

The ``build-on`` and ``build-for`` entries are identical, so the
:ref:`shorthand notation <reference-platforms-shorthand>` can be used:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     amd64:

The results are the same with either snippet. Building on AMD64 will
produce one charm that runs on an AMD64 Ubuntu 24.04 LTS system. Charmcraft
will not build the charm on other architectures.

.. note::

  The OS of the build system doesn't affect what is built. Using `LXD`_ or
  `Multipass`_ as a backend, Charmcraft will create a build environment with the
  correct OS.

Select one build architecture and target all architectures
----------------------------------------------------------

When crafting a charm that contains only architecture-independent code,
set ``build-for: [all]``. For example, the following project file snippet
packs a single charm on an AMD64 host while declaring support for any architecture:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     all:
       build-on: [amd64]
       build-for: [all]

The ``all`` key can only be used for the ``build-for`` key. If the charm can
be built on multiple architectures, they must be added to the ``build-on`` key:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     all:
       build-on: [amd64, riscv64]
       build-for: [all]

In this sample, building on AMD64 or 64-bit RISC-V will produce one charm that
runs on Ubuntu 24.04 LTS across all architectures.

.. important::

    Charmcraft does not check that the resulting charm is architecture-independent.
    It is up to the charm developer to ensure that the charm does not include any
    architecture-dependent code, including Python dependencies that contain
    compiled code.


Select multiple build and target architectures
----------------------------------------------

Charms may contain architecture-specific code and thus need separate artifacts
for each. You can declare multiple architectures in the ``platforms`` key,
which instructs Charmcraft to build a charm for each of them as a set. For
example, you could use the following snippet in your project to build
for both AMD64 and 64-bit RISC-V:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     amd64:
       build-on: [amd64]
       build-for: [amd64]
     riscv64:
       build-on: [riscv64]
       build-for: [riscv64]

Because the ``build-on`` and ``build-for`` entries are identical for each
platform, the shorthand notation can be used instead:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     amd64:
     riscv64:

The results are the same with either snippet. Building on AMD64 will
produce one charm that runs on AMD64. Building on RISC-V will produce
one charm that runs on RISC-V.

.. note::

    The ``build-for`` key may only contain one architecture, despite being a list.


Select different architectures for building and running
-------------------------------------------------------

A charm may require cross-compilation to build. To create a charm for a
different architecture, use the following snippet:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     riscv64-cross:
       build-on: [amd64]
       build-for: [riscv64]

Building on AMD64 will produce one charm that runs on ``riscv64``.

Note that the charm developer must ensure the charm is compatible with the
target architectures. By default, the `charm`_,
:ref:`python <craft_parts_python_plugin>`, :ref:`poetry <craft_parts_poetry_plugin>`,
and :ref:`uv <craft_parts_uv_plugin>` plugins will install wheels for python packages
for the ``build-on`` architecture rather than the ``build-for``. For more information,
see `craft-parts#974`_.

Select multiple OS releases
---------------------------

The resulting ``.charm`` file packed by charmcraft can only run on a single OS release
or ``base``, using ``charmcraft.yaml`` nomenclature. A project file can use multi-base
syntax to create multiple ``.charm`` files, each for a different base. To do this, the
base is defined in each platform entry instead of being defined with the top-level
``base`` and ``build-base`` keys.

To build a charm for Ubuntu 22.04 LTS and a charm for Ubuntu 24.04 LTS, use the
following snippet which uses :ref:`multi-base
notation<reference-platforms-multi-base>`:

.. code-block:: yaml

   platforms:
     ubuntu-22.04-amd64:
       build-on: [ubuntu@22.04:amd64]
       build-for: [ubuntu@22.04:amd64]
     ubuntu-24.04-amd64:
       build-on: [ubuntu@24.04:amd64]
       build-for: [ubuntu@24.04:amd64]

The ``build-on`` and ``build-for`` entries are identical for each platform, so
the :ref:`multi-base shorthand notation
<reference-platforms-multi-base-shorthand>` can be used:

.. code-block:: yaml

   platforms:
     ubuntu@22.04:amd64:
     ubuntu@24.04:amd64:

With both snippets, building on AMD64 will produce two charms, one for
AMD64 systems running Ubuntu 22.04 LTS and one for AMD64 systems running
Ubuntu 24.04 LTS.

.. _charm: https://juju.is/docs/sdk/charmcraft-yaml#heading--the-charm-plugin
.. _craft-parts#974: https://github.com/canonical/craft-parts/issues/974
