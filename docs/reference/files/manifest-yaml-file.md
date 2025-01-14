(manifest-yaml-file)=

# `manifest.yaml` file

> See also: [How to configure Charmcraft](https://juju.is/docs/sdk/charmcraft-config)

The `manifest.yaml` file in your charm (bundle) is a file that contains information that
Charmhub and `charmcraft` can use to identify the version, build time, OS name, and
version at build time, as well as the architectures that the charm (bundle) can run on.

The file is created automatically by `charmcraft pack` and you can inspect it by
unzipping the `.charm` archive (`unzip <charm name>.charm` ) or by deploying the charm,
SSHing into one its units, and inspecting the charm directory in there (e.g., for unit
`0`: `ls agents/unit-<charm name>-0/charm`).
