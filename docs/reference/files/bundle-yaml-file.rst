.. _bundle-yaml-file:

``bundle.yaml`` file
====================

.. important::

    Bundles are being phased out. Starting 1 Jan 2025, charm authors can no longer
    register new bundles.

..

    See also: :external+juju:ref:`Juju | Bundle <bundle>`

    Source for the keys used by Juju:
    `Schema <https://github.com/juju/charm/blob/v12/bundledata.go>`_,
    `Examples from test files
    <https://github.com/juju/charm/blob/v12/bundledata_test.go>`_

    The metadata keys ``docs``, ``issues``, ``source``, and ``website`` are
    only used by Charmhub.

File ``<bundle>.yaml`` is the file in your bundle directory where you define
your bundle.

.. important::

    ``bundle.yaml`` is typically generated using
    :external+juju:ref:`Juju's export-bundle command <command-juju-export-bundle>`.

**For overlay bundles:**

- Instead of providing overlays as external files, you may alternatively leverage
  Juju's support for multi-document YAML files and provide both the base overlay
  and any required overlays as a *single file*, appending the contents of the
  overlay after the base bundle using the special YAML document separator token
  ``---`` as the delimiter. Juju will treat the first document as the base bundle
  and any subsequent document as an overlay.


  .. collapse:: Example base and overlay in the same file

      .. code-block:: yaml

          applications:
            mysql:
              charm: "mysql"
              num_units: 1
              to: ["lxd:wordpress/0"]
          --- # This is part of overlay 1
          applications:
            mysql:
              num_units: 1
          --- # This is part of overlay 2
          applications:
            mysql:
              trust: true

- Relative paths are resolved relative to the path of the entity that describes them.
  That is, relative to the overlay bundle file itself.
- An application is removed from the base bundle by defining the application name
  in the application section, but omitting any values. Removing an application also
  removes all the relations for that application.
- If a machines section is specified in an overlay bundle, it replaces the
  corresponding section of the base bundle. No merging of machine information is
  attempted. Multiple overlay bundles can be specified and they are processed in
  the order they appear on the command line.
- Overlays can include new integrations, which are normally required for any new
  charms which have been added. Existing integrations cannot be removed however,
  except in the case where the referenced application is also removed by the overlay.

.. collapse:: Example bundle file for Kubernetes

    .. code-block:: yaml

        bundle: kubernetes
        applications:
          postgresql:
            charm: postgresql-k8s
            scale: 3
            constraints: mem=1G
            storage:
              database: postgresql-pv,20M
          mattermost:
            charm: mattermost-k8s
            placement: foo=bar
            scale: 1
        relations:
          - - postgresql:db
            - mattermost:db

.. collapse:: Example bundle file for machines

    A bundle for deployment on machines, for example, the `kubernetes-core <https://jaas.ai/kubernetes-core/>`_ bundle, looks as follows:

    .. code-block:: yaml

        description: A highly-available, production-grade Kubernetes cluster.
        issues: https://bugs.launchpad.net/charmed-kubernetes-bundles
        series: jammy
        source: https://github.com/charmed-kubernetes/bundle
        website: https://ubuntu.com/kubernetes/charmed-k8s
        name: charmed-kubernetes
        applications:
          calico:
            annotations:
              gui-x: '475'
              gui-y: '605'
            channel: 1.26/stable
            charm: calico
            options:
              vxlan: Always
          containerd:
            annotations:
              gui-x: '475'
              gui-y: '800'
            channel: 1.26/stable
            charm: containerd
          easyrsa:
            annotations:
              gui-x: '90'
              gui-y: '420'
            channel: 1.26/stable
            charm: easyrsa
            constraints: cores=1 mem=4G root-disk=16G
            num_units: 1
          etcd:
            annotations:
              gui-x: '800'
              gui-y: '420'
            channel: 1.26/stable
            charm: etcd
            constraints: cores=2 mem=8G root-disk=16G
            num_units: 3
            options:
              channel: 3.4/stable
          kubeapi-load-balancer:
            annotations:
              gui-x: '450'
              gui-y: '250'
            channel: 1.26/stable
            charm: kubeapi-load-balancer
            constraints: cores=1 mem=4G root-disk=16G
            expose: true
            num_units: 1
          kubernetes-control-plane:
            annotations:
              gui-x: '800'
              gui-y: '850'
            channel: 1.26/stable
            charm: kubernetes-control-plane
            constraints: cores=2 mem=8G root-disk=16G
            num_units: 2
            options:
              channel: 1.26/stable
          kubernetes-worker:
            annotations:
              gui-x: '90'
              gui-y: '850'
            channel: 1.26/stable
            charm: kubernetes-worker
            constraints: cores=2 mem=8G root-disk=16G
            expose: true
            num_units: 3
            options:
              channel: 1.26/stable
        relations:
        - - kubernetes-control-plane:loadbalancer-external
          - kubeapi-load-balancer:lb-consumers
        - - kubernetes-control-plane:loadbalancer-internal
          - kubeapi-load-balancer:lb-consumers
        - - kubernetes-control-plane:kube-control
          - kubernetes-worker:kube-control
        - - kubernetes-control-plane:certificates
          - easyrsa:client
        - - etcd:certificates
          - easyrsa:client
        - - kubernetes-control-plane:etcd
          - etcd:db
        - - kubernetes-worker:certificates
          - easyrsa:client
        - - kubeapi-load-balancer:certificates
          - easyrsa:client
        - - calico:etcd
          - etcd:db
        - - calico:cni
          - kubernetes-control-plane:cni
        - - calico:cni
          - kubernetes-worker:cni
        - - containerd:containerd
          - kubernetes-worker:container-runtime
        - - containerd:containerd
          - kubernetes-control-plane:container-runtime


