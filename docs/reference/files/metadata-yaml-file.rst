.. _metadata-yaml-file:


``metadata.yaml`` file
======================

This document describes the ``metadata.yaml`` file in your charm project.

.. caution::

    Starting with Charmcraft 2.5, the ``metadata.yaml`` file is created
    automatically from information you provide in the :ref:`charmcraft-yaml-file`. For
    backwards compatibility, Charmcraft will continue to allow the use of the
    ``metadata.yaml`` file, but you may not duplicate keys across the two files.

.. important::

    The project file follows keywords similar to snaps, but
    ``metadata.yaml`` does not. As a result, when ``charmcraft pack`` generates
    the file, some keys may differ -- e.g., the project's ``title``  key from
    is rendered as ``display-name`` in ``metadata.yaml``.

This file contains identifying and configuration information about the charm.
Identifying information is used to describe the charm, its author, and its purpose; it
is indexed by `Charmhub`_ to enable easy discovery of charms. Configuration information
is provided by the charm author to inform `Juju`_ how and where to deploy the charm
depending on the intended platform, storage requirements, resources, and possible
integrations.

The file is a YAML dictionary and consists of a number of keys and their values. There
are 3 keys that are required for all charms: `name`_, `summary`_ , and `description`_.
Then, also keys that are required only for Kubernetes charms, e.g., `containers`_.
Additionally, 15+ optional keys. Finally, any number of arbitrary keys; these can serve
to keep track of other choices a charmer might make.

.. dropdown:: Minimal ``metadata.yaml``

    .. code-block:: yaml

        name: mongodb
        summary: A document database
        description: A database that stores JSON-like data.

.. dropdown:: ``metadata.yaml`` for a Kubernetes charm

    .. code-block:: yaml

        name: super-k8s
        summary: a really great charm
        description: |
          This is a really great charm, whose metadata is suitably complete so as to
          demonstrate as many of the fields as possible.
        maintainers:
          - Joe Bloggs <joe.bloggs@email.com>
        docs: https://discourse.charmhub.io/t/9999

        # The following three fields can be a single string, or a list of strings.
        source: https://github.com/foo/super-k8s-operator
        issues: https://github.com/foo/super-k8s-operator/issues/
        website:
          - https://charmed-super.io/k8s
          - https://super-app.io

        containers:
          super-app:
            resource: super-app-image
            mounts:
              - storage: logs
                location: /logs

          super-app-helper:
              bases:
                - name: ubuntu
                  channel: ubuntu/24.04
                  architectures:
                    - amd64
                    - arm64

        resources:
          super-app-image:
            type: oci-image
            description: OCI image for the Super App (hub.docker.com/_/super-app)

          definitions:
            type: file
            description: A small SQLite3 database of definitions needed by super app
            filename: definitions.db

        provides:
          super-worker:
            interface: super-worker

        requires:
          ingress:
            interface: ingress
            optional: true
            limit: 1

        peers:
          super-replicas:
            interface: super-replicas

        storage:
          logs:
            type: filesystem
            location: /logs
            description: Storage mount for application logs

        assumes:
          - juju >= 3.6.0
          - k8s-api

        charm-user: non-root

The rest of this document describes all these keys. Click on a key below or scroll down
to find out more.

