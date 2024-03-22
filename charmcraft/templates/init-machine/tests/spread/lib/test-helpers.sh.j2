
export PATH=/snap/bin:$PROJECT_PATH/tests/spread/lib/tools:$PATH
export CONTROLLER_NAME="craft-test-$PROVIDER"


install_lxd() {
    snap install lxd --channel "$LXD_CHANNEL"
    snap refresh lxd --channel "$LXD_CHANNEL"
    lxd waitready
    lxd init --auto
    chmod a+wr /var/snap/lxd/common/lxd/unix.socket
    lxc network set lxdbr0 ipv6.address none
    usermod -a -G lxd "$USER"

    # Work-around clash between docker and lxd on jammy
    # https://github.com/docker/for-linux/issues/1034
    iptables -F FORWARD
    iptables -P FORWARD ACCEPT
}


install_charmcraft() {
    snap install charmcraft --classic --channel "$CHARMCRAFT_CHANNEL"
    snap refresh charmcraft --classic --channel "$CHARMCRAFT_CHANNEL"
}


install_juju() {
    snap install juju --classic --channel "$JUJU_CHANNEL"
    snap refresh juju --classic --channel "$JUJU_CHANNEL"
    mkdir -p "$HOME"/.local/share/juju
    snap install juju-crashdump --classic
}


bootstrap_juju() {
    juju bootstrap --verbose "$PROVIDER" "$CONTROLLER_NAME" \
      $JUJU_BOOTSTRAP_OPTIONS $JUJU_EXTRA_BOOTSTRAP_OPTIONS \
      --bootstrap-constraints=$JUJU_BOOTSTRAP_CONSTRAINTS
}


restore_charmcraft() {
    snap remove --purge charmcraft
}


restore_lxd() {
    snap stop lxd
    snap remove --purge lxd
}


restore_juju() {
    juju controllers --refresh ||:
    juju destroy-controller -v --no-prompt --show-log \
       --destroy-storage --destroy-all-models "$CONTROLLER_NAME"
    snap stop juju
    snap remove --purge juju
    snap remove --purge juju-crashdump
}
