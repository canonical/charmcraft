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
"""Tests for remote build service."""

from unittest.mock import Mock

import pytest

from charmcraft.services.remotebuild import RemoteBuildService


@pytest.fixture
def mock_build():
    """Create a mock build with URL-encoded artifact name."""
    build = Mock()
    build.arch_tag = "amd64"

    # Mock distribution and distro_series
    build.distribution = Mock()
    build.distribution.name = "ubuntu"
    build.distro_series = Mock()
    build.distro_series.version = "20.04"

    # Simulate a Launchpad URL with URL-encoded @ symbol
    build.get_artifact_urls.return_value = [
        "https://launchpad.net/~user/+archive/charm-builds/+files/test-charm_ubuntu%4020.04-amd64.charm"
    ]

    return build


class TestRemoteBuildServiceFilenames:
    """Tests for remote build service filename handling."""

    def test_fetch_logs_filename_format(self, tmp_path):
        """Test that fetch_logs creates filenames with proper format."""
        # Create service with minimal mocking
        service = RemoteBuildService.__new__(RemoteBuildService)
        service._is_setup = True
        service._name = "charmcraft-test-charm-abcd1234"
        service._builds = []

        # Create a mock build
        mock_build = Mock()
        mock_build.arch_tag = "amd64"
        mock_build.distribution = Mock()
        mock_build.distribution.name = "ubuntu"
        mock_build.distro_series = Mock()
        mock_build.distro_series.version = "20.04"
        mock_build.build_log_url = "https://launchpad.net/~user/log.txt"

        service._builds = [mock_build]
        service.request = Mock()
        service.request.download_files_with_progress = Mock(return_value={})

        # Fetch logs
        logs = service.fetch_logs(tmp_path)

        # Check that the filename uses underscore and dash, not @ symbol
        log_file = logs["amd64"]
        assert log_file is not None
        assert "_ubuntu-20.04-amd64-" in log_file.name
        # Ensure no URL encoding in the filename
        assert "%40" not in log_file.name
        # Ensure @ is not used (it should be dash)
        assert "@" not in log_file.name.split("_ubuntu")[1].split("-amd64")[0]

    def test_artifact_filename_url_decoding(self, tmp_path, mock_build):
        """Test that fetch_artifacts properly decodes URL-encoded filenames.

        This test verifies that when Launchpad returns URLs with URL-encoded
        characters (e.g., %40 for @), the downloaded artifacts have properly
        decoded filenames.
        """
        # Create service with minimal mocking
        service = RemoteBuildService.__new__(RemoteBuildService)
        service._is_setup = True
        service._builds = [mock_build]

        # Mock the download to capture what filenames are used
        downloaded_files = {}
        def mock_download(file_dict):
            downloaded_files.update(file_dict)
            return dict(file_dict.items())

        service.request = Mock()
        service.request.download_files_with_progress = mock_download

        # Fetch artifacts
        artifacts = service.fetch_artifacts(tmp_path)

        # Check that the filename is properly decoded
        # The URL contains %40 (encoded @), but the filename should have @ decoded
        artifact_paths = list(artifacts)
        assert len(artifact_paths) == 1

        filename = artifact_paths[0].name
        # The filename should NOT contain %40
        assert "%40" not in filename, f"Filename should not contain URL encoding: {filename}"
        # The filename should contain @ (decoded from %40)
        assert "@" in filename, f"Filename should contain decoded @ symbol: {filename}"
        assert "ubuntu@20.04" in filename, f"Expected 'ubuntu@20.04' in filename: {filename}"
