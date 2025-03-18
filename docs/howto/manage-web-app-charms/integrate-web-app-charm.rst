.. _integrate-12-factor-charms:

Manage relations for a 12-factor app charm
==========================================

A charm integration can be added to your charmed 12-factor app by providing
the integration and endpoint definition in your project file:

.. code-block:: yaml
    :caption: charmcraft.yaml

    requires:
      <endpoint name>:
        interface: <endpoint interface name>
        optional: false

Here, ``<endpoint name>`` corresponds to the endpoint of the application with which
you want the integration, and ``<endpoint interface name>`` is the endpoint schema
to which this relation conforms. Both the ``<endpoint name>`` and
``<endpoint interface name>`` must coincide with the structs defined in the
pfoject file of that particular application's charm. The key ``optional``
with value ``False`` means that the charm will get blocked and stop the services if
the integration is not provided.

You can provide the integration to your deployed 12-factor app using:

.. code-block:: bash

    juju integrate <app charm> <endoint name>

After the integration has been established, the connection string and other
configuration options will be available as environment variables that you may
use to configure your 12-factor application.

For example, if you wish to integrate your 12-factor application with PostgreSQL
(`machine <https://charmhub.io/postgresql>`_ or
`k8s <https://charmhub.io/postgresql-k8s>`_
charm), add the following endpoint definition to your project file:

.. code-block:: yaml

    requires:
      postgresql:
        interface: postgresql_client
        optional: True

Provide the integration to your deployed 12-factor app with:

.. code-block:: bash

    juju integrate <app charm> postgresql

This integration creates the following environment variables you may use to
configure your 12-factor application.

- ``POSTGRESQL_DB_CONNECT_STRING``
- ``POSTGRESQL_DB_SCHEME``
- ``POSTGRESQL_DB_NETLOC``
- ``POSTGRESQL_DB_PATH``
- ``POSTGRESQL_DB_PARAMS``
- ``POSTGRESQL_DB_QUERY``
- ``POSTGRESQL_DB_FRAGMENT``
- ``POSTGRESQL_DB_USERNAME``
- ``POSTGRESQL_DB_PASSWORD``
- ``POSTGRESQL_DB_HOSTNAME``
- ``POSTGRESQL_DB_PORT``

    See also: :external+ops:doc:`Ops | How to manage relations <howto/manage-relations>`
