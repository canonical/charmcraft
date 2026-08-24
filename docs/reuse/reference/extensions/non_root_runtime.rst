Runtime user and writable directory
-----------------------------------

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
