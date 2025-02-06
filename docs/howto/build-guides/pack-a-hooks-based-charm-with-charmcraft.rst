.. _pack-a-hooks-based-charm-with-charmcraft:

How to pack a hooks-based charm with Charmcraft
===============================================

    Introduced in Charmcraft 1.4

    See first: :external+ops:ref:`Ops | Turn a hooks-based charm into an ops charm
    <turn-a-hooks-based-charm-into-an-ops-charm>`

Suppose you have a legacy hooks-only charm, for example, `tiny-bash
<https://github.com/erik78se/tiny-bash>`_, which you can clone with:

.. code-block:: bash

    git clone https://github.com/erik78se/tiny-bash

To make it packable by Charmcraft, all you need to do is navigate inside the charm
directory and create a ``charmcraft.yaml`` file with the part definition for a
hooks-based charm, as shown below:

.. code-block:: yaml

    type: charm

    bases:
      - build-on:
        - name: "ubuntu"
          channel: "20.04"
        run-on:
        - name: "ubuntu"
          channel: "20.04"

    parts:
      tiny-bash:
        plugin: dump
        source: .
        prime:
          - LICENSE
          - README.md
          - config.yaml
          - copyright
          - hooks
          - icon.svg
          - metadata.yaml

After this, you can pack your charm with ``charmcraft pack``, as usual:

.. code-block:: bash

   charmcraft pack

If successful, the result should look like the following.

.. terminal::

    Charms packed:
        tiny-bash_ubuntu-20.04-amd64.charm

The charm file should contain all the files listed in the ``prime`` section of the
``tiny-bash`` part and the charm manifest.

.. code-block:: bash

    unzip -l tiny-bash_ubuntu-20.04-amd64.charm

.. terminal::

    Archive:  tiny-bash_ubuntu-20.04-amd64.charm
      Length      Date    Time    Name
    ---------  ---------- -----   ----
          423  2021-11-12 19:37   metadata.yaml
          431  2021-11-12 19:37   README.md
           12  2021-11-12 19:37   config.yaml
         3693  2021-11-12 19:37   icon.svg
           38  2021-11-12 19:37   copyright
          261  2021-11-12 20:08   manifest.yaml
        34523  2021-11-12 19:37   LICENSE
          381  2021-11-12 19:37   hooks/update-status
          346  2021-11-12 19:37   hooks/start
         1294  2021-11-12 19:37   hooks/shared-fs-relation-changed
          563  2021-11-12 19:37   hooks/stop
          497  2021-11-12 19:37   hooks/leader-elected
          447  2021-11-12 19:37   hooks/install
          417  2021-11-12 19:37   hooks/leader-settings-changed
          811  2021-11-12 19:37   hooks/upgrade-charm
          625  2021-11-12 19:37   hooks/config-changed
    ---------                     -------
        44762                     16 files

And you can also deploy your application with ``juju deploy``, as usual:

.. code-block:: bash

   juju deploy ./tiny-bash_ubuntu-20.04-amd64.charm

.. terminal::

    Located local charm "tiny-bash", revision 0
    Deploying "tiny-bash" from local charm "tiny-bash", revision 0

If successful, the result should look as below, i.e., with the application status
active.

.. code-block:: bash

    juju status

.. terminal::

    Model    Controller           Cloud/Region         Version  SLA          Timestamp
    default  localhost-localhost  localhost/localhost  2.9.12   unsupported  17:23:23-03:00

    App        Version  Status  Scale  Charm      Store  Channel  Rev  OS      Message
    tiny-bash           active      1  tiny-bash  local             0  ubuntu  update-status ran: 20:22

    Unit          Workload  Agent  Machine  Public address  Ports  Message
    tiny-bash/0*  active    idle   0        10.2.17.31             update-status ran: 20:22

    Machine  State    DNS         Inst id        Series  AZ  Message
    0        started  10.2.17.31  juju-55481c-0  focal       Running
