.. _manage-charm-revisions:

Manage charm revisions
======================

.. raw:: html

    <!--As opposed to resource revisions.-->


Create a charm revision
-----------------------

A charm revision is created implicitly every time you upload a charm to
Charmhub (unless you're uploading the exact same file again).

    See more: :ref:`publish-a-charm`


View the existing charm revisions
---------------------------------

To inspect the existing charm revisions, run ``charmcraft revisions``
followed by the name of the charm.

    See more: :ref:`ref_commands_revisions`


Promote a charm revision to a better risk level
-----------------------------------------------

To promote a charm revision to a more stable risk level, run
:literalref:`charmcraft promote<ref_commands_promote>` with flags specifying the current
and desired channels. For example, to promote a charm from the ``candidate`` channel to
the ``stable`` channel, you would run:

.. code-block:: bash

    charmcraft promote --from-channel=candidate --to-channel=stable

If you are looking to promote charm revisions in your CI workflow, the same result can
be achieved with the `Charmhub Promotion
<https://github.com/canonical/charming-actions/tree/main/promote-charm>`_ GitHub action.
Note that this GitHub action resides in a separate repository and is therefore
maintained separately from Charmcraft.

.. collapse:: Example outcome

    For example, in the following output of ``juju info mongodb``, revision 100
    has been promoted from ``3.6/edge`` through ``3.6/beta`` and ``3.6/candidate`` all
    the way to ``3.6/stable``. (The up arrow next to ``3.6/beta`` indicates that that
    channel has been closed and, if you try ``juju deploy --channel 3.6/beta``, what
    you'll get is the next higher-ranking risk level of the same track, that is,
    ``3.6/candidate``.)

    .. terminal::

       channels: |
        5/stable:       117  2023-04-20  (117)  12MB  amd64  ubuntu@22.04
        5/candidate:    117  2023-04-20  (117)  12MB  amd64  ubuntu@22.04
        5/beta:         ↑
        5/edge:         118  2023-05-03  (118)  13MB   amd64  ubuntu@22.04
        3.6/stable:     100  2023-04-28  (100)  860kB  amd64  ubuntu@20.04, ubuntu@18.04
        3.6/candidate:  100  2023-04-13  (100)  860kB  amd64  ubuntu@20.04, ubuntu@18.04
        3.6/beta:       ↑
        3.6/edge:       100  2023-02-03  (100)  860kB  amd64  ubuntu@20.04, ubuntu@18.04


.. _release-a-revision-into-a-channel:

Release a charm revision into a channel
---------------------------------------

To release a specific charm revision to a channel, run ``charmcraft release`` followed
by the name of the charm and flags specifying the revision and its target channel. E.g.,

.. code-block:: bash

    charmcraft release my-awesome-charm --revision=1 --channel=beta

.. terminal::

    Revision 1 of charm 'my-awesome-charm' released to beta

..

    See more: :ref:`ref_commands_release`

This opens the channel you're releasing to.

    See more: :ref:`manage-channels`

Following the release, Charmhub will display the charm's information at
``charmhub.io/<charm-name>``. (The default information displayed is obtained from the
most stable channel.) Your charm will also become available for download.

    See more: :external+juju:ref:`Juju | Manage charms <manage-charms>`
