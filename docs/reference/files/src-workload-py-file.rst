.. _src-workload-py-file:


``src/<workload>.py`` file
==========================

The ``src/<workload>.py`` file is an optional, standalone Python module in which you can
add custom workload logic to a charm.

Charmcraft doesn't have any requirements about the file's contents. You can, as a common
example, insert helper functions for your workload.

    See more: :external+ops:ref:`Ops | Design your Python modules
    <design-your-python-modules>`

If you already have a Python module for interacting with your charm's workload, you can
ignore this file.

If you run the :ref:`ref_commands_init` command with either profile, Charmcraft
automatically creates this file for ``kubernetes`` and ``machine`` profiles.

The name of this file depends on the name of your charm. For example, if the name of
your charm is ``my-server-k8s``, Charmcraft creates ``src/my_server.py``.
