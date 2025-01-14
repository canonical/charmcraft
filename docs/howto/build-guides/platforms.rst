Build platform-specific charms
==============================

A ``charmcraft.yaml`` defines where charms are built and where charms are run
using the ``platforms``, ``base``, and ``build-base`` keywords.

See the :doc:`Platforms reference </reference/platforms>` for more information.

Create a charm for a specific base and architecture
---------------------------------------------------

To create a charm that will be built on an ``amd64`` system with Ubuntu 24.04
and will run on an ``amd64`` system with Ubuntu 24.04, use the
``charmcraft.yaml`` snippet below:

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

The results are the same with either snippet. Building on ``amd64`` will
produce one charm that runs on an ``amd64`` Ubuntu 24.04 system.

.. note::

  The OS of the build system doesn't affect what is built. Using LXD or
  Multipass as a backend, Charmcraft will create a build environment with the
  correct OS.

Create a charm for all architectures
------------------------------------

For charms that are architecture-independent, use the following
``charmcraft.yaml`` snippet to create a single charm that can run on any
architecture:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     all:
       build-on: [amd64]
       build-for: [all]

Building on ``amd64`` will produce one charm that runs on any architecture on
an Ubuntu 24.04 system.

The ``all`` keyword can only be used for the ``build-for`` keyword. If the
charm can be built on multiple architectures, they must be added to the
``build-on`` keyword:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     all:
       build-on: [amd64, riscv64]
       build-for: [all]

Building on ``amd64`` or ``riscv64`` will produce one charm that runs on all
architectures on Ubuntu 24.04 systems.


Create a set of charms for multiple architectures
-------------------------------------------------

Charms may contain architecture-specific code. To build charms for specific
architectures, use the following ``charmcraft.yaml`` snippet:

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

The results are the same with either snippet. Building on ``amd64`` will
produce one charm that runs on ``amd64``. Building on ``riscv64`` will produce
one charm that runs on ``riscv64``.


Create a charm for a different architecture
-------------------------------------------

A charm may require cross-compilation to build. To create a charm for a
different architecture, use the following ``charmcraft.yaml`` snippet:

.. code-block:: yaml

   base: ubuntu@24.04
   platforms:
     riscv64-cross:
       build-on: [amd64]
       build-for: [riscv64]

Building on ``amd64`` will produce one charm that runs on ``riscv64``.


Create a set of charms for multiple bases
------------------------------------------

A charm can only run on a single base. A ``charmcraft.yaml`` can use multi-base
syntax to create a set of charms, each for a different base. To do this, the
base is defined in each platform entry instead of being defined with the
top-level ``base`` and ``build-base`` keywords,

To build a charm for Ubuntu 22.04 and a charm for Ubuntu 24.04, use the
following ``charmcraft.yaml`` snippet which uses :ref:`multi-base
notation<reference-platforms-multi-base>`:

.. code-block:: yaml

   platforms:
     ubuntu-22.04-amd64:
       build-on: [amd64]
       build-for: [amd64]
     ubuntu-24.04-amd64:
       build-on: [amd64]
       build-for: [amd64]

The ``build-on`` and ``build-for`` entries are identical for each platform, so
the :ref:`multi-base shorthand notation
<reference-platforms-multi-base-shorthand>` can be used:

.. code-block:: yaml

   platforms:
     ubuntu@22.04:amd64:
     ubuntu@24.04:amd64:

With both snippets, building on ``amd64`` will produce two charms, one for
``amd64`` systems running Ubuntu 22.04 and one for ``amd64`` systems running
Ubuntu 24.04.
