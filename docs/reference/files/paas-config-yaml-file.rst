.. meta::
    :description: Reference for how Charmcraft stages and validates paas-config.yaml in experimental V2 12-factor app charms.

.. _paas-config-yaml-file:

``paas-config.yaml`` file
=========================

The optional ``paas-config.yaml`` file configures runtime behavior in experimental
12-factor app charms targeting Ubuntu 26.04 LTS. Place the file in the charm folder
right beside ``charmcraft.yaml``.

When the file exists, the extension adds a ``config`` part that stages
``paas-config.yaml`` into the charm. When the file doesn't exist, the extension doesn't
generate the part. For bases 24.04 LTS and 22.04 LTS, the extension doesn't stage the
file through a separate config part.

Charmcraft validation
---------------------

Charmcraft validates the following properties when it expands the extension with base
26.04 LTS during ``charmcraft pack`` or ``charmcraft expand-extensions``:

* The file contains valid YAML.
* The top-level value is a mapping.
* ``framework_logging_format: json`` is used only with Flask, Django, or FastAPI.
* ``port`` and ``metrics-port`` are integers from 1 through 65535.
* ``metrics-path`` is a string that starts with ``/`` and is a valid RFC 3986 URL
  path.

The public top-level spellings are ``port``, ``metrics-port``, and ``metrics-path``.
Charmcraft doesn't validate other paas-charm settings beyond YAML structure and the
framework logging compatibility check.

For example:

.. code-block:: yaml
    :caption: paas-config.yaml

    port: 8080
    metrics-port: 9102
    metrics-path: /metrics
    framework_logging_format: json

Workload settings
-----------------

With base 26.04 LTS, the charm reads ``port``, ``metrics-port``, and ``metrics-path``
from the file and passes them to the workload. When you omit a value, the framework
default applies. The following table shows the defaults and how each framework receives
the values.

.. list-table::
    :header-rows: 1

    * - Framework
      - Port (default)
      - Metrics port (default)
      - Metrics path (default)
    * - Flask
      - 8000 (Gunicorn bind address)
      - ``FLASK_METRICS_PORT`` (9102)
      - ``FLASK_METRICS_PATH`` (``/metrics``)
    * - Django
      - 8000 (Gunicorn bind address)
      - ``DJANGO_METRICS_PORT`` (9102)
      - ``DJANGO_METRICS_PATH`` (``/metrics``)
    * - FastAPI
      - ``UVICORN_PORT`` (8000)
      - ``METRICS_PORT`` (8000)
      - ``METRICS_PATH`` (``/metrics``)
    * - Express
      - ``PORT`` (8080)
      - ``METRICS_PORT`` (9464)
      - ``METRICS_PATH`` (``/metrics``)
    * - Go
      - ``PORT`` (8080)
      - ``METRICS_PORT`` (8080)
      - ``METRICS_PATH`` (``/metrics``)
    * - Spring Boot
      - ``SERVER_PORT`` (8080)
      - ``management.server.port`` (8080)
      - ``management.endpoints.web.base-path`` and
        ``management.endpoints.web.path-mapping.prometheus``
        (``/actuator/prometheus``)

The `paas-config reference
<https://canonical.com/juju/docs/12-factor/latest/reference/paas-config/>`__ defines runtime defaults, framework
behavior, and the rest of the schema.