.. dropdown:: Alternatively, expand to see the full spec at once

    .. code-block:: yaml

        # (Required) The name of the charm. Determines URL in Charmhub and the name administrators
        # will ultimately use to deploy the charm. E.g. `juju deploy <name>`
        name: <name>

        # (Required) A short, one-line description of the charm
        summary: <summary>

        # (Required) A full description of the configuration layer
        description: |
          <description>

        # (Optional) A list of maintainers in the format "First Last <email>"
        maintainers:
          - <maintainer>

        # (Optional) A string (or a list of strings) containing a link (or links) to project websites.
        # In general this is likely to be the upstream project website, or the formal website for the
        # charmed offering.
        website: <url> | [<urls>]

        # (Optional) A string (or a list of strings) containing a link (or links) to the charm source code.
        source: <url> | [<urls>]

        # (Optional) A string (or a list of strings) containing a link (or links) to the charm bug tracker.
        issues: <url> | [<urls>]

        # (Optional) A link to a documentation cover page on Discourse
        # More details at https://juju.is/docs/sdk/add-docs-to-your-charmhub-page
        docs: <url>

        # (Optional) A list of terms that any charm user must agree with
        terms:
          - <term>

        # (Optional) True if the charm is meant to be deployed as a subordinate to a
        # principal charm
        subordinate: true | false

        # (Optional) A map of containers to be created adjacent to the charm. This field
        # is required when the charm is targeting Kubernetes, where each of the specified
        # containers will be created as sidecars to the charm in the same pod.
        containers:
          # Each key represents the name of the container
          <container name>:
            # Note: One of either resource or bases must be specified.

            # (Optional) Reference for an entry in the resources field. Specifies
            # the oci-image resource used to create the container. Must not be
            # present if a base/channel is specified
            resource: <resource name>

            # (Optional) A list of bases in descending order of preference for use
            # in resolving a container image. Must not be present if resource is
            # specified. These bases are listed as base (instead of name) and
            # channel as in the Base definition, as an unnamed top-level object list
            bases:
                # Name of the OS. For example ubuntu/almalinux/opensuse
              - name: <base name>

                # Channel of the OS in format "track[/risk][/branch]" such as used by
                # Snaps. For example 20.04/stable or 18.04/stable/fips
                channel: <track[/risk][/branch]>

                # List of architectures that this particular charm can run on
                architectures:
                  - <architecture>

            # (Optional) List of mounted storages for this container
            mounts:
              # (Required) Name of the storage to mount from the charm storage
              - storage: <storage name>

                # (Optional) In the case of filesystem storages, the location to
                # mount the storage. For multi-stores, the location acts as the
                # parent directory for each mounted store.
                location: <path>

            # (Optional) UID to run the pebble entry process for this container as.
            # Can be any value from 0-999 or any value from 10,000 (values from 1000-9999 are reserved for users).
            # Default is 0 (root). Added in Juju 3.5.0.
            uid: <unix UID>

            # (Optional) GID to run the pebble entry process for this container as.
            # Can be any value from 0-999 or any value from 10,000 (values from 1000-9999 are reserved for user's primary groups).
            # Default is 0 (root). Added in Juju 3.5.0.
            gid: <unix GID>

        # (Optional) Additional resources that accompany the charm
        resources:
          # Each key represents the name of the resource
          <resource name>:

            # (Required) The type of the resource
            type: file | oci-image

            # (Optional) Description of the resource and its purpose
            description: <description>

            # (Required: when type:file) The filename of the resource as it should
            # appear in the filesystem
            filename: <filename>

        # (Optional) Map of relations provided by this charm
        provides:
          # Each key represents the name of the relation as known by this charm
          <relation name>:

            # (Required) The interface schema that this relation conforms to
            interface: <interface name>

            # (Optional) Maximum number of supported connections to this relation
            # endpoint. This field is an integer
            limit: <n>

            # (Optional) Defines if the relation is required. Informational only.
            optional: true | false

            # (Optional) The scope of the relation. Defaults to "global"
            scope: global | container

        # (Optional) Map of relations required by this charm
        requires:
          # Each key represents the name of the relation as known by this charm
          <relation name>:

            # (Required) The interface schema that this relation conforms to
            interface: <interface name>

            # (Optional) Maximum number of supported connections to this relation
            # endpoint. This field is an integer
            limit: <n>

            # (Optional) Defines if the relation is required. Informational only.
            optional: true | false

            # (Optional) The scope of the relation. Defaults to "global"
            scope: global | container

        # (Optional) Mutual relations between units/peers of this charm
        peers:
          # Each key represents the name of the relation as known by this charm
          <relation name>:

            # (Required) The interface schema that this relation conforms to
            interface: <interface name>

            # (Optional) Maximum number of supported connections to this relation
            # endpoint. This field is an integer
            limit: <n>

            # (Optional) Defines if the relation is required. Informational only.
            optional: true | false

            # (Optional) The scope of the relation. Defaults to "global"
            scope: global | container

        # (Optional) Storage requests for the charm
        storage:
          # Each key represents the name of the storage
          <storage name>:

            # (Required) Type of the requested storage
            type: filesystem | block

            # (Optional) Description of the storage requested
            description: <description>

            # (Optional) The mount location for filesystem stores. For multi-stores
            # the location acts as the parent directory for each mounted store.
            location: <location>

            # (Optional) Indicates if the storage should be made read-only (where possible)
            read-only: true | false

            # (Optional) The number of storage instances to be requested
            multiple: <n> | <n>-<m> | <n>- | <n>+

            # (Optional) Minimum size of requested storage in forms G, GiB, GB. Size
            # multipliers are M, G, T, P, E, Z or Y. With no multiplier supplied, M
            # is implied.
            minimum-size: <n>| <n><multiplier>

            # (Optional) List of properties, only supported value is "transient"
            properties:
              - transient

        # (Optional) Device requests for the charm, for example a GPU
        devices:
          # Each key represents the name of the device
          <device name>:

            # (Required) The type of device requested
            type: gpu | nvidia.com/gpu | amd.com/gpu

            # (Optional) Description of the requested device
            description: <description>

            # (Optional) Minimum number of devices required
            countmin: <n>

            # (Optional) Maximum number of devices required
            countmax: <n>

        # (Optional) Extra bindings for the charm. For example binding extra network
        # interfaces. Key only map, value must be blank. Key represents the name
        extra-bindings:
          # Key only map; key represents the name of the binding
          <binding name>:

        # (Optional) A set of features that must be provided by the Juju model to ensure that the charm can be successfully deployed.
        # See https://juju.is/docs/olm/supported-features for the full list.
        assumes:
          - <feature_name>
          - any-of:
            - <feature_name>
            - <feature_name>
          - all-of:
            - <feature_name>
            - <feature_name>

        # (Optional) What kind of user is required to run the charm code.
        # It can be one of root, sudoer or non-root.
        # Added in Juju 3.6.0. If not specified, root is assumed.
        charm-user: <one of root, sudoer or non-root>


