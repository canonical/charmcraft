# Copyright 2024 Canonical Ltd.
import ops  # type: ignore


class SomeCharm(ops.CharmBase): ...


# ruff: noqa: ERA001
# charmcraft analyse should detect that ops.main() call is missing
#
# if __name__ == "__main__":
#     ops.main(SomeCharm)
