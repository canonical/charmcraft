.. _tests-integration-test-charm-py-file:


``tests/integration/test_charm.py`` file
========================================

The ``tests/integration/test_charm.py`` file is the companion to
``src/charm.py`` for integration testing.

Profiles other than the one for 12-factor apps automatically create
``charmcraft init``. It is pre-populated with standard constructs used by
``pytest-operator``, similar to the below:

.. code-block:: python

    #!/usr/bin/env python3
    # Copyright 2023 Ubuntu
    # See LICENSE file for licensing details.

    import asyncio
    import logging
    from pathlib import Path

    import pytest
    import yaml
    from pytest_operator.plugin import OpsTest

    logger = logging.getLogger(__name__)

    METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
    APP_NAME = METADATA["name"]


    @pytest.mark.abort_on_fail
    async def test_build_and_deploy(ops_test: OpsTest):
        """Build the charm-under-test and deploy it together with related charms.

        Assert on the unit status before any relations/configurations take place.
        """
        # Build and deploy charm from local source folder
        charm = await ops_test.build_charm(".")
        resources = {
            "some-container-image": METADATA["resources"]["some-container-image"]["upstream-source"]
        }

        # Deploy the charm and wait for active/idle status
        await asyncio.gather(
            ops_test.model.deploy(charm, resources=resources, application_name=APP_NAME),
            ops_test.model.wait_for_idle(
                apps=[APP_NAME], status="active", raise_on_blocked=True, timeout=1000
            ),
        )
