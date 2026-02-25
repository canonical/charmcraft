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
"""Unit tests for FetchLibCommand - specifically testing error message handling."""

import argparse
import pathlib
from unittest import mock

import pytest

from charmcraft import errors
from charmcraft.application.commands.store import FetchLibCommand
from charmcraft.application.main import APP_METADATA
from charmcraft.utils.charmlibs import LibData


def test_fetchlibcommand_library_not_found_error_message_with_no_args(
    service_factory, monkeypatch
):
    """Test that error message shows actual library name when no library argument is provided.
    
    This test reproduces the bug where running `charmcraft fetch-lib` without arguments
    and getting a LibraryError from the store would show "Library None not found in Charmhub."
    instead of the actual library name.
    """
    # Create a mock LibData for a library that exists locally
    lib_data = LibData(
        lib_id="6c3e6b6680d64e9c89e611d1a15f65be",
        api=0,
        patch=40,
        content="# Library content",
        content_hash="abcd1234",
        full_name="charms.opensearch.v0.helper_charm",
        path=pathlib.Path("lib/charms/opensearch/v0/helper_charm.py"),
        lib_name="helper_charm",
        charm_name="opensearch",
    )
    
    # Mock utils.get_libs_from_tree to return our test library
    mock_get_libs = mock.Mock(return_value=[lib_data])
    monkeypatch.setattr(
        "charmcraft.application.commands.store.utils.get_libs_from_tree",
        mock_get_libs,
    )
    
    # Mock the store service to raise LibraryError when getting metadata
    # This simulates the store not finding the library
    mock_store_svc = service_factory.store
    mock_store_svc.get_libraries_metadata.side_effect = errors.LibraryError(
        "One or more declared charm-libs could not be found in the store."
    )
    
    # Create the command
    cmd = FetchLibCommand({"app": APP_METADATA, "services": service_factory})
    
    # Run with no library argument (library=None)
    args = argparse.Namespace(library=None, format=None)
    
    # The command should raise a LibraryError
    with pytest.raises(errors.LibraryError) as exc_info:
        cmd.run(args)
    
    # The error message should NOT contain "Library None not found"
    # It should contain the actual library name or a more helpful message
    error_message = str(exc_info.value.args[0])
    assert "Library None" not in error_message, (
        f"Error message contains 'Library None': {error_message}"
    )
    # We expect the original error message to be preserved or enhanced
    # The bug was that it was replacing the error with "Library None not found in Charmhub."


def test_fetchlibcommand_library_not_found_in_tips(service_factory, monkeypatch):
    """Test error message when a library is not found in the store tips.
    
    This tests the second error location where the library ID/API combination
    is not found in the returned tips from the store.
    """
    # Create a mock LibData for a library that exists locally
    lib_data = LibData(
        lib_id="6c3e6b6680d64e9c89e611d1a15f65be",
        api=0,
        patch=40,
        content="# Library content",
        content_hash="abcd1234",
        full_name="charms.opensearch.v0.helper_charm",
        path=pathlib.Path("lib/charms/opensearch/v0/helper_charm.py"),
        lib_name="helper_charm",
        charm_name="opensearch",
    )
    
    # Mock utils.get_libs_from_tree to return our test library
    mock_get_libs = mock.Mock(return_value=[lib_data])
    monkeypatch.setattr(
        "charmcraft.application.commands.store.utils.get_libs_from_tree",
        mock_get_libs,
    )
    
    # Mock the store service to return an empty list (no matching tips)
    # This simulates the library not being found in Charmhub
    mock_store_svc = service_factory.store
    mock_store_svc.get_libraries_metadata.return_value = []
    
    # Create the command
    cmd = FetchLibCommand({"app": APP_METADATA, "services": service_factory})
    
    # Run with no library argument (library=None)
    args = argparse.Namespace(library=None, format=None)
    
    # The command should raise a LibraryError
    with pytest.raises(errors.LibraryError) as exc_info:
        cmd.run(args)
    
    # The error message should NOT contain "Library None not found"
    error_message = str(exc_info.value.args[0])
    assert "Library None" not in error_message, (
        f"Error message contains 'Library None': {error_message}"
    )
    # We should see the actual library name
    assert "opensearch" in error_message or "helper_charm" in error_message, (
        f"Error message should contain library name: {error_message}"
    )
