.. _howto-shared-cache:

Cache intermediate build artefacts
==================================

Because Charmcraft builds Python packages from source rather than using pre-built
wheels, the initial builds of charms can take a while. However, future builds of
the same charm are sped up significantly by reusing the built wheels. When installed
as a snap, Charmcraft automatically caches these wheels in the
``~/snap/charmcraft/common/cache`` directory. However, in some cases, it may be
beneficial to change this directory. This can be done by setting the
``CRAFT_SHARED_CACHE`` environment variable to the path of an existing directory to
use instead.

This can be especially useful in CI, where you may wish to specify a directory that
gets cached between CI runs. This is done automatically when using the
``charmcraft/pack`` action in Canonical's `craft-actions`_ repository for GitHub,
but it can also be done manually in any CI.

CI examples
-----------

On GitLab
~~~~~~~~~

The following example ``gitlab-ci.yml`` will install and run Charmcraft to pack your
charm, caching the intermediate artefacts:

.. code-block:: yaml

    pack-charm:
      cache:
        - key:
            files:
              - requirements.txt
          paths:
            - .charmcraft_cache/
      variables:
        CRAFT_SHARED_CACHE: .charmcraft_cache/
      script:
        - mkdir -p .charmcraft_cache
        - snap install charmcraft
        - charmcraft pack

On GitHub
~~~~~~~~~

While it's recommended that you use `craft-actions`_ where possible, the following
workflow will manually pack a charm, caching the intermediate files:

.. code-block:: yaml

    name: Pack charm
    on:
      pull_request:
    jobs:
      pack:
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v4
        - uses: canonical/craft-actions/charmcraft/setup
        - uses: actions/cache@v4
            with:
              path: ${{ runner.temp }}
              key: charmcraft-cache-${{ hashfiles('requirements.txt') }}
              restore-keys: |
                charmcraft-cache-
        - env:
            CRAFT_SHARED_CACHE: ${{ runner.temp }
          run: |
            charmcraft pack

.. _craft-actions: https://github.com/canonical/craft-actions
