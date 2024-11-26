(file-dispatch)=
# File 'dispatch'

The `dispatch` file in your charm is an executable shell script whose responsibility is to execute the `src/charm.py` file with certain environment variables.

The file is created automatically by `charmcraft pack` and you can inspect it by unzipping the `.charm` archive (`unzip <charm name>.charm` ) or by deploying the charm, SSHing into one its units, and inspecting the charm directory in there (e.g., for unit `0`: `ls agents/unit-<charm name>-0/charm`).

---
```{dropdown} Expand to view contents of a sample dispatch file

```bash
#!/bin/sh

JUJU_DISPATCH_PATH="${JUJU_DISPATCH_PATH:-$0}" PYTHONPATH=lib:venv \
  exec ./src/charm.py
```

```