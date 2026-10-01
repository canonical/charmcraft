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
project file of that particular application's charm. The key ``optional``
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

.. _integrate-web-app-charm-integrate-database:

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

Use an actively maintained ingress implementation,
such as the `Gateway API integrator
<https://charmhub.io/gateway-api-integrator>`__,
to expose your 12-factor web app outside the Kubernetes cluster.
First, follow the `Gateway API integrator deployment guide
<https://canonical.com/juju/docs/gateway-api-integrator-charm/latest/tutorial/getting-started/>`__
to deploy and configure the ingress charm.
Then, integrate it with your deployed app:

.. code-block:: bash

    juju integrate <APP_CHARM> gateway-api-integrator

You don't need to add an endpoint definition to your charm's
project file.

Handle a stripped URL prefix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ingress implementation can expose an app under a URL prefix
and strip the prefix before forwarding the request to the app.
The app must still know the external prefix to generate correct redirects,
links, static asset locations, and framework user interface URLs.

Ingress implementations communicate a stripped prefix differently.
Gateway API integrator and Traefik pass the stripped prefix in the
``X-Forwarded-Prefix`` header.
Nginx Ingress Integrator does not pass this header.
``X-Forwarded-Prefix`` is a commonly used proxy header,
not part of the standardized ``Forwarded`` header.

The generated charm also exposes the full external URL from the ingress relation
as ``DJANGO_BASE_URL`` for Django, ``FLASK_BASE_URL`` for Flask,
and ``APP_BASE_URL`` for the other frameworks.
When the ingress URL contains a prefix,
the app can extract its path component from this environment variable.

Configure your framework to account for the stripped prefix:

* **FastAPI with Uvicorn**: Extract the path from ``APP_BASE_URL``
  and pass it as the ASGI ``root_path``.
  Configure it on Uvicorn or the FastAPI app.
  FastAPI doesn't derive ``root_path`` from ``X-Forwarded-Prefix``.
  Setting ``root_path`` corrects generated URLs and the Swagger UI.

* **Django**: Extract the path from ``DJANGO_BASE_URL``
  and use it as ``FORCE_SCRIPT_NAME``.
  Django doesn't read ``X-Forwarded-Prefix`` by default,
  so header-driven configuration requires middleware.
  ``FORCE_SCRIPT_NAME`` takes precedence over a prefix supplied by the
  WSGI or ASGI server.

* **Flask with Gunicorn**: Extract the path from ``FLASK_BASE_URL``
  and supply it as the standard WSGI ``SCRIPT_NAME``,
  which Gunicorn accepts as an environment variable.
  For header-driven configuration, use Werkzeug ``ProxyFix`` with
  ``x_prefix`` set to the number of trusted proxies.
  ``ProxyFix`` converts ``X-Forwarded-Prefix`` to ``SCRIPT_NAME``,
  avoiding app-specific prefix code.

* **Spring Boot**: Set ``server.forward-headers-strategy=framework`` to use
  Spring's forwarded-header support.
  On Spring Boot versions that provide the setting,
  also set ``spring.mvc.forwarded-headers.use-forwarded-prefix=true``
  or ``spring.webflux.forwarded-headers.use-forwarded-prefix=true``.
  Other versions may require a configured ``ForwardedHeaderFilter``,
  ``ForwardedHeaderTransformer``, or custom ``WebFilter``.
  ``APP_BASE_URL`` provides the external URL for custom handling.
  Don't set ``server.servlet.context-path`` when the ingress strips the prefix,
  because the app then expects a prefix that the ingress removed
  and can return HTTP 404 errors.

* **Express**: Express has no native equivalent.
  Custom middleware can add the prefix to redirect ``Location`` headers.
  Use the path from ``APP_BASE_URL`` when handling redirects,
  static assets, and template links.

* **Go with ``net/http``**: The standard library has no native equivalent.
  Add middleware that wraps ``http.ResponseWriter`` and rewrites the
  ``Location`` header for redirects using the path from ``APP_BASE_URL``.

.. _integrate_web_app_cos:

Integrate with observability
----------------------------

You must prepare an ingress if you wish to integrate your 12-factor web app
with the `Canonical Observability Stack
(COS) <https://charmhub.io/topics/canonical-observability-stack>`_.
COS relies on the Traefik ingress to expose, for example, Grafana.
Traefik requires a load balancer to be enabled with an IP range. Provide the
IP range and enable the load balancer with:

.. tab-set::

    .. tab-item:: MicroK8s
        :sync: microk8s

        .. code-block:: bash

            IPADDR=$(ip -4 -j route get 2.2.2.2 | jq -r '.[] | .prefsrc')
            microk8s enable metallb:$IPADDR-$IPADDR

    .. tab-item:: Canonical K8s
        :sync: canonical-k8s

        .. code-block:: bash

            IPADDR=$(ip -4 -j route get 2.2.2.2 | jq -r '.[] | .prefsrc')
            sudo k8s set load-balancer.l2-mode=true load-balancer.cidrs=$IPADDR-$IPADDR
            sudo k8s enable load-balancer


Deploy and integrate observability to the 12-factor app with:

.. code-block:: bash

    juju deploy cos-lite --trust
    juju integrate <app charm> grafana
    juju integrate <app charm> prometheus
    juju integrate <app charm> loki

You don't need to add endpoint definitions to your charm's
project file.

.. _integrate_web_app_http_proxy:

Integrate with HTTP proxy
-------------------------

If you wish to integrate your 12-factor web app with
`Squid Forward Proxy <https://charmhub.io/squid-forward-proxy>`_, ensure the
following prerequisites are met:

1. Your web app needs to support basic proxy authentication within
the proxy URI (i.e., it must support the format
``scheme://username:password@proxy_value``).

2. The Squid Forward Proxy charm requires information about the proxy domains
and authentication modes supported by your web app. However, the 12 factor
framework currently does not provide a native way to set these values directly.

To supply the domains and authentication modes to the Squid Forward Proxy charm, `deploy
the HTTP proxy configurator charm
<https://github.com/canonical/http-proxy-operators/blob/main/http-proxy-configurator-operator/docs/tutorial/getting-started.md>`__.
Then, add the following endpoint definition to your project file:

.. code-block:: yaml

    requires:
      http-proxy:
        interface: http_proxy
        optional: True

Provide the integration to your deployed 12-factor app with:

.. code-block:: bash

    juju integrate <app charm> http-proxy-configurator

This integration creates the following environment variables you may use to
configure your 12-factor app.

- ``HTTP_PROXY``
- ``HTTPS_PROXY``

.. _integrate-web-app-charm-integrate-s3:

Integrate with S3
-----------------

If you wish to integrate your 12-factor web app with S3,
for instance using the
`S3 Integrator <https://charmhub.io/s3-integrator>`_,
add the following endpoint definition to your project file:

.. code-block:: yaml
    :caption: charmcraft.yaml

    requires:
      s3:
        interface: s3
        optional: True
        limit: 1

Then, integrate the charm in your deployed 12-factor app.

.. code-block:: bash

    juju integrate <app charm> s3-integrator

See the :ref:`framework's reference <extensions>` for a list of its exposed environment
variables.
