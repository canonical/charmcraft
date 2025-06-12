.. _init-12-factor-charms:

Initialize a 12-factor app charm
================================

Prepare an OCI image for a 12-factor app charm
----------------------------------------------

:external+rockcraft:ref:`Prepare a rock for a 12-factor app charm <set-up-web-app-rock>`
with Rockcraft.

Prepare a 12-factor app charm
-----------------------------

Use ``charmcraft init`` and specify the relevant profile:

.. code-block:: bash

  charmcraft init --profile <profile>

Charmcraft automatically creates a ``charmcraft.yaml`` project file, a
``requirements.txt`` file and source code for the charm in your current directory. You
will need to check the project file and ``README.md`` to verify that the charm's name
and description are correct.

    See also: :ref:`ref_commands_init`

.. tabs::

    .. group-tab:: Flask

        .. code-block:: bash

            charmcraft init --profile flask-framework

    .. group-tab:: Django

        .. code-block:: bash

            charmcraft init --profile django-framework

    .. group-tab:: FastAPI

        .. code-block:: bash

            charmcraft init --profile fastapi-framework

    .. group-tab:: Go

        .. code-block:: bash

            charmcraft init --profile go-framework
