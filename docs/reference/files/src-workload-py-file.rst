.. _src-workload-py-file:


``src/<workload>.py`` file
==========================

The ``src/<workload>.py`` file is a standalone Python module for workload-specific
logic. You can put helper functions in this file, or replace it if you already have a
Python module for interacting with your charm's workload. Charmcraft doesn't have any
requirements about the contents of this file.

The :ref:`ref_commands_init` command creates this file for the following profiles:

- ``kubernetes``
- ``machine``

The name of this file depends on the name of your charm. For example, if the name of
your charm is ``my-server-k8s``, Charmcraft creates ``src/my_server.py``.
