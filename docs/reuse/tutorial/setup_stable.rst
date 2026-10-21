First, :external+multipass:ref:`install multipass <how-to-guides-install-multipass>`.
Then use Multipass to launch an Ubuntu VM with the name ``charm-dev``
from the 24.04 blueprint:

.. code-block:: text

    multipass launch --cpus 4 --disk 50G --memory 8G --name charm-dev 24.04

Once the VM is up, open a shell into it:

.. code-block:: bash

    multipass shell charm-dev

Unless stated otherwise, we will work entirely within the VM from now on.

Install Rockcraft and Charmcraft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to create the rock, you need to install Rockcraft with
classic confinement, which grants it access to the whole file system:

.. code-block:: bash

    sudo snap install rockcraft --classic

In order to create the charm, you'll need to install Charmcraft:

.. code-block:: bash

    sudo snap install charmcraft --channel latest/stable --classic

Install LXD and Canonical Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LXD will be required for building the rock.
Make sure it is installed:

.. code-block:: bash

    lxd --version

If LXD is not installed, install it with ``sudo snap install lxd``.

Initialize LXD:

.. code-block:: bash

    lxd init --auto

Canonical Kubernetes is required to deploy the |12FactorApp| application on
Kubernetes. Let's install Canonical Kubernetes using the
``1.34-classic/stable`` channel and bootstrap the cluster:

.. code-block:: text

    sudo snap install k8s --classic --channel 1.34-classic/stable
    sudo k8s bootstrap


Canonical Kubernetes needs local storage so Juju can provide storage volumes,
and ingress so that we can expose and access the app.

Enable the necessary features:

.. code-block:: bash

    sudo k8s enable local-storage
    sudo k8s enable ingress

Canonical Kubernetes exposes ingress through a load-balancer service. Enable
the built-in load balancer, wait for the MetalLB controller (which hosts the
load balancer's validating webhook) to roll out, then point its address pool
at the VM's own IP so the ingress is assigned a reachable address:

.. code-block:: bash

    sudo k8s enable load-balancer
    sudo k8s kubectl rollout status deployment/metallb-controller \
      -n metallb-system --timeout=5m
    INGRESS_IP=$(ip -4 route get 2.2.2.2 | grep -oP 'src \K[0-9.]+')
    sudo k8s set load-balancer.l2-mode=true load-balancer.cidrs="$INGRESS_IP/32"

Check the status of Canonical Kubernetes:

.. code-block:: bash

   sudo k8s status --wait-ready

If successful, the terminal will output ``status: ready``
along with a list of enabled and disabled features.

Set up a local registry
~~~~~~~~~~~~~~~~~~~~~~~~~

Canonical Kubernetes pulls application images from an OCI registry. Deploy a
small registry inside the cluster, exposed on the node at ``localhost:32000``:

.. code-block:: bash

    sudo k8s kubectl apply -f - <<'EOF'
    apiVersion: v1
    kind: Namespace
    metadata:
      name: container-registry
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: registry
      namespace: container-registry
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: registry
      template:
        metadata:
          labels:
            app: registry
        spec:
          containers:
            - name: registry
              image: registry:2.8.3
              ports:
                - containerPort: 5000
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: registry
      namespace: container-registry
    spec:
      type: NodePort
      selector:
        app: registry
      ports:
        - port: 5000
          targetPort: 5000
          nodePort: 32000
    EOF

Wait for the registry to become available:

.. code-block:: bash

    sudo k8s kubectl rollout status deployment/registry \
      -n container-registry --timeout=5m

Install Juju
~~~~~~~~~~~~

Juju is required to deploy the |12FactorApp| application.
We'll install Juju using the ``3.6/stable`` channel. Since the snap is
sandboxed, we'll also manually create a directory to contain
its files. Canonical Kubernetes isn't automatically registered as a Juju
cloud, so let's add it before bootstrapping a development controller:

.. code-block:: text

    sudo snap install juju --channel 3.6/stable
    mkdir -p ~/.local/share
    sudo k8s config | juju add-k8s k8s-cloud --client
    juju bootstrap k8s-cloud dev-controller

It could take a few minutes to download the images.
