First, `install Multipass <https://multipass.run/docs/install-multipass>`_.

Use Multipass to launch an Ubuntu VM with the name ``charm-dev``
from the 24.04 blueprint:

.. code-block:: bash

    multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 24.04

Once the VM is up, open a shell into it:

.. code-block:: bash

    multipass shell charm-dev

In order to create the rock, you'll need to install Rockcraft:

.. code-block:: bash

    sudo snap install rockcraft --classic

``LXD`` will be required for building the rock.
Make sure it is installed and initialised:

.. code-block:: bash

    sudo snap install lxd
    lxd init --auto

In order to create the charm, you'll need to install Charmcraft:

.. code-block:: bash

    sudo snap install charmcraft --channel latest/stable --classic

.. warning::

    This tutorial requires version ``3.0.0`` or later of Charmcraft. Check the
    version of Charmcraft using ``charmcraft --version`` If you have an older
    version of Charmcraft installed, use
    ``sudo snap refresh charmcraft --channel latest/edge`` to get the latest
    edge version of Charmcraft.

MicroK8s is required to deploy the Flask application on Kubernetes. Install MicroK8s:

.. code-block:: bash

    sudo snap install microk8s --channel 1.31-strict/stable
    sudo adduser $USER snap_microk8s
    newgrp snap_microk8s

Wait for MicroK8s to be ready using ``sudo microk8s status --wait-ready``.
Several MicroK8s add-ons are required for deployment:

.. code-block:: bash

    sudo microk8s enable hostpath-storage
    # Required to host the OCI image of the Flask application
    sudo microk8s enable registry
    # Required to expose the Flask application
    sudo microk8s enable ingress

Juju is required to deploy the Flask application.
Install Juju and bootstrap a development controller:

.. code-block:: bash

    sudo snap install juju --channel 3.5/stable
    mkdir -p ~/.local/share
    juju bootstrap microk8s dev-controller
