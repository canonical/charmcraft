.. _manage-charmcraft:

Manage Charmcraft
=================


Install Charmcraft
------------------

On Linux
~~~~~~~~

The recommended way to install Charmcraft on Linux is from the ``stable`` channel via
snap:

.. code-block:: bash

    sudo snap install charmcraft --classic

There are multiple channels other than ``stable``. See the full list with ``snap info
charmcraft``.

We recommend either ``latest/stable`` or ``latest/candidate`` for everyday charming.
With the snap you will always be up to date as Charmhub services and APIs evolve.
Charmcraft supports Kubernetes operator development.

In Linux, Charmcraft defaults to LXD to build the charms in a container matching the
target bases (Multipass can also be used). Charmcraft will offer to install LXD if
required, but here are steps to set it up manually:

.. code-block:: bash

    sudo snap install lxd
    sudo adduser $USER lxd
    newgrp lxd
    lxd init --auto

You can also install Charmcraft in an isolated environment.

    See more: :ref:`install-in-an-isolated-environment`


On macOS
~~~~~~~~

An unofficial Charmcraft package is available on `homebrew
<https://formulae.brew.sh/formula/charmcraft>`_.

Installation should be straightforward if using homebrew (if not already set up, refer
to `these instructions <https://brew.sh/>`_).

.. code-block:: bash

    brew install charmcraft

Charmhub commands work natively:

.. terminal::

    charmcraft whoami

    name:      John Doe
    username:  jdoe
    id:        xxxxxxxxxxxxxxxxxxxxxxxxx

On macOS, Charmcraft defaults to Multipass for the build environment. If Multipass isn't
installed on the system, Charmcraft will offer to install it the first time you run the
``charmcraft pack`` command.

You can also install Charmcraft in an isolated environment.

    See more: :ref:`install-in-an-isolated-environment`

.. _install-in-an-isolated-environment:


In an isolated environment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Another way to install Charmcraft is via `Multipass`_. This is a good way to install it
on any platform, as it will give you an isolated development environment.

First, `install Multipass <https://documentation.ubuntu.com/multipass/latest/how-to-guides/install-multipass/>`_.

Then, provision a virtual machine with Multipass. The following command launches
a fresh new VM with 4 cores, 8GB RAM, a 20GB disk, and the name 'charm-dev':

.. code-block:: bash

    multipass launch --cpus 4 --memory 8G --disk 20G --name charm-dev

Open a shell in the resulting Ubuntu virtual machine and install Charmcraft there:

.. code-block:: bash

    multipass shell charm-dev
    sudo snap install charmcraft --classic

That's it. You can now start typing in Charmcraft commands.


Check the installed version of Charmcraft
-----------------------------------------

To check the installed version, run:

.. code-block:: bash

    charmcraft version

..

    See more: :ref:`ref_commands_version`


Upgrade Charmcraft
------------------

If you've installed Charmcraft on Linux as a snap, it will upgrade automatically.

Uninstall Charmcraft
--------------------

For an installation on Linux via snap, run:

.. code-block:: bash

    sudo snap remove charmcraft
