# Charmcraft

[![Charmcraft][charmcraft-badge]](charmcraft-latest)
[![Documentation Status][rtd-badge]](rtd-latest)
[![Tests][tests-badge]](tests-results)
[![Spread][spread-badge]](spread-results)
[![Weekly Spread][weekly-spread-badge]](weekly-spread-results)

**Charmcraft** is the command-line tool for initializing, packaging, and publishing
charms, the software operators used by Juju. With Charmcraft, you can bypass the
boilerplate steps of crafting a charm and focus on what matters — building scalable,
configurable, and easy-to-deploy applications for Juju.

## Basic usage

Charmcraft provides commands to streamline every step of the charm development process,
from initializing your charm project to releasing it on Charmhub.

In your project's root directory, initialize your charm project with basic template
content by running:

```bash
charmcraft init
```

Once you've configured your project to suit the needs of the application you're
charming, build the charm by running:

```bash
charmcraft pack
```

If you're ready to distribute your charm, you can register its name on Charmhub with:

```bash
charmcraft register
```

Upload your charm and any subsequent revisions to Charmhub with:

```bash
charmcraft upload
```

## Installation

Charmcraft is available on all major Linux distributions and macOS.

The recommended way to install Charmcraft on Linux systems is through its
[snap](https://snapcraft.io/charmcraft).

```bash
sudo snap install charmcraft --classic
```

For information on installing Charmcraft on other platforms, refer to our [installation
guide](https://documentation.ubuntu.com/charmcraft/stable/howto/set-up-charmcraft).

## Documentation

The [Charmcraft
documentation](https://documentation.ubuntu.com/charmcraft/stable/) provides
guidance and learning materials for every step of the charming process. Whether you're
new to charming or a seasoned expert, this is the best place to deepen your knowledge.

## Community and support

To get in touch with developers and other
[charmcraft-badge]: https://snapcraft.io/charmcraft/badge.svg
[charmcraft-site]: https://snapcraft.io/charmcraft members of the charming community, reach
out on the [forum](https://discourse.charmhub.io) or in our [Matrix
channel](https://matrix.to/#/#charmhub-charmcraft:ubuntu.com).

You can report any issues or bugs on the project's [GitHub
repository](https://github.com/canonical/charmcraft/issues).

Charmcraft is covered by the [Ubuntu Code of
Conduct](https://ubuntu.com/community/ethos/code-of-conduct).

## Contribute to Charmcraft

Charmcraft is open source and part of the Canonical family. We would love your help.

If you're interested, start with the [contribution guide](CONTRIBUTING.md).

We welcome any suggestions and help with the docs. The [Canonical Open Documentation
Academy](https://github.com/canonical/open-documentation-academy) is the hub for doc
development, including Charmcraft docs. No prior coding experience is required.

## License and copyright

Charmcraft is released under the [Apache-2.0 license](LICENSE)

© 2023-2025 Canonical Ltd.

[charmcraft-badge]: https://snapcraft.io/charmcraft/badge.svg
[charmcraft-site]: https://snapcraft.io/charmcraft
[rtd-badge]: https://readthedocs.com/projects/canonical-charmcraft/badge/?version=latest
[rtd-latest]: https://documentation.ubuntu.com/charmcraft/latest/?badge=latest
[tests-badge]: https://github.com/canonical/charmcraft/actions/workflows/tests.yaml/badge.svg?event=push
[tests-results]: https://github.com/canonical/charmcraft/actions/workflows/tests.yaml
[spread-badge]: https://github.com/canonical/charmcraft/actions/workflows/spread.yaml/badge.svg?event=push
[spread-results]: https://github.com/canonical/charmcraft/actions/workflows/spread.yaml
[weekly-spread-badge]: https://github.com/canonical/charmcraft/actions/workflows/spread-large.yaml/badge.svg
[weekly-spread-results]: https://github.com/canonical/charmcraft/actions/workflows/spread-large.yaml