The rest of this document describes each key in this file.

.. note::

    A bundle for deployment on Kubernetes differs from a standard bundle in the
    following ways:

    - key ``bundle`` is given the value of ``kubernetes``
    - key ``num_units`` is replaced by key ``scale``
    - key ``to`` is replaced by key ``placement``

    The value of ``placement`` is a key=value pair and is used as a Kubernetes
    node selector.


``applications``
----------------

**Purpose:** Holds all the applications in your bundle.

**Value:** Mapping. Keys are application names.


``applications.<application>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Holds an application definition.

**Name:** The name of the application. User-defined, usually identical to
`applications.<application>.charm`_


``applications.<application>.annotations``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Affects the GUI only. It provides horizontal and vertical placement of the
application's icon on the GUI's canvas. Annotations are expressed in terms of ``x``
and ``y`` coordinates.

.. collapse:: Example

    .. code-block:: yaml

        annotations:
          gui-x: 450
          gui-y: 550


``applications.<application>.base``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Missing content?


``applications.<application>.bindings``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Maps endpoints to network spaces. Used to constrain relations to specific subnets in
environments where machines have multiple network devices. The empty (``""``) key
represents all endpoints and can be used to specify the default space for any endpoint
that is not explicitly bound to a space.

.. collapse:: Example

    .. code-block:: yaml

        bindings:
          "": alpha
          kube-api-endpoint: internal
          loadbalancer: dmz


``applications.<application>.channel``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** States what the preferred channel should be used when deploying a
non-local charm.

.. note::

    Charmhub charms expect ``<track>/<risk>/<branch>`` format (e.g.,
    ``latest/stable``).

.. collapse:: Example

    .. code-block:: yaml

        channel: latest/edge


``applications.<application>.charm``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** States what charm to use for the application.

**If you're defining a public bundle:** Use a fully qualified charm URI.

.. collapse:: Example

    .. code-block:: yaml

        charm: containers-easyrsa


``applications.<application>.constraints``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets standard constraints for the application. As per normal behaviour, these become
the application's default constraints (i.e. units added subsequent to bundle
deployment will have these constraints applied).

.. collapse:: Examples

    .. code-block:: yaml

        constraints: root-disk=8G

    .. code-block:: yaml

        constraints: cores=4 mem=4G root-disk=16G

    .. code-block:: yaml

        constraints: zones=us-east-1a

    .. code-block:: yaml

        constraints: "arch=amd64 mem=4G cores=4"


``applications.<application>.devices``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Missing content?


``applications.<application>.expose``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Whether to expose the application to the outside network. Default is ``false``.

In order to use the granular per-endpoint expose settings feature by specifying an
"exposed-endpoints" section, the expose field must either be set to ``false`` or
omitted from the bundle.

.. collapse:: Example

    .. code-block:: yaml

        expose: true


``applications.<application>.exposed-endpoints``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Specifies the set of CIDRs and/or spaces that are allowed to access the port ranges
opened by the application. Expose settings can be specified both for the entire
application using the wildcard (``""``) key and for individual endpoints.

