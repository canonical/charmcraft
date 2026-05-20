from ops.charm import CharmBase
from ops.main import main


class TestCharm(CharmBase):
    """Minimal charm implementation for Ubuntu 26.04 spread tests."""

    pass


if __name__ == "__main__":
    main(TestCharm)
