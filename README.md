# Charmcraft is for Kubernetes operator developers

Charmcraft supports Kubernetes operator development.

Charmcraft enables collaboration between charmed operator developers, and
publication on [Charmhub](https://charmhub.io/), home of the Charmed Operator
Collection.

Use `charmcraft` to:

- Init a new charmed operator file structure
- Build your operator into a charmed operator for distribution
- Register your charmed operator name on Charmhub
- Upload your charmed operators to Charmhub
- Release your charmed operators into channels

You can use charmcraft with operators written in any language but we
recommend the [Python Operator Framework on
Github](https://github.com/canonical/operator) which is also [on
PyPI](https://pypi.org/project/ops/) for ease of development and
collaboration.

Charmcraft and the Charmed Operator Framework extend the operator pattern
beyond Kubernetes with [universal
operators](https://juju.is/universal-operators) that drive Linux and
Windows apps. The universal operator pattern is very exciting for
multi-cloud application management.


## Install

The recommended way to install `charmcraft` is from the stable channel with

    sudo snap install charmcraft

There are multiple channels other than `stable`. See the full list with
`snap info charmcraft`. We recommend either `latest/stable` or `latest/beta`
for everyday charming. With the snap you will always be up to date as
Charmhub services and APIs evolve.

You can also install `charmcraft` from PyPI, but some system packages 
(`libffi-dev`, `libapt-pkg-dev` and `libssl-dev`) and a Python package 
need to be installed first (`python-apt`). For the later in Ubuntu 
systems you need to check the 
[Python APT library page](https://launchpad.net/ubuntu/+source/python-apt) 
and choose the source file that matches your system (e.g. for Impish 
it's `python-apt_2.2.1.tar.xz`). So the instructions would be:

    $ sudo apt install -y libffi-dev libapt-pkg-dev libssl-dev
    $ python3 -m venv env
    $ source env/bin/activate
    (env)$ pip install https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.2.1/python-apt_2.2.1.tar.xz
    (env)$ pip install charmcraft


## Initialize a charm operator package file structure

Use `charmcraft init` to create a new template charm operator file tree:

```bash
$ mkdir my-new-charm; cd my-new-charm
$ charmcraft init
Charm operator package file and directory tree initialized.
TODO:

      README.md: Describe your charm in a few paragraphs of Markdown
      README.md: Provide high-level usage, such as required config or relations
   actions.yaml: change this example to suit your needs.
    config.yaml: change this example to suit your needs.
  metadata.yaml: fill out the charm's description
  metadata.yaml: fill out the charm's summary
  metadata.yaml: replace with containers for your workload (delete for non-k8s)
  metadata.yaml: each container defined above must specify an oci-image resource
   src/charm.py: change this example to suit your needs.
   src/charm.py: change this example to suit your needs.
   src/charm.py: change this example to suit your needs.
```

You will now have all the essential files for a charmed operator, including
the actual `src/charm.py` skeleton and various items of metadata. Charmcraft
assumes you want to work in Python so it will add `requirements.txt` with
the Python operator framework `ops`, and other conventional development
support files.

## Build your charm

With a correct `metadata.yaml` and with `ops` in `requirements.txt` you can
build a charmed operator with:

```text
$ charmcraft build
Created 'test-charm.charm'.
```

`charmcraft build` will fetch additional files into the tree from PyPI based
on `requirements.txt` and will compile modules using a virtualenv.

The charmed operator is just a zipfile with metadata and the operator code
itself:

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

Now, if you have a Kubernetes cluster with the Juju OLM accessible you can issue
`juju deploy ./my-new-charm.charm --resource httpbin-image=kennethreitz/httpbin`.
You do not need to publish your operator on Charmhub, you can pass the charmed
operator file around directly to users, or for CI/CD purposes.

## Charmhub login and charm name reservations

[Charmhub](https://charmhub.io/) is the world's largest repository of
operators. It makes it easy to share and collaborate on operators. The
community are interested in operators for a very wide range of purposes,
including infrastructure-as-code and legacy application management, and of
course Kubernetes operators.

Use `charmcraft login` and `charmcraft logout` to sign into Charmhub.

## Charmhub name registration

You can register operator names in Charmhub with `charmcraft register <name>`.
Many common names have been reserved, you are encouraged to discuss your
interest in leading or collaborating on a charmed operator in
[Charmhub Discourse](https://discourse.charmhub.io/).

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
charmed operator, and `charmcraft release` to release a revision into any
particular channel for your users.
