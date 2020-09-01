# What is charmcraft?

Charmcraft provides a streamlined, powerful, opinionated, and flexible tool to
develop, package, and manage the lifecycle of Juju charm publication, focused
particularly on charms written within the [Operator Framework].

[Operator Framework]: https://pypi.org/project/ops/

It is still in heavy, initial development and so a lot is still To Be
Done. However it is already useful, and already simplifies the life of the
charmer.

## How do I install it?

The easiest way to install `charmcraft` is by doing

    sudo snap install --beta charmcraft

(more options are available as per `snap info charmcraft`) but some
people with more esoteric needs not covered by the snap might need to
instead go via `pip3 install --user charmcraft`.

## What can it do for me today?

It can build your charm! No need for git submodules nor pesky hook symlinks, you
can concentrate on your charm being pure python code (plus the required juju
metadata), and `charmcraft` will fill in the boring bits for you.

For example, given a charm that consists exclusively of

    my-charm
    ├── metadata.yaml
    ├── requirements.txt
    └── src/
        └── charm.py

(and assuming `ops` is in `requirements.txt`), then running `charmcraft build`
will produce a charm that looks like

    my-charm
    ├── dispatch
    ├── hooks
    │   ├── install -> ../dispatch
    │   ├── start -> ../dispatch
    │   └── upgrade-charm -> ../dispatch
    ├── metadata.yaml
    ├── src/
    │   └── charm.py
    └── venv/
        ├── ops/
        │   ├── ...
        └── yaml/
            └── ...

which should be all you need to `juju deploy` the charm!

## How do I run it from source?

    git clone https://github.com/canonical/charmcraft.git
    cd charmcraft
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    python -m charmcraft

If you would like to run the tests you can do so with

    pip install -r requirements-dev.txt
    ./run_tests
