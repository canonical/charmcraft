Runtime user and writable directory
-----------------------------------

The ``charm-user`` field controls the user that runs the charm's hook code.
Setting it to ``non-root`` runs the charm without root privileges or access
to ``sudo``.

Running as a non-root user follows the principle of least privilege
and limits the impact of a compromised charm.
The charm can modify only files and directories permitted by
the configured ownership and filesystem permissions.
Configure the workload user and writable directories separately.

Learn more about ``charm-user`` in the
:ref:`Charmcraft configuration reference <charmcraft-yaml-key-charm-user>`.

.. tab-set::

    .. tab-item:: Ubuntu 22.04 and 24.04
        :sync: base-22-24

        The generated ``charmcraft.yaml`` doesn't set ``charm-user``, so Juju
        runs the charm as the root user by default.

    .. tab-item:: Ubuntu 26.04 and higher
        :sync: base-26-plus

        The generated ``charmcraft.yaml`` sets ``charm-user: non-root`` by
        default. The matching rock provides ``/app-data`` outside ``/app`` as
        an application data directory writable by the ``_daemon_`` user.
