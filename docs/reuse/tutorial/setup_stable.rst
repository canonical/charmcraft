First, install Multipass.

.. seealso::

    See more: `Multipass |
    How to install Multipass <https://canonical.com/multipass/docs/install-multipass>`_

Use Multipass to launch an Ubuntu VM with the name ``charm-dev``
from the 24.04 blueprint:

.. code-block:: text

    multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 24.04

Once the VM is up, open a shell into it:

.. code-block:: bash

    multipass shell charm-dev

In order to create the rock, you need to install Rockcraft with
classic confinement, which grants it access to the whole file system:

.. code-block:: bash

    sudo snap install rockcraft --classic

LXD will be required for building the rock.
Make sure it is installed and initialized:

.. code-block:: bash

    lxd --version
    lxd init --auto

If ``LXD`` is not installed, install it with ``sudo snap install lxd``.

In order to create the charm, you'll need to install Charmcraft:

.. code-block:: bash

    sudo snap install charmcraft --channel latest/stable --classic

MicroK8s is required to deploy the |12FactorApp| application on Kubernetes.
Let's install MicroK8s using the ``1.31-strict/stable`` track, add the current
user to the group, and activate the changes:

.. code-block:: text

    sudo snap install microk8s --channel 1.31-strict/stable
    sudo adduser $USER snap_microk8s
    newgrp snap_microk8s


Several MicroK8s add-ons are required for deployment:

.. code-block:: bash

    # Required for Juju to provide storage volumes
    sudo microk8s enable hostpath-storage
    # Required to host the OCI image of the application
    sudo microk8s enable registry
    # Required to expose the application
    sudo microk8s enable ingress

Check the status of MicroK8s:

.. code-block:: bash

   sudo microk8s status --wait-ready

If successful, the terminal will output ``microk8s is running``
along with a list of enabled and disabled add-ons.

Juju is required to deploy the |12FactorApp| application.
We'll install Juju using the ``3.6/stable`` track. Since the snap is
sandboxed, we'll also manually create a directory to contain
its files. Once Juju is ready, we initialize it by bootstrapping a
development controller:

.. code-block:: text

    sudo snap install juju --channel 3.6/stable
    mkdir -p ~/.local/share
    juju bootstrap microk8s dev-controller

It could take a few minutes to download the images.
