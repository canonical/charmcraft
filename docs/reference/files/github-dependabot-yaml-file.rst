.. _github-dependabot-yaml-file:


``.github/dependabot.yaml`` file
================================

The ``.github/dependabot.yaml`` file configures Dependabot to open pull requests
that update the charm's dependencies. Charmcraft creates this file only when the
profile is ``machine`` or ``kubernetes``.

Dependabot updates are grouped into separate pull requests, so that they're easier to
review. Charmers need to enable Dependabot in their GitHub repo settings to receive
updates.

    See more:

    `GitHub | Enabling Dependabot for your repository
    <https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/dependabot-quickstart#enabling-dependabot-for-your-repository>`__
