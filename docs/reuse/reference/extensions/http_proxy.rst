
HTTP Proxy
----------

Proxy settings can be sourced either from the model configurations or from the
``http-proxy`` relation. When the ``http-proxy`` relation is present, its
values take precedence over those defined in the model configuration. Charms
built using the |framework| extension automatically expose the Juju proxy
settings to the workload as the environment variables ``HTTP_PROXY``,
``HTTPS_PROXY`` and ``NO_PROXY``. The ``HTTP_PROXY`` and ``HTTPS_PROXY`` values
are obtained from the relation, whereas the ``NO_PROXY`` value is obtained from
the model configuration. For example, if the relation is absent, the
``juju-http-proxy`` environment variable will be exposed as ``HTTP_PROXY`` to
the |framework| service.

    See more:
    :external+juju:ref:`Juju | List of model configuration
    keys <list-of-model-configuration-keys>`,
    :ref:`How to integrate with HTTP Proxy <integrate_web_app_http_proxy>`
