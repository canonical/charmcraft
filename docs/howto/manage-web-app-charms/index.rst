.. _manage-12-factor-app-charms:

Manage a 12-factor app charm
============================

These guides walk you through all ways you can manage 12-factor app charms,
from initialization to usage.

:ref:`Extensions <profile>` add customized elements to a charm for specific
web app frameworks. While the overall basic logic is the same as
:ref:`managing a charm <manage-charms>`, the following guides are about
the 12-factor app charm workflow.

Initialization
--------------

.. _init-12-factor-charms:

You will need a rock for your 12-factor app charm.
:external+rockcraft:ref:`Prepare a 12-factor app rock <set-up-web-app-rock>`
with Rockcraft.

Once you have a rock, use ``charmcraft init`` and specify the relevant profile:

.. tabs::

    .. group-tab:: Django

        .. code-block:: bash

            charmcraft init --profile django-framework

    .. group-tab:: Express

        .. code-block:: bash

            charmcraft init --profile expressjs-framework

    .. group-tab:: FastAPI

        .. code-block:: bash

            charmcraft init --profile fastapi-framework

    .. group-tab:: Flask

        .. code-block:: bash

            charmcraft init --profile flask-framework

    .. group-tab:: Go

        .. code-block:: bash

            charmcraft init --profile go-framework

    .. group-tab:: Spring Boot

        .. code-block:: bash

            charmcraft init --profile spring-boot-framework

Charmcraft automatically creates a ``charmcraft.yaml`` project file, a
``requirements.txt`` file and source code for the charm in your current directory. You
will need to check the project file and ``README.md`` to verify that the charm's name
and description are correct.

Configuration
-------------

Once your 12-factor app charm has been set up, you can customize many aspects
of it using Juju.

.. toctree::
   :maxdepth: 2

   Configure your 12-factor app charm <configure-web-app-charm>

Integration
-----------

Once deployed, your 12-factor app can be integrated into nearly anything in the
Juju ecosystem.

.. toctree::
   :maxdepth: 2

   Integrate your 12-factor app charm <integrate-web-app-charm>

Usage
-----

Now that you've initialized and configured your 12-factor app charm, you're
ready to use it.


.. toctree::
   :maxdepth: 2

   Use your 12-factor app charm <use-web-app-charm>

