# Copyright 2023 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft

"""Constants used in charmcraft."""
import enum
from typing import Literal

from craft_providers.bases import BaseName

# region Environment variables
ALTERNATE_AUTH_ENV_VAR = "CHARMCRAFT_AUTH"
DEVELOPER_MODE_ENV_VAR = "CHARMCRAFT_DEVELOPER"
EXPERIMENTAL_EXTENSIONS_ENV_VAR = "CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS"
IMAGE_INFO_ENV_VAR = "CHARMCRAFT_IMAGE_INFO"
PROVIDER_ENV_VAR = "CHARMCRAFT_PROVIDER"
SHARED_CACHE_ENV_VAR = "CRAFT_SHARED_CACHE"
STORE_API_ENV_VAR = "CHARMCRAFT_STORE_API_URL"
STORE_STORAGE_ENV_VAR = "CHARMCRAFT_UPLOAD_URL"
STORE_REGISTRY_ENV_VAR = "CHARMCRAFT_REGISTRY_URL"
# These are only for use within the managed environment
MANAGED_MODE_ENV_VAR = "CHARMCRAFT_MANAGED_MODE"
# endregion
# region Project files and directories
CHARMCRAFT_FILENAME = "charmcraft.yaml"
BUNDLE_FILENAME = "bundle.yaml"
MANIFEST_FILENAME = "manifest.yaml"
JUJU_CONFIG_FILENAME = "config.yaml"
METADATA_FILENAME = "metadata.yaml"
JUJU_ACTIONS_FILENAME = "actions.yaml"

WORK_DIRNAME = "work_dir"
BUILD_DIRNAME = "build"
VENV_DIRNAME = "venv"
STAGING_VENV_DIRNAME = "staging-venv"
# endregion
# region Output files and directories
# Dispatch script filename
DISPATCH_FILENAME = "dispatch"
# Hooks directory name
HOOKS_DIRNAME = "hooks"
# The minimum set of hooks to be provided for compatibility with old Juju
MANDATORY_HOOK_NAMES = frozenset(("install", "start", "upgrade-charm"))

CommonBaseStr = Literal[  # Bases supported as both build bases and run bases
    "ubuntu@18.04",
    "ubuntu@20.04",
    "ubuntu@22.04",
    "ubuntu@23.10",
    "ubuntu@24.04",
    "centos@7",
    "almalinux@9",
]
BaseStr = CommonBaseStr
BuildBaseStr = CommonBaseStr | Literal["ubuntu@devel"]

DEVEL_BASE_STRINGS = ()  # Bases that require a specified build base.

SUPPORTED_BASES = frozenset(
    (
        BaseName("ubuntu", "18.04"),
        BaseName("ubuntu", "20.04"),
        BaseName("ubuntu", "22.04"),
        BaseName("ubuntu", "23.10"),
        BaseName("ubuntu", "24.04"),
        BaseName("ubuntu", "devel"),
        BaseName("centos", "7"),
        BaseName("almalinux", "9"),
    )
)

SUPPORTED_OSES = frozenset(base.name for base in SUPPORTED_BASES)


class CharmArch(str, enum.Enum):
    """An architecture for a charm."""

    amd64 = "amd64"
    arm64 = "arm64"
    armhf = "armhf"
    ppc64el = "ppc64el"
    riscv64 = "riscv64"
    s390x = "s390x"

    def __str__(self) -> str:
        return str(self.value)


SUPPORTED_ARCHITECTURES = frozenset(arch.value for arch in CharmArch)


# The minimum set of files for a charm to be considered valid
CHARM_MANDATORY_FILES = frozenset(
    (
        DISPATCH_FILENAME,
        HOOKS_DIRNAME,
    )
)
# Optional files that can be present in a charm
CHARM_OPTIONAL_FILES = frozenset(
    (
        METADATA_FILENAME,
        JUJU_ACTIONS_FILENAME,
        JUJU_CONFIG_FILENAME,
        "metrics.yaml",
        "lxd-profile.yaml",
        "templates",
        "version",
        "lib",
        "mod",
        "LICENSE",
        "icon.svg",
        "README.md",
        "actions",
    )
)
# endregion

DEPENDENCIES_HASH_FILENAME = "charmcraft-dependencies-hash.txt"

