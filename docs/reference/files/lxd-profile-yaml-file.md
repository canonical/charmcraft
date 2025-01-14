(lxd-profile-yaml-file)=

# `lxd-profile.yaml` file

This document describes the `lxd-profile.yaml` file in the root direct of your machine charm project.

This file is optional, though it may be useful for charms intended for a machine cloud of the LXD type.

> See more: [Juju | The LXD cloud and Juju](https://juju.is/docs/juju/lxd)

The file allows you to specify a LXD profile to be applied to the LXD container that your charm is deployed into. The structure of the file closely mimics that of the upstream LXD profile, except that only the following devices are supported: `unix-char`, `unix-block`, `gpu`, `usb`. 

> See more: [LXD | How to use profiles](https://documentation.ubuntu.com/lxd/en/latest/profiles/), [Charmhub | Charmed Neutron Openvswitch](https://charmhub.io/neutron-openvswitch)'s [`lxd-profile.yaml`](https://opendev.org/openstack/charm-neutron-openvswitch/src/branch/master/lxd-profile.yaml)



<!--
Source: https://github.com/juju/charm/blob/master/lxdprofile.go#L58-L75 
// WhiteList devices: unix-char, unix-block, gpu, usb.
// BlackList config: boot*, limits* and migration*.
-->

On the Juju end, profiles are upgraded during `juju refresh <charm>`; applied automatically during `juju deploy <charm>; and displayed at the machine level via `juju show-machine` or `juju status --format=yaml`. 


<!--


- Profiles are upgraded during the upgrade of the charm (`juju refresh <charm>`).
- Profiles are displayed at the machine level by using either the `show-machine` command or the `status --format=yaml` command. Below is an example of the kind of information that can be obtained from either of these two commands:

```yaml
   lxd-profiles:
      juju-default-lxd-profile-0:
        config:
          linux.kernel_modules: openvswitch,ip_tables,ip6_tables
```


Juju (`v.2.5.0`) supports LXD profiles for charms. This is implemented by including file `lxd-profile.yaml` in a  charm's root directory. For example, here is a simple two-line file (this is taken from the [Openvswitch](https://jaas.ai/neutron-openvswitch) charm):

```yaml
config:
  linux.kernel_modules: openvswitch,ip_tables,ip6_tables
```

- A validity check is performed on the profile(s) during the deployment of the charm. This is based on a hardcoded list of allowed items, everything else being denied. The `--force` option can be used to bypass this check but this is not recommended. The list is:

```yaml
config
   -boot
   -limits
   -migration

devices
   unix-char
   unix-block
   gpu
   usb
```
-->
