[![charmcraft](https://snapcraft.io/charmcraft/badge.svg)](https://snapcraft.io/charmcraft)
[![Tests](https://github.com/canonical/charmcraft/actions/workflows/tests.yaml/badge.svg?event=push)](https://github.com/canonical/charmcraft/actions/workflows/tests.yaml)
[![Spread](https://github.com/canonical/charmcraft/actions/workflows/spread.yaml/badge.svg?event=push)](https://github.com/canonical/charmcraft/actions/workflows/spread.yaml)
[![Weekly Spread](https://github.com/canonical/charmcraft/actions/workflows/spread-large.yaml/badge.svg)](https://github.com/canonical/charmcraft/actions/workflows/spread-large.yaml)

# Charmcraft -- easily initialise, pack, and publish your charms

Charmcraft is a CLI tool that makes it easy and quick to initialise, package, and publish Kubernetes and machine charms. It is an official component of the Charm SDK, itself a part of [the Juju universe](https://juju.is/).

||||
|-|-|- |
|| [Juju](https://juju.is/docs/juju) | Learn how to quickly deploy, integrate, and manage charms on any cloud with Juju. <br>  _It's as simple as `juju deploy foo`, `juju integrate foo bar`, ..., on any cloud._ |
||||
|| [Charmhub](https://charmhub.io/) | Sample our existing charms on Charmhub. <br> _A charm can be a cluster ([OpenStack](https://charmhub.io/openstack-base), [Kubernetes](https://charmhub.io/charmed-kubernetes)), a data platform ([PostgreSQL](https://charmhub.io/postgresql-k8s), [MongoDB](https://charmhub.io/mongodb), etc.), an observability stack ([Canonical Observability Stack](https://charmhub.io/cos-lite)), an MLOps solution ([Kubeflow](https://charmhub.io/kubeflow)), and so much more._ |
||||
|:point_right:| [Charm SDK](https://juju.is/docs/sdk) | Write your own charm! <br> _Juju is written in Go, but our SDK supports easy charm development in Python._  |


## Give it a try

Let's use Charmcraft to initialise and pack a Kubernetes charm:

### Set up

> See [Charm SDK | Set up your development environment automatically > Set up an Ubuntu `charm-dev` VM with Multipass](https://juju.is/docs/sdk/dev-setup#heading--automatic-set-up-an-ubuntu-charm-dev-vm-with-multipass). <br> Choose the MicroK8s track. 

### Initialise and pack your charm

In your Multipass VM shell, create a charm directory and use Charmcraft to initialise your charm file structure:

```
mkdir my-new-charm
cd my-new-charm
charmcraft init
```

This has created a standard charm directory structure:

```
$ ls -R
.:
CONTRIBUTING.md  README.md        pyproject.toml    src    tox.ini
LICENSE          charmcraft.yaml  requirements.txt  tests

./src:
charm.py

./tests:
integration  unit

./tests/integration:
test_charm.py

./tests/unit:
test_charm.py
```

Poke around: 

Note that the `charmcraft.yaml` file shows that what we have is an example charm called `my-new-charm`, which builds on Ubuntu 22.04 and which uses an OCI image resource `httpbin` from `kennethreitz/httpbin`.

Note that the `src/charm.py` file contains code scaffolding featuring the Charm SDK's Ops library for writing charms.

Explore further, start editing the files, or skip ahead and pack the charm: 

```
charmcraft pack
```

If you didn't take any wrong turn or simply left the charm exactly as it was, this should work and yield a file called `my-new-charm_ubuntu-22.04-amd64.charm` (the architecture bit may be different depending on your system's architecture). Use this name and the resource from the `metadata.yaml` to deploy your example charm to your local MicroK8s cloud with Juju:

```
juju deploy ./my-new-charm_ubuntu-22.04-amd64.charm --resource httpbin-image=kennethreitz/httpbin
```

Congratulations, you’ve just initialised and packed your first Kubernetes charm using Charmcraft!

But Charmcraft goes far beyond `init` and `pack`. For example, when you're ready to share your charm with the world, you can use Charmcraft to publish your charm on Charmhub. Run `charmcraft help` to preview more.

### Clean up

> See [Charm SDK | Set up your development environment automatically > Clean up](https://juju.is/docs/sdk/dev-setup#heading--automatic-set-up-an-ubuntu-charm-dev-vm-with-multipass).

## Next steps

### Learn more

Read our [user documentation](https://juju.is/docs/sdk/charmcraft), which also includes other guides showing Charmcraft in action

### Chat with us

Read our [Code of conduct](https://ubuntu.com/community/code-of-conduct) and:
- Join our chat: [Matrix](https://matrix.to/#/#charmhub-charmcraft:ubuntu.com)
- Join our forum: [Discourse](https://discourse.charmhub.io/)

### File an issue

- Report a Charmcraft bug on [GitHub](https://github.com/canonical/charmcraft/issues)
- Raise a general https://juju.is/docs documentation issue on [GitHub | juju/docs](https://github.com/juju/docs)

### Make your mark

- Read our [documentation contributor guidelines](https://discourse.charmhub.io/t/documentation-guidelines-for-contributors/1245) and help improve a doc 
- Read our [codebase contributor guidelines](https://github.com/canonical/charmcraft/blob/main/CONTRIBUTING.md) and help improve the codebase
