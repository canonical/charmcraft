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

.. seealso::

  :external+ops:doc:`Ops | How to manage relations <howto/manage-relations>`

Integrate with a database
-------------------------

If you wish to integrate your 12-factor web app with PostgreSQL
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

.. _integrate-web-app-charm-integrate-ingress:


Integrate with ingress
----------------------

If you wish to integrate your 12-factor web app with an ingress,
for instance
`Nginx Ingress Integrator <https://charmhub.io/nginx-ingress-integrator>`_,
provide the integration to your deployed app with:

.. code-block:: bash

    juju integrate <app charm> nginx-ingress-integrator

You don't need to add an endpoint definition to your charm's
project file.

.. _integrate_web_app_cos:

Integrate with observability
----------------------------

You must prepare an ingress if you wish to integrate your 12-factor web app
with the `Canonical Observability Stack
(COS) <https://charmhub.io/topics/canonical-observability-stack>`_.
COS relies on the Traefik ingress to expose, for example, Grafana.
On MicroK8s, Traefik requires the MetalLB loadbalancer to be enabled which
requires an IP range. Provide the IP range and enable the addon with:

.. code-block:: bash

    IPADDR=$(ip -4 -j route get 2.2.2.2 | jq -r '.[] | .prefsrc')
    microk8s enable metallb:$IPADDR-$IPADDR


Deploy and integrate observability to the 12-factor app with:

.. code-block:: bash

    juju deploy cos-lite --trust
    juju integrate <app charm> grafana
    juju integrate <app charm> prometheus
    juju integrate <app charm> loki

You don't need to add endpoint definitions to your charm's
project file.
