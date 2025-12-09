#!/bin/bash -e

install_charmcraft()
{
    if stat /charmcraft/charmcraft_*.snap 2>/dev/null; then
        snap install --classic --dangerous /charmcraft/charmcraft_*.snap
    else
        echo "Expected a snap to exist in /charmcraft/"
        exit 1
    fi
}

refresh_or_install_snap()
{
  # Refresh a snap or, if it's not installed, install it.
  # args:
  #  1. snap name
  #  2. Channel
  #  3?. Extra arguments to snap install
  snap refresh "$1" --channel="$2" || snap install "$1" --channel="$2" "${@:3}"
}
