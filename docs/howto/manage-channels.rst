.. _manage-channels:

Manage channels
===============

    See first: :external+juju:ref:`Juju | Charm channel <charm-channel>`

Create a channel
----------------

When you register a name on Charmhub, that automatically creates 4 channels, all with
track ``latest`` but with different risk levels, namely, ``edge``, ``beta``,
``candidate``, ``stable``, respectively.

    See more: :ref:`register-a-name`

.. raw:: html

   <!--
   A charm channel consists of three pieces, in this order: <track>/<risk>/<branch>.

   The <risk> refers to one of the following risk levels:

       stable: (default) This is the latest, tested, working stable version of the charm.
       candidate: A release candidate. There is high confidence this will work fine, but there may be minor bugs.
       beta: A beta testing milestone release.
       edge: The very latest version - expect bugs!


   When you register, you get a track called `latest` with all the usual risk levels. So, you get all of:

   latest/stable
   latest/candidate
   latest/beta
   latest/edge

   This counts as 4 separate channels. They're created implicitly. (They're only _opened_ if you release a revision to them.)

   The track is what you request a guardrail and create a new of (not the channel).

   Later on, if you specify a channel, you get:
   - An implicit stable risk, if you don't declare a risk.
   - An implicit empty branch, if you don't declare a branch.
   -->

View the available channels
---------------------------

To view a charm's channels on Charmhub, run ``charmcraft status`` followed by the name
of the charm. E.g.,

.. code-block:: bash

    charmcraft status my-awesome-charm

The following output shows four channels, all of which have the same track, ``latest``,
but different risk levels, namely, ``edge``, ``beta``, ``candidate``, and ``stable``.

.. terminal::

    Track    Channel    Version    Revision
    latest   stable     -          -
             candidate  -          -
             beta       0.1        1
             edge       ↑          ↑


   See more: :ref:`ref_commands_status`


Customise a channel's track
---------------------------

You can request a track guardrail and create a track.

    See more: :ref:`manage-tracks`


Open a channel
--------------

A channel is opened when you release a revision to it. Before that, the
channel is created but not opened.


Close a channel
---------------

Close a channel with:

.. code-block:: bash

  charmcraft close <charm> <track>/<risk>[/<branch>]

When you close a channel, e.g.,
latest/candidate, that means that any deployment requests that go there will be
forwarded to the next most stable risk, e.g., for beta, latest/stable. If you close
stable, you can no longer deploy or update from that, unless you release again to that
channel (because releasing opens the channel).

If you add a branch, closing that branch will forward people to the same track and risk,
without a branch.
