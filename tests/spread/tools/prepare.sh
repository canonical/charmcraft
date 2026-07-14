#!/bin/bash -e

install_charmcraft()
{
    if ! stat /charmcraft/charmcraft_*.snap 2>/dev/null; then
        echo "Expected a snap to exist in /charmcraft/"
        exit 1
    fi

    for attempt in 1 2 3; do
        output_file="$(mktemp)"
        if snap install --classic --dangerous /charmcraft/charmcraft_*.snap > >(tee "$output_file") 2> >(tee -a "$output_file" >&2); then
            rm -f "$output_file"
            return
        fi

        if grep -Eq "No root device could be found|daemon is stopping to wait for socket activation" "$output_file" && [[ "$attempt" -lt 3 ]]; then
            snap remove charmcraft --purge || true
            rm -f "$output_file"
            sleep 5
            continue
        fi

        rm -f "$output_file"
        exit 1
    done
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
