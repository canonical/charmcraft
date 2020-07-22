#!/usr/bin/env python3
# Copyright (c) {{ year }} {{ author }}
# See LICENSE file for licensing details.

import logging

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState

logger = logging.getLogger(__name__)


class {{ class_name }}(CharmBase):
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self._stored.set_default(things=[])

    def _on_config_changed(self, _):
        current = self.framework.model.config["thing"]
        if current not in self._stored.things:
            logger.debug("found a new thing: %r", current)
            self._stored.things.append(current)


if __name__ == "__main__":
    main({{ class_name }})