.. note::

    This is a deployment-specific field and can only be specified as part of an overlay.

Operators can control the expose parameters (CIDRs and/or spaces that are allowed
access to the port ranges opened by exposed applications) for the entire application
and/or on a per-endpoint basis.

Application expose parameters can also be specified in bundles. However, as expose
parameters are deployment-specific, they can only be provided as part of an overlay.
Consider the following multi-document bundle:

.. code-block:: yaml

    applications:
      mysql:
        charm: "mysql"
        num_units: 1
    --- # overlay
    applications:
      mysql:
        exposed-endpoints:
          "":
            expose-to-cidrs:
            - 0.0.0.0/0
            - ::/0
          db-admin:
            expose-to-spaces:
            - dmz
            expose-to-cidrs:
            - 192.168.0.0/24

This is equivalent to the following commands:

.. code-block:: bash

    juju deploy mysql
    juju expose mysql --to-cidrs 0.0.0.0/0,::/0
    juju expose mysql --endpoints db-admin --to-spaces dmz --to-cidrs 192.168.0.0/24

As a result of the above commands, the mysql application will be exposed and:

- All port ranges opened by the charm for any endpoint **except** ``db-admin`` will be
  reachable by **any** IP address.
- Port ranges opened by the charm for the ``db-admin`` endpoint will only be reachable
  by IPs that are part of the ``192.168.0.0/24`` block or belong to a subnet associated
  with the ``dmz`` space.

.. note::

    When using this particular feature, the bundle must not also contain an
    ``expose: true`` field or Juju will display an error when attempting to deploy the
    bundle.

    This constraint prevents operators from accidentally exposing **all** ports for an
    application when attempting to deploy such a bundle to a pre 2.9 controller as older
    controllers would honor the ``expose: true`` flag but would not interpret the
    ``exposed-endpoints`` field.

    In addition, Juju 2.9 (and newer) clients will also display an error when
    attempting to deploy a bundle containing an ``exposed-endpoints`` section to a
    pre-2.9 controller.


``applications.<application>.num_units``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** Specifies the number of units to deploy.

**Value:** Integer = the number of units.

**Default:** ``0``

.. collapse:: Example

    .. code-block:: yaml

        num_units: 2


``applications.<application>.offers``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Specifies a list of offers for the application endpoints that can be consumed by other
models. Each offer entry is identified by a unique name and must include a list of
application endpoints to be exposed as part of the offer. In addition, each offer may
optionally define an ``acl`` block to control, on a per-user level, the permissions
granted to the consumer side. The ``acl`` block keys are user names and values are
permission levels.

.. note::

    This is a deployment-specific field and can only be specified as part of an overlay.

.. collapse:: Example

    .. code-block:: yaml

        offers:
          my-offer:
            endpoints:
            - apache-website
            acl:
              admin: admin
              user1: read


``applications.<application>.options``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets configuration options for the application. The keys are application-specific and
are found within the corresponding charm's metadata.yaml file. An alias (a string
prefixed by an asterisk) may be used to refer to a previously defined anchor (see the
`variables`_ element).

.. collapse:: Example

    .. code-block:: yaml

        options:
          osd-devices: /dev/sdb
          worker-multiplier: *worker-multiplier

Values for options and annotations can also be read from a file. For binary files,
such as binary certificates, there is an option to base64-encode the contents. A file
location can be expressed with an absolute or relative (to the bundle file) path.

.. collapse:: Example

    .. code-block:: yaml

        applications:
          my-app:
            charm: some-charm
            options:
              config: include-file://my-config.yaml
              cert: include-base64://my-cert.crt


``applications.<application>.placement``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Missing content?


``applications.<application>.plan``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is for third-party Juju support only. It sets the "managed solutions" plan for
the application. The string has the format ``<reseller-name>/<plan name>``

.. collapse:: Example

    .. code-block:: yaml

        plan: acme-support/default


``applications.<application>.resources``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** States what charm resource to use.

**Value:** Map. Keys are individual resources.

Bundles support charm resources through the use of the ``resources`` key.
Consider the following charm ``metadata.yaml`` file that includes a
resource called ``pictures``:

.. code-block:: yaml

    name: example-charm
    summary: "example charm."
    description: This is an example charm.
    resources:
      pictures:
        type: file
        filename: pictures.zip
        description: "This charm needs pictures.zip to operate"

