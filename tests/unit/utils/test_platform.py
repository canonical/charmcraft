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
from textwrap import dedent
from unittest.mock import patch

import distro
import pytest
from craft_application import errors
from hypothesis import given, strategies

from charmcraft import const
from charmcraft.utils.platform import (
    OSPlatform,
    get_os_platform,
    validate_architectures,
)


@pytest.mark.parametrize(
    ("os_release", "expected_system", "expected_release"),
    [
        pytest.param(
            dedent(
                """
                # the following is an empty line

                NAME="Ubuntu"
                VERSION="20.04.1 LTS (Focal Fossa)"
                ID=ubuntu
                ID_LIKE=debian
                PRETTY_NAME="Ubuntu 20.04.1 LTS"
                VERSION_ID="20.04"
                HOME_URL="https://www.ubuntu.com/"
                SUPPORT_URL="https://help.ubuntu.com/"
                BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"

                # more in the middle; the following even would be "out of standard", but
                # we should not crash, just ignore it
                SOMETHING-WEIRD

                PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
                VERSION_CODENAME=focal
                UBUNTU_CODENAME=focal
                """
            ),
            "ubuntu",
            "20.04",
            id="ubuntu-focal",
        ),
        pytest.param(
            dedent(
                """
            NAME="Ubuntu Core"
            VERSION="20"
            ID=ubuntu-core
            PRETTY_NAME="Ubuntu Core 20"
            VERSION_ID="20"
            HOME_URL="https://snapcraft.io/"
            BUG_REPORT_URL="https://bugs.launchpad.net/snappy/"
            """
            ),
            "ubuntu-core",
            "20",
            id="ubuntu-core-20",
        ),
        pytest.param(
            dedent(
                """
                PRETTY_NAME="KDE neon 5.27"
                NAME="KDE neon"
                VERSION_ID="22.04"
                VERSION="5.27"
                VERSION_CODENAME=jammy
                ID=neon
                ID_LIKE="ubuntu debian"
                HOME_URL="https://neon.kde.org/"
                SUPPORT_URL="https://neon.kde.org/"
                BUG_REPORT_URL="https://bugs.kde.org/"
                PRIVACY_POLICY_URL="https://kde.org/privacypolicy/"
                UBUNTU_CODENAME=jammy
                LOGO=start-here-kde-neon
                """
            ),
            "ubuntu",
            "22.04",
            id="kde-neon-like-ubuntu",
        ),
    ],
)
@pytest.mark.parametrize("machine", ["x86_64", "riscv64", "arm64"])
def test_get_os_platform_linux(tmp_path, os_release, expected_system, expected_release, machine):
    """Utilize an /etc/os-release file to determine platform."""
    filepath = tmp_path / "os-release"
    filepath.write_text(os_release)
    with patch("distro.distro._distro", distro.LinuxDistribution(os_release_file=filepath)):
        with patch("platform.machine", return_value=machine):
            with patch("platform.system", return_value="Linux"):
                os_platform = get_os_platform(filepath)
    assert os_platform.system == expected_system
    assert os_platform.release == expected_release
    assert os_platform.machine == machine


@pytest.mark.parametrize("system", ["Windows", "Darwin", "Java", ""])
@pytest.mark.parametrize("release", ["NT", "Sparkling", "Jaguar", "0.0", ""])
@pytest.mark.parametrize("machine", ["AMD64", "x86_86", "arm64", "riscv64"])
def test_get_os_platform_non_linux(system, release, machine):
    """Get platform from a patched Windows machine."""
    with patch("platform.system", return_value=system):
        with patch("platform.release", return_value=release):
            with patch("platform.machine", return_value=machine):
                os_platform = get_os_platform()
    assert os_platform == OSPlatform(system, release, machine)


@given(strategies.iterables(strategies.sampled_from(sorted(const.SUPPORTED_ARCHITECTURES))))
def test_validate_architectures_valid_values(architectures):
    validate_architectures(architectures)


@given(strategies.iterables(strategies.just("all")))
def test_validate_architectures_all_success(architectures):
    validate_architectures(architectures, allow_all=True)


@pytest.mark.parametrize(
    ("architectures", "message"),
    [
        (["brutalist"], "Invalid architecture(s): brutalist"),
    ],
)
@pytest.mark.parametrize(
    "details",
    [
        "Valid architecture values are: 'amd64', 'arm64', 'armhf', 'ppc64el', 'riscv64', and 's390x'"
    ],
)
def test_validate_architectures_error(architectures, message, details):
    match = r"^Invalid architecture\(s\): "
    with pytest.raises(errors.CraftValidationError, match=match) as exc_info:
        validate_architectures(architectures)

    assert exc_info.value.details == details


def test_validate_architectures_all_error():
    with pytest.raises(
        errors.CraftValidationError,
        match="If 'all' is defined for architectures, it must be the only architecture.",
    ):
        validate_architectures(["all", "amd64"], allow_all=True)
