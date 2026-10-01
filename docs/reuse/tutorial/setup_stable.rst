First, :external+multipass:ref:`install multipass <how-to-guides-install-multipass>`.
Then use Multipass to launch an Ubuntu VM with the name ``charm-dev``
from the 24.04 blueprint:

.. code-block:: text

    multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 24.04

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

Install LXD, Canonical Kubernetes, and Juju
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Check the status of Canonical Kubernetes:

.. code-block:: bash

   sudo k8s status --wait-ready

If successful, the terminal will output ``status: ready``
along with a list of enabled and disabled features.

Set up a local registry
~~~~~~~~~~~~~~~~~~~~~~~~~

Canonical Kubernetes pulls application images from an OCI registry. Unlike
MicroK8s, it doesn't bundle a registry, so we run a small local one. Download
the registry and start it as a service:

.. code-block:: bash

    ARCH=$(dpkg --print-architecture)
    sudo curl -sSL -o /tmp/registry.tar.gz \
      "https://github.com/distribution/distribution/releases/download/v2.8.3/registry_2.8.3_linux_${ARCH}.tar.gz"
    sudo tar -xzf /tmp/registry.tar.gz -C /usr/local/bin registry
    sudo mkdir -p /etc/distribution
    sudo tee /etc/distribution/config.yml > /dev/null <<'EOF'
    version: 0.1
    storage:
      filesystem:
        rootdirectory: /var/lib/registry
    http:
      addr: :5000
    EOF
    sudo tee /etc/systemd/system/registry.service > /dev/null <<'EOF'
    [Unit]
    Description=OCI registry
    After=network.target

    [Service]
    ExecStart=/usr/local/bin/registry serve /etc/distribution/config.yml
    Restart=always

    [Install]
    WantedBy=multi-user.target
    EOF
    sudo systemctl enable --now registry

Finally, let Canonical Kubernetes pull from this registry over plain HTTP by
adding a containerd hosts configuration:

.. code-block:: bash

    sudo mkdir -p /etc/containerd/hosts.d/localhost:5000
    sudo tee /etc/containerd/hosts.d/localhost:5000/hosts.toml > /dev/null <<'EOF'
    server = "http://localhost:5000"

    [host."http://localhost:5000"]
      capabilities = ["pull", "resolve"]
    EOF

Juju is required to deploy the |12FactorApp| application.
We'll install Juju using the ``3.6/stable`` channel. Since the snap is
sandboxed, we'll also manually create a directory to contain
its files. Canonical Kubernetes isn't automatically registered as a Juju
cloud, so we add it before bootstrapping a development controller:

.. code-block:: text

    sudo snap install juju --channel 3.6/stable
    mkdir -p ~/.local/share
    sudo k8s config | juju add-k8s k8s-cloud --client
    juju bootstrap k8s-cloud dev-controller

It could take a few minutes to download the images.