It might be desirable to use a specific resource revision in a bundle:

.. code-block:: yaml

    applications:
      example-charm:
        charm: "example-charm"
        series: trusty
        resources:
          pictures: 1

So here we specify a revision of ``1`` from Charmhub.

The ``resources`` key can also specify a local path to a resource instead:

.. code-block:: yaml

    applications:
      example-charm:
        charm: "example-charm"
        series: trusty
        resources:
          pictures: "./pictures.zip"

Local resources can be useful in network restricted environments where the controller
is unable to contact Charmhub.


``applications.<application>.resources.<resource>``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** Defines individual resources.

**Name:** Application specific. Cf. the charm's ``metadata.yaml``.

**Value:**  Integer (the resource revision stored in the Charmhub) or String (absolute
or relative file path to local resource).

.. collapse:: Examples

    .. code-block:: yaml

        easyrsa: 5

    .. code-block:: yaml

        easyrsa: ./relative/path/to/file


``applications.<application>.revision``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** States the revision of the charm should be used when deploying a non-local
charm. Use requires a channel to be specified, indicating  which channel should be used
when refreshing the charm.

.. collapse:: Example

    .. code-block:: yaml

        revision: 8


``applications.<application>.scale``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Missing content?


``applications.<application>.series``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Missing content?


``applications.<application>.storage``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets storage constraints for the application. There are three such constraints:
``pool``, ``size`` and ``count``. The key (label) is application-specific and is
found within the corresponding charm's :ref:`metadata-yaml-file` file. A value string
is one that would be used in the argument to the ``--storage`` option for the
``deploy`` command.

.. collapse:: Example

    .. code-block:: yaml

        storage:
          database: ebs,10G,1


``applications.<application>.to``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dictates the placement (destination) of the deployed units in terms of machines,
applications, units, and containers that are defined elsewhere in the bundle. The
number of destinations cannot be greater than the number of requested units
(see `applications.<application>.num_units`_ above). Zones are not supported;
see `applications.<application>.constraints`_ instead. The value types are given
below.

**Values:**

``new``: Unit is placed on a new machine. This is the default value type. This type
also gets used if the number of destinations is less than than ``num_units``.

``<machine>``: Unit is placed on an existing machine denoted by its (unquoted) ID.

.. collapse:: Example:

    .. code-block:: yaml

        to: 3, new

``<unit>``: Unit is placed on the same machine as the specified unit. Doing so must
not create a loop in the placement logic. The specified unit must be for an
application that is different from the one being placed.

.. collapse:: Example

    .. code-block:: yaml

        to: ["django/0", "django/1", "django/2"]

``<application>``: The application's existing units are iterated over in ascending
order, with each one being assigned as the destination for a unit to be placed. New
machines are used when ``num_units`` is greater than the number of available units.
The same results can be obtained by stating the units explicitly with the ``unit``
type above.

.. collapse:: Example

    .. code-block:: yaml

        to: ["django"]

``<container-type>:new``: Unit is placed inside a container on a new machine. The
value for ``<container-type>`` can be either ``lxd`` or ``kvm``. A new machine is the
default and does not require stating, so ``["lxd:new"]`` is equivalent to just
``["lxd"]``.

.. collapse:: Example

    .. code-block:: yaml

        to: ["lxd"]

``<container-type>:<machine>``: Unit is placed inside a new container on an existing
machine.

.. collapse:: Example

    .. code-block:: yaml

        to: ["lxd:2", "lxd:3"]

``<container-type>:<unit>``: Unit is placed inside a container on the machine that
hosts the specified unit. If the specified unit itself resides within a container,
then the resulting container becomes a peer (sibling) of the other (i.e. containers
are not nested).

.. collapse:: Example

    .. code-block:: yaml

        to: ["lxd:nova-compute/2", "lxd:glance/3"]


``applications.<application>.trust``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Missing content?


``bundle``
----------

If set to ``kubernetes``, indicates a Kubernetes bundle.


``default-base``
----------------

The default base for deploying charms that can be deployed on multiple bases.


``description``
---------------

**Status:** Optional, but recommended.

**Purpose:** Sets the bundle description visible on Charmhub.

**Type:** String

.. collapse:: Examples

    .. code-block:: yaml

        description: This is a test bundle.

    .. code-block:: yaml

        description: |
          This description is long and has multiple lines. Use the vertical bar as
          shown in this example.