# If Juju doesn't support the dispatch mechanism, it will execute the
# hook, and we'd need sys.argv[0] to be the name of the hook but it's
# getting lost by calling this dispatch, so we fake JUJU_DISPATCH_PATH
# to be the value it would've otherwise been.
DISPATCH_CONTENT = """#!/bin/sh

JUJU_DISPATCH_PATH="${{JUJU_DISPATCH_PATH:-$0}}" PYTHONPATH=lib:venv \\
  exec ./{entrypoint_relative_path}
"""

UBUNTU_LTS_STABLE = frozenset(
    (
        "18.04",
        "20.04",
        "22.04",
        "24.04",
    )
)

# Metadata keys that are defined in the metadata.yaml file, for backwards compatible
METADATA_YAML_KEYS = frozenset(
    (
        "assumes",
        "containers",
        "description",
        "devices",
        "display-name",
        "docs",
        "extra-bindings",
        "issues",
        "maintainers",
        "name",
        "peers",
        "provides",
        "requires",
        "resources",
        "series",
        "storage",
        "subordinate",
        "summary",
        "terms",
        "website",
    )
)

CHARM_METADATA_LEGARY_KEYS_ALIAS = frozenset(
    (
        "display_name",
        "extra_bindings",
    )
)

# Metadata keys that are allowed in the charmcraft.yaml file
CHARM_METADATA_KEYS = frozenset(
    (
        "assumes",
        "containers",
        "description",
        "devices",
        "title",
        "documentation",
        "extra-bindings",
        "links",
        "name",
        "peers",
        "provides",
        "requires",
        "resources",
        "storage",
        "subordinate",
        "summary",
        "terms",
    )
)

CHARM_METADATA_KEYS_ALIAS = frozenset(("extra_bindings",))

METADATA_YAML_MIGRATE_FIELDS = ("name", "summary", "description")
"""Fields that can exist in metadata.yaml or charmcraft.yaml, but not both."""

