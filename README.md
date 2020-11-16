# Charmcraft is for Kubernetes operator developers

Charmcraft supports Kubernetes operator development.

Charmcraft enables collaboration between operator developers, and
publication on [Charmhub](https://charmhub.io/), home of the Open Operator
Collection.

Use `charmcraft` to:

 * Init a new charm file structure
 * Build your operator into a charm for distribution
 * Register your charm name on Charmhub
 * Upload your charms to Charmhub
 * Release your charms into channels

You can use charmcraft with operators written in any language but we
recommend the [Python Operator Framework on
Github](https://github.com/canonical/operator) which is also [on
PyPI](https://pypi.org/project/ops/) for ease of development and
collaboration.

Charmcraft and the Python Operator Framework extend the operator pattern
beyond Kubernetes with [universal
operators](https://juju.is/universal-operators) that drive Linux and
Windows apps. The universal operator pattern is very exciting for
multi-cloud application management.

## Install

The easiest way to install `charmcraft` is with

    sudo snap install charmcraft --beta

There are multiple channels other than `--beta`. See the full list with
`snap info charmcraft`. We recommend either `latest/stable` or `latest/beta`
for everyday charming. With the snap you will always be up to date as
Charmhub services and APIs evolve.

You can also install from PyPI with `pip3 install --user charmcraft`

## Initialize a charm operator package file structure

Use `charmcraft init` to create a new template charm operator file tree:

```bash
$ mkdir my-new-charm; cd my-new-charm
$ charmcraft init
All done.
There are some notes about things we think you should do.
These are marked with ‘TODO:’, as is customary. Namely:
      README.md: fill out the description
      README.md: explain how to use the charm
  metadata.yaml: fill out the charm's description
  metadata.yaml: fill out the charm's summary
```

You will now have all the essential files for a charmed operator, including
the actual `src/charm.py` skeleton and various items of metadata. Charmcraft
assumes you want to work in Python so it will add `requirements.txt` with
the Python operator framework `ops`, and other conventional development
support files.

## Build your charm

With a correct `metadata.yaml` and with `ops` in `requirements.txt` you can
build a charm with:

```text
$ charmcraft build
Created 'test-charm.charm'.
```

`charmcraft build` will fetch additional files into the tree from PyPI based
on `requirements.txt` and will compile modules using a virtualenv.

The charm is just a zipfile with metadata and the operator code itself:

```text
$ unzip -l test-charm.charm
Archive:  test-charm.charm
  Length      Date    Time    Name
---------  ---------- -----   ----
      221  2020-11-15 08:10   metadata.yaml
[...]
    25304  2020-11-15 08:14   venv/yaml/__pycache__/scanner.cpython-38.pyc
---------                     -------
   812617                     84 files
```

Now, if you have a Kubernetes cluster with the Juju OLM accessible you can
directly `juju deploy <test-charm.charm>` to the cluster. You do not need to
publish your operator on Charmhub, you can pass the charm file around
directly to users, or for CI/CD purposes.

## Charmhub login and charm name reservations

[Charmhub](https://charmhub.io/) is the world's largest repository of
operators.  It makes it easy to share and collaborate on operators. The
community are interested in operators for a very wide range of purposes,
including infrastructure-as-code and legacy application management, and of
course Kubernetes operators.

Use `charmcraft login` and `charmcraft logout` to sign into Charmhub.

## Charmhub name registration

You can register operator names in Charmhub with `charmcraft register
<name>`. Many common names have been reserved, you are encouraged to discuss
your interest in leading or collaborating on a charm in [Charmhub
Discourse](https://discourse.charmhub.io/).

Charmhub naming policy is the principle of least surprise - a well-known
name should map to an operator that most people would expect to get for that
name.

Operators in Charmhub can be renamed as needed, so feel free to register a
temporary name, such as <username>-<charmname> as a placeholder.

## Operator upload and release

Charmhub operators are published in channels, like:

```text
latest/stable
latest/candidate
latest/beta
latest/edge
1.3/beta
1.3/edge
1.2/stable
1.2/candidate
1.0/stable
```

Use `charmcraft upload` to get a new revision number for your freshly built
charm, and `charmcraft release` to release a revision into any particular
channel for your users.

# Charmcraft source

Get the source from github with:

    git clone https://github.com/canonical/charmcraft.git
    cd charmcraft
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    python -m charmcraft

If you would like to run the tests you can do so with

    pip install -r requirements-dev.txt
    ./run_tests

Contributions welcome!