``assumes``
-----------

.. Based on https://discourse.charmhub.io/t/assumes/5450#feature-names-and-version-constraints

**Status:** Optional. Recommended for Kubernetes charms.

**Purpose:** The ``assumes`` key  allows charm authors to explicitly state in the
metadata of a charm various features that a Juju model must be able to provide to ensure
that the charm can be successfully deployed on it. When a charm comes preloaded with
such requirements, this enables Juju to perform a pre-deployment check and to display
user-friendly error messages if a feature requirement cannot be met by the model that
the user is trying to deploy the charm to. If the assumes section of the charm metadata
is omitted, Juju will make a best-effort attempt to deploy the charm, and users must
rely on the output of ``juju status`` to figure out whether the deployment was
successful. The ``assumes`` key is available since 2.9.23.

**Structure:** The key consists of a list of features that can be given either directly
or, depending on the complexity of the condition you want to enforce, nested under one
or both of the boolean expressions ``any-of`` or ``all-of``, as shown below. In order
for a charm to be deployed, all entries in the ``assumes`` block must be satisfied.

.. code-block:: yaml

    assumes:
      - <feature_name>
      - any-of:
        - <feature_name>
        - <feature_name>
      - all-of:
        - <feature_name>
        - <feature_name>

The supported feature names are as below:

.. list-table::

    * - ``juju <comparison predicate> <version number>`` E.g., ``juju < 3.0``
      - The charm deploys if and only if the model runs agent binaries with the
        specified Juju version(s).
      - Since 2.9.23
    * - ``k8s-api``
      - The charm deploys if and only if the underlying substrate for the model
        is Kubernetes.
      - Since 2.9.23

The Boolean expressions are defined as below:

.. list-table::

    * - ``any-of``
      - The sub-expression is satisfied if any of the provided child expressions is
        satisfied.
    * - ``all-of``
      - The sub-expression is satisfied if all of the provided
        child expressions are satisfied.

Examples:

.. dropdown:: Simple example

    .. code-block:: yaml

        assumes:
          - juju >= 2.9.23
          - k8s-api

