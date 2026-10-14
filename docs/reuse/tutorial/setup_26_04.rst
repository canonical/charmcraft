First, :external+multipass:ref:`install Multipass <how-to-guides-install-multipass>`.
Launch an Ubuntu 26.04 VM named ``charm-dev``:

.. code-block:: bash

    multipass launch --cpus 4 --disk 50G --memory 8G --name charm-dev 26.04
    multipass shell charm-dev

Unless stated otherwise, work entirely within the VM from now on.

Install Rockcraft and Charmcraft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Ubuntu 26.04 extensions require the edge releases of Rockcraft and Charmcraft.
Install both tools with classic confinement:

.. code-block:: bash

    sudo snap install rockcraft --channel latest/edge --classic
    sudo snap install charmcraft --channel latest/edge --classic

Install LXD, Canonical Kubernetes, and Juju
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LXD provides the build environment for the rock and charm. If it isn't installed,
install it with ``sudo snap install lxd``. Initialize it:

.. code-block:: bash

    lxd init --auto

Canonical Kubernetes will host the |12FactorApp| app and PostgreSQL.
Install the Kubernetes and Juju snaps:

.. code-block:: bash

    sudo snap install k8s --channel 1.34-classic/stable --classic
    sudo snap install juju --channel 3.6/stable

Bootstrap a single-node cluster and enable local storage and Gateway API:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:bootstrap-k8s]
    :end-before: [docs:bootstrap-k8s-end]

The ``--wait-ready`` option waits for the cluster to become ready.
Local storage supplies the volumes needed by Juju, PostgreSQL, and the image registry.
Gateway API supplies the ingress controller used later in the tutorial.

Find the VM's Kubernetes node address and define the local registry endpoint:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:cluster-addresses]
    :end-before: [docs:cluster-addresses-end]

Keep this terminal open. The remaining commands use ``NODE_IP`` and ``REGISTRY``.
If you open a new terminal, run these address commands again.

Configure the load balancer to use the VM's address, so the app will be
accessible from outside the VM:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:enable-load-balancer]
    :end-before: [docs:enable-load-balancer-end]

Create a local image registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Canonical Kubernetes doesn't include a registry addon. We'll deploy an OCI
registry in the cluster to store the rocks built during this tutorial.
Create ``registry.yaml`` with the following contents:

.. literalinclude:: /reuse/tutorial/registry_26_04.yaml
    :language: yaml
    :caption: registry.yaml

Deploy the registry and wait for it to be ready:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:deploy-registry]
    :end-before: [docs:deploy-registry-end]

The registry is exposed on the VM's address at port 32000, rather than on
loopback. It uses a persistent volume so its images survive pod restarts.

This registry uses unauthenticated HTTP for an isolated development VM only.
Don't expose it to an untrusted network or use it in production.
Configure containerd to pull images from this HTTP registry:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:configure-registry]
    :end-before: [docs:configure-registry-end]

Bootstrap Juju
~~~~~~~~~~~~~~~

Register Canonical Kubernetes as a Juju cloud, then bootstrap the development
controller:

.. literalinclude:: /reuse/tutorial/bootstrap_26_04.sh
    :language: bash
    :start-after: [docs:bootstrap-juju]
    :end-before: [docs:bootstrap-juju-end]

It can take a few minutes to download the controller images.
