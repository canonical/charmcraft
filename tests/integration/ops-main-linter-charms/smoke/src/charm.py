# Copyright 2024 Canonical Ltd.
import ops  # type: ignore


class SomeCharm(ops.CharmBase): ...


if __name__ == "__main__":
    ops.main(SomeCharm)
