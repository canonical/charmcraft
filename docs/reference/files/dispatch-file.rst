.. _dispatch-file:

``dispatch``
============

The ``dispatch`` file in your charm the file `Juju`_ runs when an event occurs.

In most cases, is an executable shell script whose responsibility is to execute
``src/charm.py`` file within your charm's virtual environment.

The file is normally created automatically by ``charmcraft pack``, and you can
inspect it by extracting the ``.charm`` archive (``unzip <charm name>.charm``).
The template for the default dispatch script is available `on Github
<https://github.com/canonical/charmcraft/blob/main/charmcraft/dispatch.py>`_.

Overriding ``dispatch``
-----------------------

While it is not recommended, it is possible to override the dispatch script with
the file of your choice, simply by placing a file called ``dispatch`` in the root
directory of the charm. The only requirements are that the file have the executable
bit set in its file mode and that it be executable on the platform where the charm
will be deployed.

.. collapse:: Example charm with an overridden dispatch script

    The following :ref:`part` section added to any charm will replace the dispatch
    script with a script that does nothing (but successfully) upon any event.

    .. code-block:: yaml

        parts:
          dispatch:
            plugin: nil
            override-build: |
              echo "!#/bin/true" >> "$CRAFT_PART_INSTALL"/dispatch
