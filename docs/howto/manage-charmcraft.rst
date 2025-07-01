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

.. terminal::

    ==> Downloading https://ghcr.io/v2/homebrew/core/charmcraft/manifests/1.3.2
    ######################################################################## 100.0%
    ==> Downloading https://ghcr.io/v2/homebrew/core/charmcraft/blobs/sha256:ebe7aac3dcfa401762faaf339a28e64bb5fb277a7d96bbcfb72bdc
    ==> Downloading from https://pkg-containers.githubusercontent.com/ghcr1/blobs/sha256:ebe7aac3dcfa401762faaf339a28e64bb5fb277a7d
    ######################################################################## 100.0%
    ==> Pouring charmcraft--1.3.2.mojave.bottle.tar.gz
    🍺  /usr/local/Cellar/charmcraft/1.3.2: 2,205 files, 17.2MB

Charmhub commands work natively:

.. code-block:: bash

    charmcraft whoami
    name:      John Doe
    username:  jdoe
    id:        xxxxxxxxxxxxxxxxxxxxxxxxx

In macOS, Charmcraft defaults to Multipass to build the charms in a container matching
the target bases. Running pack asks to setup Multipass if not already installed, and
continues with the packing process:

.. code-block:: bash

   $ charmcraft pack

.. terminal::

    Multipass is required, but not installed. Do you wish to install Multipass and configure it with the defaults? [y/N]: y
    ==> Downloading https://github.com/canonical/multipass/releases/download/v1.7.2/multipass-1.7.2+mac-Darwin.pkg
    Already downloaded: /Users/jdoe/Library/Caches/Homebrew/downloads/4237fcef800faa84459a2911c3818dfa76f1532d693b151438f1c8266318715b--multipass-1.7.2+mac-Darwin.pkg
    ==> Installing Cask multipass
    ==> Running installer for multipass; your password may be necessary.
    Package installers may write to any location; options such as `--appdir` are ignored.
    installer: Package name is multipass
    installer: Installing at base path /
    installer: The install was successful.
    🍺  multipass was successfully installed!
    Packing charm 'test-charm_ubuntu-20.04-amd64.charm'...
    Starting charmcraft-test-charm-12886917363-0-0-amd64 ...

You can also install Charmcraft in an isolated environment.

    See more: :ref:`install-in-an-isolated-environment`

.. _install-in-an-isolated-environment:


In an isolated environment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Another way to install Charmcraft is via `Multipass`_. This is a good way to install it
on any platform, as it will give you an isolated development environment.

First, `install Multipass <https://multipass.run/docs/how-to-install-multipass>`_.

Second, use Multipass to provision a virtual machine. The following command will launch
a fresh new VM with 4 cores, 8GB RAM and a 20GB disk and the name ‘charm-dev':

.. code-block:: bash

    multipass launch --cpus 4 --memory 8G --disk 20G --name charm-dev

Last, open a shell in your new Ubuntu virtual machine, and install Charmcraft there:

.. code-block:: bash

    multipass shell charm-dev
    ...
    ubuntu@charm-dev:~$ sudo snap install charmcraft --classic
    charmcraft 2.2.0 from Canonical✓ installed

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
