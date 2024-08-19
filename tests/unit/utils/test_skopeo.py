# Copyright 2024 Canonical Ltd.
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
"""Unit tests for skopeo wrapper."""

import pathlib
import platform
from unittest import mock

import pytest

from charmcraft.utils.skopeo import Skopeo

pytestmark = [
    pytest.mark.xfail(
        platform.system().lower() not in ("linux", "darwin"),
        reason="Don't necessarily have skopeo on non Linux/mac platforms.",
        strict=False,  # Allow them to pass anyway.
    ),
]

IMAGE_PATHS = [  # See: https://github.com/containers/skopeo/blob/main/docs/skopeo.1.md#image-names
    "containers-storage:my/local:image",
    "dir:/tmp/some-dir",
    "docker://my-image:latest",
    "docker-archive:/tmp/some-archive",
    "docker-archive:/tmp/some-archive:latest",
    "docker-daemon:sha256:f515493110d497051b4a5c4d977c2b1e7f38190def919ab22683e6785b9d5067",
    "docker-daemon:ubuntu:24.04",
    "oci:/tmp/some-dir:latest",
    "oci-archive:my-image.tar",
]


@pytest.mark.parametrize("path", ["/skopeo", "/bin/skopeo"])
def test_skopeo_path(fake_process, path):
    fake_process.register([path, "--version"])
    skopeo = Skopeo(skopeo_path=path)

    assert skopeo.get_global_command() == [path]


def test_find_skopeo_success(fake_process):
    path = "/fake/path/to/skopeo"
    fake_process.register([path, "--version"])
    with mock.patch("shutil.which", return_value=path) as mock_which:
        skopeo = Skopeo()

    assert skopeo.get_global_command() == [path]
    mock_which.assert_called_once_with("skopeo")


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param({}, [], id="empty"),
        pytest.param({"insecure_policy": True}, ["--insecure-policy"], id="insecure_policy"),
        pytest.param({"arch": "amd64"}, ["--override-arch", "amd64"], id="amd64"),
        pytest.param({"arch": "arm64"}, ["--override-arch", "arm64"], id="arm64"),
        pytest.param({"arch": "riscv64"}, ["--override-arch", "riscv64"], id="riscv64"),
        pytest.param({"os": "linux"}, ["--override-os", "linux"], id="os-linux"),
        pytest.param({"os": "bsd"}, ["--override-os", "bsd"], id="os-bsd"),
        pytest.param(
            {"tmpdir": pathlib.Path("/tmp/skopeo_tmp")},
            ["--tmpdir", "/tmp/skopeo_tmp"],
            id="tmpdir",
        ),
    ],
)
def test_get_global_command(fake_process, kwargs, expected):
    """Tests for getting the global command and arguments."""
    fake_process.register(["/skopeo", "--version"])
    skopeo = Skopeo(skopeo_path="/skopeo", **kwargs)

    assert skopeo.get_global_command() == ["/skopeo", *expected]


@pytest.fixture
def fake_skopeo(fake_process):
    fake_process.register(["/skopeo", "--version"])
    return Skopeo(skopeo_path="/skopeo")


@pytest.mark.parametrize("source_image", IMAGE_PATHS)
@pytest.mark.parametrize("destination_image", IMAGE_PATHS)
@pytest.mark.parametrize(
    ("kwargs", "expected_args"),
    [
        ({}, []),
        ({"all_images": True}, ["--all"]),
        ({"preserve_digests": True}, ["--preserve-digests"]),
        ({"source_username": "user"}, ["--src-creds", "user"]),
        ({"source_password": "pass"}, ["--src-password", "pass"]),
        ({"source_username": "user", "source_password": "pass"}, ["--src-creds", "user:pass"]),
        ({"dest_username": "user"}, ["--dest-creds", "user"]),
        ({"dest_password": "pass"}, ["--dest-password", "pass"]),
        ({"dest_username": "user", "dest_password": "pass"}, ["--dest-creds", "user:pass"]),
    ],
)
def test_get_copy_command(
    fake_process, fake_skopeo: Skopeo, source_image, destination_image, kwargs, expected_args
):
    fake_process.register(
        [
            *fake_skopeo.get_global_command(),
            "copy",
            *expected_args,
            source_image,
            destination_image,
        ]
    )
    result = fake_skopeo.copy(source_image, destination_image, **kwargs)

    result.check_returncode()
