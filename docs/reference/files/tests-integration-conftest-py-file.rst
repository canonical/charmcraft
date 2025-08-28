.. _tests-integration-conftest-py-file:


``tests/integration/conftest.py`` file
======================================

The ``tests/integration/conftest.py`` file contains reusable test fixtures for
integration testing.

When a charm is initialized with the Kubernetes or machine profile, Charmcraft creates
this file with the following contents:

- A fixture that creates a temporary Juju model
- A fixture that packs your charm

The fixtures use the Jubilant library.

    See more:
    :external+ops:ref:`Ops | How to write integration tests for a charm
    <write-integration-tests-for-a-charm>`,
    `Jubilant documentation <https://documentation.ubuntu.com/jubilant/>`_

The integration tests for your charm are in the
:ref:`tests-integration-test-charm-py-file`.
