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
"""A wrapper around Skopeo."""

import io
import json
import pathlib
import shutil
import subprocess
from collections.abc import Sequence
from typing import Any, cast, overload

from charmcraft import errors


class Skopeo:
    """A class for interacting with skopeo."""

    def __init__(
        self,
        *,
        skopeo_path: str = "",
        insecure_policy: bool = False,
        arch: str | None = None,
        os: str | None = None,
        tmpdir: pathlib.Path | None = None,
        debug: bool = False,
    ) -> None:
        if skopeo_path:
            self._skopeo = skopeo_path
        else:
            self._skopeo = cast(str, shutil.which("skopeo"))
            if not self._skopeo:
                raise RuntimeError("Cannot find a skopeo executable.")
        self._insecure_policy = insecure_policy
        self.arch = arch
        self.os = os
        if tmpdir:
            tmpdir.mkdir(parents=True, exist_ok=True)
        self._tmpdir = tmpdir
        self._debug = debug

        self._run_skopeo([self._skopeo, "--version"], capture_output=True, text=True)

    def get_global_command(self) -> list[str]:
        """Prepare the global skopeo options."""
        command = [self._skopeo]
        if self._insecure_policy:
            command.append("--insecure-policy")
        if self.arch:
            command.extend(["--override-arch", self.arch])
        if self.os:
            command.extend(["--override-os", self.os])
        if self._tmpdir:
            command.extend(["--tmpdir", str(self._tmpdir)])
        if self._debug:
            command.append("--debug")
        return command

    def _run_skopeo(self, command: Sequence[str], **kwargs) -> subprocess.CompletedProcess:
        """Run skopeo, converting the error message if necessary."""
        try:
            return subprocess.run(command, check=True, **kwargs)
        except subprocess.CalledProcessError as exc:
            raise errors.SubprocessError.from_subprocess(exc) from exc

    def copy(
        self,
        source_image: str,
        destination_image: str,
        *,
        all_images: bool = False,
        preserve_digests: bool = False,
        source_username: str | None = None,
        source_password: str | None = None,
        dest_username: str | None = None,
        dest_password: str | None = None,
        stdout: io.FileIO | int | None = None,
        stderr: io.FileIO | int | None = None,
    ) -> subprocess.CompletedProcess:
        """Copy an OCI image using Skopeo."""
        command = [
            *self.get_global_command(),
            "copy",
        ]
        if all_images:
            command.append("--all")
        if preserve_digests:
            command.append("--preserve-digests")
        if source_username and source_password:
            command.extend(["--src-creds", f"{source_username}:{source_password}"])
        elif source_username:
            command.extend(["--src-creds", source_username])
        elif source_password:
            command.extend(["--src-password", source_password])
        if dest_username and dest_password:
            command.extend(["--dest-creds", f"{dest_username}:{dest_password}"])
        elif dest_username:
            command.extend(["--dest-creds", dest_username])
        elif dest_password:
            command.extend(["--dest-password", dest_password])

        command.extend([source_image, destination_image])

        if stdout or stderr:
            return self._run_skopeo(command, stdout=stdout, stderr=stderr, text=True)
        return self._run_skopeo(command, capture_output=True, text=True)

    @overload
    def inspect(
        self, image: str, *, format_template: None = None, raw: bool = False, tags: bool = True
    ) -> dict[str, Any]: ...
    @overload
    def inspect(
        self, image: str, *, format_template: str, raw: bool = False, tags: bool = True
    ) -> str: ...
    def inspect(
        self,
        image: str,
        *,
        format_template: str | None = None,
        raw: bool = False,
        tags: bool = True,
    ) -> dict[str, Any] | str:
        """Inspect an image."""
        command = [*self.get_global_command(), "inspect"]
        if format_template is not None:
            command.extend(["--format", format_template])
        if raw:
            command.append("--raw")
        if not tags:
            command.append("--no-tags")

        command.append(image)

        result = self._run_skopeo(command, capture_output=True, text=True)

        if format_template is None:
            return json.loads(result.stdout)
        return result.stdout