.. dropdown:: Example with a nested expression

    .. code-block:: yaml

        assumes:
          - any_of:
            - juju >= 2.9
            - k8s-api


``charm-user``
--------------

.. important::

    ``charm-user`` was added in Juju 3.6.0. It's currently only supported by
    Kubernetes charms and has no effect on machine charms.

**Status:** Optional. Recommended for Kubernetes charms.

**Purpose:** The ``charm-user`` key  allows charm authors to specify that their charm
hook code does not need to be run as root. This key, in combination with ``uid`` and
``gid`` fields in ``containers``, allows the charm to be run rootless. If set to
``root``, the charm runs as root. If set to ``sudoer`` or ``non-root``, the charm runs
as a user other than root. If the value is ``sudoer``, the charm will be run as a user
with access to sudo to elevate its privileges.

**Structure:** The key consists of a single value. One of ``root``, ``sudoer`` or
``non-root``.

.. code-block:: yaml

    # (Optional) What kind of user is required to run the charm code.
    # It can be one of root, sudoer or non-root.
    # Added in Juju 3.6.0. If not specified, root is assumed.
    charm-user: <one of root, sudoer or non-root>


``containers``
--------------

    See also: `resources <#resources>`_

**Status:** Required for Kubernetes charms (except for proxy charms running on
Kubernetes).

**Purpose:** The ``containers`` key allows you to define a map of containers to be
created adjacent to the charm (as a sidecar, in the same pod).

**Structure:** This key consists of a list of containers along with their specification.
Each container can be specified in terms of ``resource``, ``bases``, ``uid``, ``gid``
and ``mounts``, where one of either the ``resource`` or the ``bases`` subkeys must be
defined, and ``mounts`` is optional. ``resource`` stands for the OCI image resource used
to create the container; to use it, specify  an OCI image resource name (that you will
then define further in the `resources`_ block). ``bases`` is a list of bases to be used
for resolving a container image, in descending order of preference; to use it, specify a
base name (for example, ``ubuntu``, ``almalinux``, ``opensuse``), a
`channel <https://snapcraft.io/docs/channels>`_, and an architecture. ``mounts`` is a
list of mounted storages for this container; to use it, specify the name of the storage
to mount from the charm storage and, optionally, the location where to mount the
storage. And, starting with Juju 3.5.0, ``uid`` and ``gid`` are the UID and,
respectively, GID to run the Pebble entry process for this container as; they can be any
value from 0-999 or any value from 10,000 (values from 1000-9999 are reserved for users)
and the default is 0 (root).

