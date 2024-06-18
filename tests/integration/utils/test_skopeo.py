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
"""Integration tests for skopeo wrapper."""

import contextlib
import os
import pathlib
import platform
import shutil

import pytest

from charmcraft import errors
from charmcraft.utils.skopeo import Skopeo

pytestmark = [
    pytest.mark.skipif(
        "CI" not in os.environ and not shutil.which("skopeo"), reason="skopeo not found in PATH"
    ),
    pytest.mark.xfail(
        platform.system().lower() not in ("linux", "darwin"),
        reason="Don't necessarily have skopeo on non Linux/mac platforms.",
        strict=False,  # Allow them to pass anyway.
    ),
]


@pytest.mark.parametrize(
    ("name", "image", "tag"),
    [
        ("alpine", "docker://ghcr.io/containerd/alpine", "3.14.0"),
        ("debian12", "docker://gcr.io/distroless/base-debian12", "nonroot"),
        ("mock-rock", "docker://ghcr.io/canonical/oci-factory/mock-rock", "1.2-22.04_279"),
        ("nanoserver", "docker://ghcr.io/containerd/nanoserver", "1809"),
    ],
)
def test_inspect_and_download(
    monkeypatch, tmp_path: pathlib.Path, name: str, image: str, tag: str
):
    (tmp_path / "tmp").mkdir()
    skopeo = Skopeo(tmpdir=tmp_path / "tmp")

    raw_data = skopeo.inspect(f"{image}:{tag}", raw=True)

    with contextlib.suppress(errors.SubprocessError):
        # These fail if the host platform doesn't match a valid platform for the container.
        meta_data = skopeo.inspect(f"{image}:{tag}")
        meta_data_by_hash = skopeo.inspect(f"{image}@{meta_data['Digest']}")
        assert meta_data == meta_data_by_hash
        raw_data_by_hash = skopeo.inspect(f"{image}@{meta_data['Digest']}", raw=True)
        assert raw_data == raw_data_by_hash

    for manifest in raw_data["manifests"]:
        if "variant" in manifest["platform"]:
            # We don't handle variants currently.
            continue
        os = manifest["platform"]["os"]
        arch = manifest["platform"]["architecture"]
        digest = manifest["digest"]
        by_digest_tar = tmp_path / f"{name}_{os}_{arch}-digest.tar"
        by_os_arch_tar = tmp_path / f"{name}_{os}_{arch}.tar"
        os_arch_skopeo = Skopeo(arch=arch, os=os)

        os_arch_skopeo.copy(f"{image}:{tag}", f"oci-archive:{by_os_arch_tar}")
        skopeo.copy(f"{image}@{digest}", f"oci-archive:{by_digest_tar}")

        assert by_digest_tar.exists()
        assert by_os_arch_tar.exists()

        image_info_by_digest = skopeo.inspect(f"{image}@{digest}")
        image_info_by_os_arch = os_arch_skopeo.inspect(f"{image}:{tag}")

        for key in ["Architecture", "Os", "Layers", "LayersData", "Env"]:
            assert image_info_by_digest[key] == image_info_by_os_arch[key]
