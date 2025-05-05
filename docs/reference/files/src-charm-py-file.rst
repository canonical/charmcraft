.. _src-charm-py-file:


``src/charm.py`` file
=====================

The ``src/charm.py`` file is the default entry point for a charm. This file must be
executable, and should include a `shebang
<https://en.wikipedia.org/wiki/Shebang_(Unix)>`_ to indicate the desired interpreter.

This file may contain all of the charm's code. It's better practice, however, to use a
separate module for workload-specific logic. If you don't already have a Python module
for interacting with your charm's workload, we recommend that you store workload code in
a :ref:`workload file <src-workload-py-file>`.

    See more: :external+ops:ref:`Ops | Design your Python modules
    <design-your-python-modules>`

It's possible to rename ``src/charm.py``, but additional changes are then required to
build the charm with Charmcraft. Specifically, you'll need to use the ``charm`` plugin
and specify ``charm-entrypoint``. For more information, see
:ref:`charmcraft-yaml-key-parts`.
