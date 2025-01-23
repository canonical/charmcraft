First, `install Multipass <https://multipass.run/docs/install-multipass>`_.

Use Multipass to launch an Ubuntu VM with the name ``charm-dev``
from the 24.04 blueprint:

.. code-block:: bash

    multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 24.04

Once the VM is up, open a shell into it:

.. code-block:: bash

    multipass shell charm-dev

In order to create the rock, you'll need to install Rockcraft with the
``--classic`` confinement to allow access to the whole file system:

.. code-block:: bash

    sudo snap install rockcraft --classic


``LXD`` will be required for building the rock.
Make sure it is installed and initialised:

.. code-block:: bash

    lxd --version
    lxd init --auto


If ``LXD`` is not installed, install it with ``sudo snap install lxd``.

In order to create the charm, you'll need to install Charmcraft:

.. code-block:: bash

    sudo snap install charmcraft --channel latest/edge --classic

.. warning::

    This tutorial requires version ``3.2.0`` or later of Charmcraft.
    Check the version of Charmcraft using ``charmcraft --version``.

MicroK8s is required to deploy the Django application on Kubernetes.
Let's install MicroK8s using the ``1.31-strict/stable`` track:

.. code-block:: bash

    sudo snap install microk8s --channel 1.31-strict/stable
    sudo adduser $USER snap_microk8s
    newgrp snap_microk8s

Wait for MicroK8s to be ready:

.. code-block:: bash

   sudo microk8s status --wait-ready

Several MicroK8s add-ons are required for deployment:

.. code-block:: bash

    # Required for Juju to provide storage volumes
    sudo microk8s enable hostpath-storage
    # Required to host the OCI image of the Django application
    sudo microk8s enable registry
    # Required to expose the Django application
    sudo microk8s enable ingress

Juju is required to deploy the Django application.
Install Juju using the ``3.5/stable`` track, and bootstrap a
development controller:

.. code-block:: bash

    sudo snap install juju --channel 3.5/stable
    mkdir -p ~/.local/share
    juju bootstrap microk8s dev-controller

.. note::

    It could take a few minutes to download the images.

