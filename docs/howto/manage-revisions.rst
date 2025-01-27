.. _manage-charm-revisions:

Manage charm revisions
======================

.. raw:: html

    <!--As opposed to resource revisions. (Or bundle revisions, but that's being phased out.)-->

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

To promote a charm revision to a higher-ranking risk level, use the GitHub
``promote-charm`` action.

    See more: `GitHub | canonical/charming-actions/promote-charm
    <https://github.com/canonical/charming-actions/tree/2.6.0/promote-charm>`_

.. collapse:: Example outcome

    For example, in the (partial) output of juju info mongodb below, revision 100 has
    been promoted from ``3.6/edge`` through ``3.6/beta`` and ``3.6/candidate`` all the
    way to ``3.6/stable``. (The up arrow next to ``3.6/beta`` indicates that that
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
