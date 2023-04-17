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