``docs``
--------

**Status:** Optional, but recommended.

**Purpose:** A link to a documentation cover page.

    See more: :external+juju:ref:`Juju | Documentation conventions
    <charm-best-practices-documentation>`


``issues``
----------

**Status:** Optional

**Purpose:** A string (or a list of strings) containing a link (or links) to the
bundle's bug tracker.

.. collapse:: Examples

    .. code-block:: yaml

        issues: https://bugs.launchpad.net/my-bundle

    .. code-block:: yaml

        issues:
          - https://bugs.launchpad.net/my-bundle
          - https://github.com/octocat/my-bundle/issues


``machines``
------------

Provides machines that have been targeted by `applications.<application>.to`_. A
machine is denoted by that same machine ID, and must be quoted. Keys for
``constraints``, ``annotations`` and ``series`` can optionally be added to each
machine. Containers are not valid machines in this context.

.. collapse:: Example

    .. code-block:: yaml

        machines:
          "1":
          "2":
            series: bionic
            constraints: cores=2 mem=2G
          "3":
            constraints: cores=3 root-disk=1T


``name``
--------

**Status:** Optional. Only used by Charmhub.

**Type:** String with the same limitations as a
:ref:`charm name <charmcraft-yaml-key-name>`.


``relations``
-------------

States the relations to add between applications. Each relation consists of a pair
of lines, where one line begins with two dashes and the other begins with a single
dash. Each side of a relation (each line) has the format ``<application>:<endpoint>``,
where ``application`` must also be represented under `applications`_. Including the
endpoint is not strictly necessary as it might be determined automatically. However,
it is best practice to do so.

.. collapse:: Example

    .. code-block:: yaml

        relations:
        - - kubernetes-master:kube-api-endpoint
          - kubeapi-load-balancer:apiserver
        - - kubernetes-master:loadbalancer
          - kubeapi-load-balancer:loadbalancer


``saas``
--------

Specifies a set of offers (from the local or a remote controller) to consume when the
bundle is deployed. Each entry in the list is identified via a unique name and a URL
to the offered service. Offer URLs have the following format:

.. code-block::

    [<controller name>:][<model owner>/]<model name>.<application name>

If the controller name is omitted, Juju will use the currently active controller.
Similarly, if the model owner is omitted, Juju will use the user that is currently
logged in to the controller providing the offer.

.. collapse:: Example

    .. code-block:: yaml

        saas:
          svc1:
            url: localoffer.svc1
          svc2:
            url: admin/localoffer.svc2
          svc3:
            url: othercontroller:admin/offer.svc3


``series``
----------

Sets the default series for all applications in the bundle. This also affects machines
devoid of applications. See 'Charm series' above for how a final series is determined.

What series a charm will use can be influenced in several ways. Some of these are set
within the bundle file while some are not. When using bundles, the series is determined
using rules of precedence (most preferred to least):

- the series stated for a machine that an application unit has been assigned to (see
  `machines`_)
- the series stated for an application (see ``series`` under the `<application name>`_
  element)
- the series given by the top level ``series`` element
- the top-most series specified in a charm's ``metadata.yaml`` file
- the most recent LTS release

.. collapse:: Example

    .. code-block:: yaml

        series: noble


``source``
----------

**Status:** Optional

**Purpose:** A string or list of strings containing a link (or links) to the
bundle source code.


``tags``
--------

Sets descriptive tags. A tag is used for organisational purposes in the Charm Store.

.. collapse:: Examples

    .. code-block:: yaml

        tags: [monitoring]

    .. code-block:: yaml

        tags: [database, utility]


``type``
--------

.. Missing content?


``variables``
-------------

Includes the optional definition of variables using anchors. Corresponding values are
later manifested with the use of aliases. An anchor is a string prefixed with an
ampersand (&) whereas an alias is the same string prefixed by an asterisk (*).
The alias will typically be used to specify a value for an application option
(see element ``options``).

.. collapse:: Example

    .. code-block:: yaml

        variables:
          data-port:           &data-port            br-ex:eno2
          worker-multiplier:   &worker-multiplier    0.25


``website``
-----------

**Status:** Optional

**Structure:** A string (or a list of strings) containing a link (or links) to
project websites. In general this is likely to be the upstream project website or the
formal website for the charmed bundle.
