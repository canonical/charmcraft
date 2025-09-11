.. _tests-integration-test-charm-py-file:


``tests/integration/test_charm.py`` file
========================================

The ``tests/integration/test_charm.py`` file is the companion to
``src/charm.py`` for integration testing.

When a charm is initialized with the Kubernetes or machine profile, Charmcraft creates
this file with the following contents:

- A test that deploys your charm to a temporary Juju model
- A placeholder test that checks the version of your charm's workload

The tests use the Jubilant library.
You should write more tests as you implement your charm.

    See more:
    :external+ops:ref:`Ops | How to write integration tests for a charm
    <write-integration-tests-for-a-charm>`,
    `Jubilant documentation <https://documentation.ubuntu.com/jubilant/>`_

The code for creating the temporary Juju model and packing your charm is in the
:ref:`tests-integration-conftest-py-file`.