.. code-block:: yaml

    containers:
      <container name>:
        resource: <resource name>
        bases:
          - name: <base name>
            channel: <track{ref}`/risk][/branch]>
            architectures:
              - <architecture>
        mounts:
          - storage: <storage name>
            location: <path>
        uid: <unix UID>
        gid: <unix GID>

.. # (Optional) A map of containers to be created adjacent to the charm. This field
.. # is required when the charm is targeting Kubernetes, where each of the specified
.. # containers will be created as sidecars to the charm in the same pod.
.. # Exception: Proxy charms running on Kubernetes.
.. containers:
..     # Each key represents the name of a container.
..     <container name>:
..         # Note: One of either ''resource' or 'bases' must be specified.
..         # If you choose 'resource', make sure to define it under the top-level
..         # 'resources' key.

..         # (Optional) Reference for an entry in the resources field. Specifies
..         # the oci-image resource used to create the container. Must not be
..         # present if a base/channel is specified.
..         resource: <resource name>

..         # (Optional) A list of bases in descending order of preference for use
..         # in resolving a container image. Must not be present if resource is
..         # specified. These bases are listed as base (instead of name) and
..         # channel as in the Base definition, as an unnamed top-level object list
..         bases:
..             # Name of the OS. For example ubuntu/almalinux/opensuse
..             - name: <base name>

..               # Channel of the OS in format "track[/risk][/branch]" such as used by
..               # Snaps. For example 20.04/stable or 18.04/stable/fips
..               channel: <track[/risk][/branch]>

..               # List of architectures that this particular charm can run on
..               architectures:
..                   - <architecture>

..         # (Optional) List of mounted storages for this container
..         mounts:
..             # (Required) Name of the storage to mount from the charm storage
..             - storage: <storage name>

..               # (Optional) In the case of filesystem storages, the location to
..               # mount the storage. For multi-stores, the location acts as the
..               # parent directory for each mounted store.
..               location: <path>

..         # (Optional) UID to run the pebble entry process for this container as.
..         # Can be any value from 0-999 or any value from 10,000 (values from
..         # 1000-9999 are reserved for users).
..         # Default is 0 (root). Added in Juju 3.5.0.
..         uid: <unix UID>

..         # (Optional) GID to run the pebble entry process for this container as.
..         # Can be any value from 0-999 or any value from 10,000 (values from
..         # 1000-9999 are reserved for user's primary groups).
..         # Default is 0 (root). Added in Juju 3.5.0.
..         gid: <unix GID>

.. dropdown:: Example

.. code-block:: yaml

    containers:
        super-app:
          resource: super-app-image
          mounts:
            - storage: logs
              location: /logs


``description``
---------------

**Status:** Required.

**Purpose:** The ``description`` key is where you provide a full description of the
configuration layer.

**Structure:**

.. code-block:: yaml

    # (Required) A full description of the configuration layer
    description: |
      <description>


``devices``
-----------

.. code-block:: yaml

    # (Optional) Device requests for the charm, for example a GPU
    devices:
      # Each key represents the name of the device
      <device name>:

        # (Required) The type of device requested
        type: gpu | nvidia.com/gpu | amd.com/gpu

        # (Optional) Description of the requested device
        description: <description>

        # (Optional) Minimum number of devices required
        countmin: <n>

        # (Optional) Maximum number of devices required
        countmax: <n>


``display name``
----------------

.. important::

    In the :ref:`project file <charmcraft-yaml-file>`, this is now the ``title`` key.

.. code-block:: yaml

    display-name: |
      <display name>


``docs``
--------

    See also: `How to create an effective README file for your charm
    <https://juju.is/docs/sdk/charm-documentation>`_

.. important::

    In the :ref:`project file <charmcraft-yaml-file>`, this is now the
    ``links.documentation`` key.

.. code-block:: yaml

    # (Optional) A link to a documentation cover page on Discourse:
    docs: <url>


``extra-bindings``
------------------

.. code-block:: yaml

    # (Optional) Extra bindings for the charm. For example binding extra network
    # interfaces. Key only map, value must be blank. Key represents the name.
    extra-bindings:
      # Key only map; key represents the name of the binding
      <binding name>:


``issues``
----------

.. important::

    In the :ref:`project file <charmcraft-yaml-file>`, this is now the ``links.issues``
    key.

.. code-block:: yaml

    # (Optional) A string (or a list of strings) containing a link (or links) to the charm
    # bug tracker.
    issues: <url> | {ref}`<urls>]


``maintainers``
---------------

.. important::

    In :ref:`the project file <charmcraft-yaml-file>`, this is now the ``links.contact``
    key.

.. code-block:: yaml

    # (Optional) A list of maintainers in the format "First Last <email>"
    maintainers:
        - <maintainer>


``name``
--------

.. code-block:: yaml

    # (Required) The name of the charm. Determines URL in Charmhub and the name
    # administrators will ultimately use to deploy the charm. E.g. `juju deploy <name>`
    name: <name>


``peer``
--------

.. code-block:: yaml

    # (Optional) Mutual relations between units/peers of this charm
    peer:
      # Each key represents the name of the relation as known by this charm
      <relation name>:

        # (Required) The interface schema that this relation conforms to
        interface: <interface name>

        # (Optional) Maximum number of supported connections to this relation
        # endpoint. This field is an integer
        limit: <n>

        # (Optional) Defines if the relation is required. Informational only.
        optional: true | false

        # (Optional) The scope of the relation. Defaults to "global"
        scope: global | container


``provides``
------------

.. code-block:: yaml

    # (Optional) Map of relations provided by this charm
    provides:
      # Each key represents the name of the relation as known by this charm
      <relation name>:

        # (Required) The interface schema that this relation conforms to
        interface: <interface name>

        # (Optional) Maximum number of supported connections to this relation
        # endpoint. This field is an integer
        limit: <n>

        # (Optional) Defines if the relation is required. Informational only.
        optional: true | false

        # (Optional) The scope of the relation. Defaults to "global"
        scope: global | container


``requires``
------------

.. code-block:: yaml

    # (Optional) Map of relations required by this charm
    requires:
      # Each key represents the name of the relation as known by this charm
      <relation name>:

        # (Required) The interface schema that this relation conforms to
        interface: <interface name>

        # (Optional) Maximum number of supported connections to this relation
        # endpoint. This field is an integer
        limit: <n>

        # (Optional) Defines if the relation is required. Informational only.
        optional: true | false

        # (Optional) The scope of the relation. Defaults to "global"
        scope: global | container


``resources``
-------------

    See also: `Juju | Resource (charm) <https://juju.is/docs/juju/charm-resource>`_

