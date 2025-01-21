.. _src-charm-py-file:


``src/charm.py`` file
=====================

The ``src/charm.py`` file is the default entry point for a charm. This file must be
executable, and should include a `shebang
<https://en.wikipedia.org/wiki/Shebang_(Unix)>`_ to indicate the desired interpreter.
For many charms, this file will contain the majority of the charm code. It is possible
to change the name of this file, but additional changes are then required to build the
charm with Charmcraft.
