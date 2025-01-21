.. _lxd-profile-yaml-file:


``lxd-profile.yaml`` file
=========================

This document describes the ``lxd-profile.yaml`` file in the root direct
of your machine charm project.

This file is optional, though it may be useful for charms intended for a
machine cloud of the LXD type.

    See more: `Juju \| The LXD cloud and
    Juju <https://juju.is/docs/juju/lxd>`_

The file allows you to specify a LXD profile to be applied to the LXD
container that your charm is deployed into. The structure of the file
closely mimics that of the upstream LXD profile, except that only the
following devices are supported: ``unix-char``, ``unix-block``, ``gpu``,
``usb``.

    See more: `LXD | How to use
    profiles <https://documentation.ubuntu.com/lxd/en/latest/profiles/>`_

.. Source: https://github.com/juju/charm/blob/master/lxdprofile.go#L58-L75
.. // WhiteList devices: unix-char, unix-block, gpu, usb.
.. // BlackList config: boot*, limits* and migration*.

On the Juju end, profiles are upgraded during ``juju refresh <charm>``;
applied automatically during ``juju deploy <charm>``; and displayed at
the machine level via ``juju show-machine`` or ``juju status --format=yaml``.

- Profiles are upgraded during the upgrade of the charm (``juju refresh <charm>``).
- Profiles are displayed at the machine level by using either the ``show-machine``
  command or the ``status --format=yaml`` command. Below is an example of the kind
  of information that can be obtained from either of these two commands:

.. code-block:: yaml

    lxd-profiles:
      juju-default-lxd-profile-0:
        config:
          linux.kernel_modules: openvswitch,ip_tables,ip6_tables
