.. _src-charm-py-file:


``src/charm.py`` file
=====================

The ``src/charm.py`` file is the default entry point for a charm. This file must be
executable, and should include a `shebang
<https://en.wikipedia.org/wiki/Shebang_(Unix)>`_ to indicate the desired interpreter.

This file may contain all of the charm code. However, if possible, you should use a
separate module for workload-specific logic. See :ref:`src-workload-py-file`.

It is possible to rename ``src/charm.py``, but additional changes are then required to
build the charm with Charmcraft.
