(file-src-charm-py)=
# File 'src/charm.py'

> <small> {ref}`List of files in the charm project <list-of-files-in-a-charm-project>` > `src/charm.py` </small>


The `src/charm.py` is the default entry point for a charm. This file must be executable, and should include a {ref}`shebang <7150md>`>) to indicate the desired interpreter. For many charms, this file will contain the majority of the charm code. It is possible to change the name of this file, but additional changes are then required to enable the charm to be built with {ref}``charmcraft` <charmcraft-charmcraft>`.
