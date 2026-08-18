Runtime user and writable directory
-----------------------------------

When Charmcraft generates a version 2 12-factor charm targeting Ubuntu 26.04 LTS
or higher, the generated ``charmcraft.yaml`` sets ``charm-user: non-root`` by
default. The matching version 2 rock provides ``/app-data`` as a writable
directory for application data outside ``/app``.

This behavior doesn't apply to version 1 generated charms or charms targeting
lower Ubuntu bases.