**Structure:**

.. code-block:: yaml

    # (Optional) Additional resources that accompany the charm
    resources:
      # Each key represents the name of a resource
      # mentioned in the 'resource' subkey of the 'containers' key.
      <resource name>:

        # (Required) The type of the resource
        type: file | oci-image

        # (Optional) Description of the resource and its purpose
        description: <description>

        # (Required: when type:file) The filename of the resource as it should
        # appear in the filesystem
        filename: <filename>

.. dropdown:: Example with an OCI-image resource

    .. code-block:: yaml

        resources:
          super-app-image:
            type: oci-image
            description: OCI image for the Super App (hub.docker.com/_/super-app)


``source``
----------

.. important::

    In the :ref:`project file <charmcraft-yaml-file>`, this is now the ``links.source``
    key.

.. code-block:: yaml

    # (Optional) A string (or a list of strings) containing a link (or links) to the charm source code.
    source: <url> | {ref}`<urls>]


``storage``
-----------

.. code-block:: yaml

    # (Optional) Storage requests for the charm
    storage:
      # Each key represents the name of the storage
      <storage name>:

        # (Required) Type of the requested storage
        type: filesystem | block

        # (Optional) Description of the storage requested
        description: <description>

        # (Optional) The mount location for filesystem stores. For multi-stores
        # the location acts as the parent directory for each mounted store.
        location: <location>

        # (Optional) Indicates if the storage should be made read-only (where possible)
        read-only: true | false

        # (Optional) The number of storage instances to be requested
        multiple:
          range: <n> | <n>-<m> | <n>- | <n>+

        # (Optional) Minimum size of requested storage in forms G, GiB, GB. Size
        # multipliers are M, G, T, P, E, Z or Y. With no multiplier supplied, M
        # is implied.
        minimum-size: <n>| <n><multiplier>

        # (Optional) List of properties, only supported value is "transient"
        properties:
          - transient


``subordinate``
---------------

.. code-block:: yaml

    # (Optional) True if the charm is meant to be deployed as a subordinate to a
    # principal charm
    subordinate: true | false


``summary``
-----------

.. code-block:: yaml

    # (Required) A short, one-line description of the charm
    summary: <summary>


``terms``
---------

.. code-block:: yaml

    # (Optional) A list of terms that any charm user must agree with
    terms:
      - <term>


``website``
-----------

.. important::

    In :literalref:`charmcraft.yaml <charmcraft-yaml-file>`,
    this is now the ``links.website`` key.

.. code-block:: yaml

    # (Optional) A string (or a list of strings) containing a link (or links) to project
    # websites. In general this is likely to be the upstream project website, or the
    # formal website for the charmed offering.
    website: <url> | [<urls>]


Other keys
----------

In addition to the keys mentioned above, a ``metadata.yaml`` file may also contain other
arbitrary keys. These can serve to keep track of other choices a charmer might make. In
some cases these become semi-official, being adopted by many charmers and even
incorporated into CI processes. One such example is ``upstream-source``:

.. code-block:: yaml

    # The upstream-source field is ignored by Juju. It is included here as a reference
    # so the integration testing suite knows which image to deploy during testing. This
    # field is also used by the 'canonical/charming-actions' Github action for automated
    # releasing.
    upstream-source: kennethreitz/httpbin