FILTERED_STAGE_PACKAGES = {
    BaseName("ubuntu", "20.04"): (
        "adduser",
        "apt",
        "base-files",
        "base-passwd",
        "bash",
        "bsdutils",
        "byobu",
        "bzip2",
        "ca-certificates",
        "coreutils",
        "curl",
        "dash",
        "debconf",
        "debianutils",
        "diffutils",
        "dpkg",
        "e2fsprogs",
        "fdisk",
        "findutils",
        "gawk",
        "gcc-10-base",
        "gettext-base",
        "gpgv",
        "grep",
        "gzip",
        "hostname",
        "init-system-helpers",
        "iproute2",
        "libacl1",
        "libapt-pkg6.0",
        "libasn1-8-heimdal",
        "libattr1",
        "libaudit-common",
        "libaudit1",
        "libblkid1",
        "libbrotli1",
        "libbsd0",
        "libbz2-1.0",
        "libc-bin",
        "libc6",
        "libcap-ng0",
        "libcap2-bin",
        "libcap2",
        "libcom-err2",
        "libcrypt1",
        "libcurl4",
        "libdb5.3",
        "libdebconfclient0",
        "libelf1",
        "libevent-2.1-7",
        "libexpat1",
        "libext2fs2",
        "libfdisk1",
        "libffi7",
        "libgcc-s1",
        "libgcrypt20",
        "libgmp10",
        "libgnutls30",
        "libgpg-error0",
        "libgssapi-krb5-2",
        "libgssapi3-heimdal",
        "libhcrypto4-heimdal",
        "libheimbase1-heimdal",
        "libheimntlm0-heimdal",
        "libhogweed5",
        "libhx509-5-heimdal",
        "libidn2-0",
        "libk5crypto3",
        "libkeyutils1",
        "libkrb5-26-heimdal",
        "libkrb5-3",
        "libkrb5support0",
        "libldap-2.4-2",
        "libldap-common",
        "liblz4-1",
        "liblzma5",
        "libmnl0",
        "libmount1",
        "libmpdec2",
        "libmpfr6",
        "libncurses6",
        "libncursesw6",
        "libnettle7",
        "libnewt0.52",
        "libnghttp2-14",
        "libp11-kit0",
        "libpam-modules-bin",
        "libpam-modules",
        "libpam-runtime",
        "libpam0g",
        "libpcre2-8-0",
        "libpcre3",
        "libprocps8",
        "libpsl5",
        "libpython3-stdlib",
        "libpython3.8-minimal",
        "libpython3.8-stdlib",
        "libreadline8",
        "libroken18-heimdal",
        "librtmp1",
        "libsasl2-2",
        "libsasl2-modules-db",
        "libseccomp2",
        "libselinux1",
        "libsemanage-common",
        "libsemanage1",
        "libsepol1",
        "libsigsegv2",
        "libslang2",
        "libsmartcols1",
        "libsqlite3-0",
        "libss2",
        "libssh-4",
        "libssl1.1",
        "libstdc++6",
        "libsystemd0",
        "libtasn1-6",
        "libtinfo6",
        "libudev1",
        "libunistring2",
        "libutempter0",
        "libuuid1",
        "libwind0-heimdal",
        "libxtables12",
        "libyaml-0-2",
        "libzstd1",
        "login",
        "logsave",
        "lsb-base",
        "mawk",
        "mime-support",
        "mount",
        "ncurses-base",
        "ncurses-bin",
        "openssl",
        "passwd",
        "perl-base",
        "procps",
        "python-pip-whl",
        "python3-distutils",
        "python3-lib2to3",
        "python3-minimal",
        "python3-newt",
        "python3-pip",
        "python3-pkg-resources",
        "python3-setuptools",
        "python3-wheel",
        "python3-yaml",
        "python3.8-minimal",
        "python3.8",
        "python3",
        "readline-common",
        "sed",
        "sensible-utils",
        "sudo",
        "sysvinit-utils",
        "tar",
        "tmux",
        "ubuntu-keyring",
        "util-linux",
        "zlib1g",
    ),
    BaseName("ubuntu", "22.04"): (
        "adduser",
        "apt",
        "base-files",
        "base-passwd",
        "bash",
        "bsdutils",
        "byobu",
        "ca-certificates",
        "coreutils",
        "curl",
        "dash",
        "debconf",
        "debianutils",
        "diffutils",
        "dpkg",
        "e2fsprogs",
        "findutils",
        "gawk",
        "gcc-12-base",
        "gettext-base",
        "gpgv",
        "grep",
        "gzip",
        "hostname",
        "init-system-helpers",
        "iproute2",
        "libacl1",
        "libapt-pkg6.0",
        "libattr1",
        "libaudit-common",
        "libaudit1",
        "libblkid1",
        "libbpf0",
        "libbrotli1",
        "libbsd0",
        "libbz2-1.0",
        "libc-bin",
        "libc6",
        "libcap-ng0",
        "libcap2-bin",
        "libcap2",
        "libcom-err2",
        "libcrypt1",
        "libcurl4",
        "libdb5.3",
        "libdebconfclient0",
        "libelf1",
        "libevent-core-2.1-7",
        "libexpat1",
        "libext2fs2",
        "libffi8",
        "libgcc-s1",
        "libgcrypt20",
        "libgmp10",
        "libgnutls30",
        "libgpg-error0",
        "libgssapi-krb5-2",
        "libhogweed6",
        "libidn2-0",
        "libk5crypto3",
        "libkeyutils1",
        "libkrb5-3",
        "libkrb5support0",
        "libldap-2.5-0",
        "liblz4-1",
        "liblzma5",
        "libmd0",
        "libmnl0",
        "libmount1",
        "libmpdec3",
        "libmpfr6",
        "libncurses6",
        "libncursesw6",
        "libnettle8",
        "libnewt0.52",
        "libnghttp2-14",
        "libnsl2",
        "libp11-kit0",
        "libpam-modules-bin",
        "libpam-modules",
        "libpam-runtime",
        "libpam0g",
        "libpcre2-8-0",
        "libpcre3",
        "libprocps8",
        "libpsl5",
        "libpython3-stdlib",
        "libpython3.10-minimal",
        "libpython3.10-stdlib",
        "libreadline8",
        "librtmp1",
        "libsasl2-2",
        "libsasl2-modules-db",
        "libseccomp2",
        "libselinux1",
        "libsemanage-common",
        "libsemanage2",
        "libsepol2",
        "libsigsegv2",
        "libslang2",
        "libsmartcols1",
        "libsqlite3-0",
        "libss2",
        "libssh-4",
        "libssl3",
        "libstdc++6",
        "libsystemd0",
        "libtasn1-6",
        "libtinfo6",
        "libtirpc-common",
        "libtirpc3",
        "libudev1",
        "libunistring2",
        "libutempter0",
        "libuuid1",
        "libxtables12",
        "libxxhash0",
        "libyaml-0-2",
        "libzstd1",
        "login",
        "logsave",
        "lsb-base",
        "mawk",
        "media-types",
        "mount",
        "ncurses-base",
        "ncurses-bin",
        "openssl",
        "passwd",
        "perl-base",
        "procps",
        "python3-distutils",
        "python3-lib2to3",
        "python3-minimal",
        "python3-newt",
        "python3-pip",
        "python3-pkg-resources",
        "python3-setuptools",
        "python3-wheel",
        "python3-yaml",
        "python3.10-minimal",
        "python3.10",
        "python3",
        "readline-common",
        "sed",
        "sensible-utils",
        "sudo",
        "sysvinit-utils",
        "tar",
        "tmux",
        "ubuntu-keyring",
        "usrmerge",
        "util-linux",
        "zlib1g",
    ),
    BaseName("ubuntu", "24.04"): (
        "apt",
        "base-files",
        "base-passwd",
        "bash",
        "bsdutils",
        "byobu",
        "ca-certificates",
        "coreutils",
        "curl",
        "dash",
        "debconf",
        "debianutils",
        "diffutils",
        "dpkg",
        "e2fsprogs",
        "findutils",
        "gawk",
        "gcc-14-base",
        "gettext-base",
        "gpgv",
        "grep",
        "gzip",
        "hostname",
        "init-system-helpers",
        "iproute2",
        "libacl1",
        "libapparmor1",
        "libapt-pkg6.0t64",
        "libassuan0",
        "libattr1",
        "libaudit-common",
        "libaudit1",
        "libblkid1",
        "libbpf1",
        "libbrotli1",
        "libbz2-1.0",
        "libc-bin",
        "libc6",
        "libcap-ng0",
        "libcap2-bin",
        "libcap2",
        "libcom-err2",
        "libcrypt1",
        "libcurl4t64",
        "libdb5.3t64",
        "libdebconfclient0",
        "libelf1t64",
        "libevent-core-2.1-7t64",
        "libexpat1",
        "libext2fs2t64",
        "libffi8",
        "libgcc-s1",
        "libgcrypt20",
        "libgmp10",
        "libgnutls30t64",
        "libgpg-error0",
        "libgssapi-krb5-2",
        "libhogweed6t64",
        "libidn2-0",
        "libk5crypto3",
        "libkeyutils1",
        "libkrb5-3",
        "libkrb5support0",
        "libldap2",
        "liblz4-1",
        "liblzma5",
        "libmd0",
        "libmnl0",
        "libmount1",
        "libmpfr6",
        "libncursesw6",
        "libnettle8t64",
        "libnewt0.52",
        "libnghttp2-14",
        "libnpth0t64",
        "libp11-kit0",
        "libpam-modules-bin",
        "libpam-modules",
        "libpam-runtime",
        "libpam0g",
        "libpcre2-8-0",
        "libproc2-0",
        "libpsl5t64",
        "libpython3-stdlib",
        "libpython3.12-minimal",
        "libpython3.12-stdlib",
        "libreadline8t64",
        "librtmp1",
        "libsasl2-2",
        "libsasl2-modules-db",
        "libseccomp2",
        "libselinux1",
        "libsemanage-common",
        "libsemanage2",
        "libsepol2",
        "libsigsegv2",
        "libslang2",
        "libsmartcols1",
        "libsqlite3-0",
        "libss2",
        "libssh-4",
        "libssl3t64",
        "libstdc++6",
        "libsystemd0",
        "libtasn1-6",
        "libtinfo6",
        "libtirpc-common",
        "libtirpc3t64",
        "libudev1",
        "libunistring5",
        "libutempter0",
        "libuuid1",
        "libxtables12",
        "libxxhash0",
        "libyaml-0-2",
        "libzstd1",
        "login",
        "logsave",
        "mawk",
        "media-types",
        "mount",
        "ncurses-base",
        "ncurses-bin",
        "netbase",
        "openssl",
        "passwd",
        "perl-base",
        "procps",
        "python3-minimal",
        "python3-newt",
        "python3-pip",
        "python3-pkg-resources",
        "python3-setuptools",
        "python3-wheel",
        "python3-yaml",
        "python3.12-minimal",
        "python3.12",
        "python3",
        "readline-common",
        "sed",
        "sensible-utils",
        "sudo",
        "sysvinit-utils",
        "tar",
        "tmux",
        "tzdata",
        "ubuntu-keyring",
        "util-linux",
        "zlib1g",
    ),
}
"""Basic lists of preinstalled packages on each Juju system.

Each of these were generated with `apt list --installed | cut -d/ -f1` in a
freshly deployed juju machine with this system.
"""
