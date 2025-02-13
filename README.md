[![charmcraft](https://snapcraft.io/charmcraft/badge.svg)](https://snapcraft.io/charmcraft)
[![Tests](https://github.com/canonical/charmcraft/actions/workflows/tests.yaml/badge.svg?event=push)](https://github.com/canonical/charmcraft/actions/workflows/tests.yaml)
[![Spread](https://github.com/canonical/charmcraft/actions/workflows/spread.yaml/badge.svg?event=push)](https://github.com/canonical/charmcraft/actions/workflows/spread.yaml)
[![Weekly Spread](https://github.com/canonical/charmcraft/actions/workflows/spread-large.yaml/badge.svg)](https://github.com/canonical/charmcraft/actions/workflows/spread-large.yaml)

# Charmcraft -- easily initialise, pack, and publish your charms

Charmcraft is a CLI tool that makes it easy and quick to initialise, package, and publish Kubernetes and machine charms.

## Give it a try

Let's use Charmcraft to initialise and pack a Kubernetes charm:

### Set up

> See [Juju | Set things up](https://canonical-juju.readthedocs-hosted.com/en/latest/user/howto/manage-your-deployment/manage-your-deployment-environment/#set-things-up). <br> Choose the automatic track and MicroK8s.

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

> See [Juju | Tear things down](https://canonical-juju.readthedocs-hosted.com/en/latest/user/howto/manage-your-deployment/manage-your-deployment-environment/#tear-things-down). <br> Choose the automatic track.

## Next steps

- Read the [docs](https://canonical-charmcraft.readthedocs-hosted.com/en/stable/).
- Read our [Code of conduct](https://ubuntu.com/community/code-of-conduct) and join our [chat](https://matrix.to/#/#charmhub-charmcraft:ubuntu.com) and [forum](https://discourse.charmhub.io/) or [open an issue](https://github.com/canonical/charmcraft/issues).
- Read our [CONTRIBUTING guide](https://github.com/canonical/charmcraft/blob/main/CONTRIBUTING.md) and contribute!