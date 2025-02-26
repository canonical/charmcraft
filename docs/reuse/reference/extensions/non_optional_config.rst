
In addition to this, you can set the configuration option to be
mandatory by setting the ``optional`` key to ``false``. This will
block the charm and stop services until the configuration is supplied. For example,
if your application needs an ``api-token`` to function correctly you can set
``optional``, as shown below. This will block the charm and stop the
services until the ``api-token`` configuration is supplied.

.. code-block:: yaml
    :caption: charmcraft.yaml

    config:
      options:
        api-token:
          description: The token necessary for the service to run.
          type: string
          optional: false

.. note::

    A configuration with ``optional: false`` can't also have a ``default`` key.
    If it has both, the charm will fail to pack.
