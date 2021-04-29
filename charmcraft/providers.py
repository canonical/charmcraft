# Copyright 2021 Canonical Ltd.
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

"""Build environment provider support for charmcraft."""

import dataclasses
import logging
import os
import pathlib
import platform
import shutil
import shlex
import subprocess
import tempfile
import contextlib

import charmcraft
from craft_providers import bases, lxd, multipass, Executor

from typing import Dict, List, Optional, Iterator

logger = logging.getLogger(__name__)


CHARMCRAFT_PROJECT_PATH = pathlib.Path("/root/project")


def fill_parser(parser):
    """Add provider parameters to the general parser."""
    parser.add_argument(
        "--debug", action="store_true", help="Launch debug shell on error."
    )
    parser.add_argument(
        "--destructive-mode",
        action="store_true",
        help="Build on host rather than instantiating a build environment instance.",
    )
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Launch debug shell instead of running build step.",
    )


def process_args(parsed_args, processed_args):
    """Update & validate processed provider args given the parsed args."""
    logger.warning("%r %r", parsed_args, processed_args)
    if os.getenv("CHARMCRAFT_BUILD_ENVIRONMENT") == "managed-host":
        processed_args["destructive_mode"] = True
    else:
        processed_args["destructive_mode"] = parsed_args.destructive_mode

    processed_args["debug"] = parsed_args.debug
    processed_args["shell"] = parsed_args.shell

    # Ensure there is no developer error.
    assert isinstance(processed_args["debug"], bool)
    assert isinstance(processed_args["destructive_mode"], bool)
    assert isinstance(processed_args["shell"], bool)


@dataclasses.dataclass
class BuildBase:
    name: str
    channel: str
    arch: str


def enumerate_buildable_environments() -> Iterator[BuildBase]:
    """Enumerate all build environments to be executed."""
    # TODO: wire up to `bases`
    arch = charmcraft.utils.ARCH_TRANSLATIONS.get(platform.machine())
    #yield BuildBase(name="ubuntu", channel="18.04", arch=arch)
    yield BuildBase(name="ubuntu", channel="20.04", arch=arch)


@contextlib.contextmanager
def launch_environment(project_name: str, project_path: pathlib.Path, base: BuildBase):
    if base.name != "ubuntu":
        raise RuntimeError(
            f"Invalid base name {base.name!r}: only 'Ubuntu' is currently supported."
        )

    if base.channel == "18.04":
        alias = bases.BuilddBaseAlias.BIONIC
        image_name = "snapcraft:core18"
    elif base.channel == "20.04":
        alias = bases.BuilddBaseAlias.FOCAL
        image_name = "snapcraft:core20"
    else:
        raise RuntimeError(
            f"Invalid base channel {base.channel!r}: only '18.04' and '20.04' are currently supported."
        )

    instance_name = (
        f"charmcraft-{project_name}-{base.name}-{base.channel.replace('.' , '-')}-{base.arch}"
    )
    environment = _get_command_environment()
    base_configuration = CharmcraftBuilddBaseConfiguration(
        alias=alias, environment=environment, hostname=instance_name
    )

    instance = multipass.launch(
        name=instance_name,
        base_configuration=base_configuration,
        image_name=image_name,
        auto_clean=True,
    )

    # Mount project.
    instance.mount(host_source=project_path, target=CHARMCRAFT_PROJECT_PATH)

    # Ensure charmcraft is up to date.
    charmcraft_path = _setup_charmcraft(instance)

    yield (instance, charmcraft_path)

    # Unmount everything.
    instance.unmount_all()

    # Shutdown with a delay in case user wants to re-use soon.
    instance.stop(delay_mins=10)


def execute_for_all_bases(
    *,
    charmcraft_cmd: List[str],
    project_name: str,
    project_path: pathlib.Path,
    debug: bool,
    shell: bool,
) -> None:
    """Run comand in provided environment."""
    for build_base in enumerate_buildable_environments():
        logger.info("Launching build environment...")
        with launch_environment(
            project_name=project_name, project_path=project_path, base=build_base
        ) as (instance, charmcraft_path):
            # NOTE: --chdir is not supported on Xenial, but that's OK because
            # Charmcraft does not support it.
            env_cmd = ["env", f"--chdir={CHARMCRAFT_PROJECT_PATH.as_posix()}"]
            shell_cmd = env_cmd + ["bash", "-i"]
            run_cmd = env_cmd + [charmcraft_path.as_posix()] + charmcraft_cmd

            if shell:
                instance.execute_run(shell_cmd)

            try:
                instance.execute_run(
                    run_cmd,
                    check=True,
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as error:
                logger.warning("Command failed with: %r", error.stdout)
                if debug:
                    instance.execute_run(shell_cmd)
                else:
                    raise error


def _is_charmcraft_running_as_snap() -> bool:
    """Get charmcraft version on host if running as snap."""
    return os.getenv("SNAP") is not None and os.getenv("SNAP_NAME") == "charmcraft"


def _get_host_charmcraft_python_version() -> str:
    """Get charmcraft version from python package."""
    return charmcraft.__version__


def _get_host_charmcraft_snap_path() -> pathlib.Path:
    """Get charmcraft SNAP directory."""
    return pathlib.Path(os.environ["SNAP"])


def _get_host_charmcraft_snap_version() -> Optional[str]:
    """Get charmcraft version on host if running as snap."""
    return os.getenv("SNAP_VERSION", None)


def _get_target_version(executor: Executor, charmcraft_path: pathlib.Path) -> str:
    """Get charmcraft version inside instance."""
    proc = executor.execute_run(
        [charmcraft_path.as_posix(), "version"],
        check=True,
        capture_output=True,
        text=True,
    )

    # Charmcraft outputs version to stderr.
    return proc.stderr.strip()


def _setup_charmcraft_snap_from_host(executor: Executor) -> pathlib.Path:
    """Install charmcraft snap into target, if needed."""
    snap_path = "/tmp/charmcraft.snap"

    # Clean outdated snap.
    executor.execute_run(
        ["rm", "-f", snap_path],
        check=True,
        capture_output=True,
    )

    # Need to create a temp path in home directory so Multipass can access it.
    with tempfile.TemporaryDirectory(
        suffix=".tmp-charmcraft",
        dir=pathlib.Path.home(),
    ) as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        tmp_snap = tmp_path / "charmcraft.snap"

        # TODO: need snapd to support grabbing existing snap, or add snapd API.
        # For now, we rebuild with snap pack on the current snap.
        cmd = [
            "snap",
            "pack",
            "/snap/charmcraft/current/",
            f"--filename={tmp_snap.as_posix()}",
        ]

        logger.debug("Executing command on host: %s", shlex.join(cmd))
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )

        executor.push_file(
            source=tmp_snap,
            destination=pathlib.Path(snap_path),
        )

    executor.execute_run(
        ["snap", "install", "--dangerous", "--classic", snap_path],
        check=True,
        capture_output=True,
    )

    return pathlib.Path("/snap/bin/charmcraft")


def _setup_charmcraft_snap_from_store(executor: Executor) -> pathlib.Path:
    """Install charmcraft snap from store into target, if needed."""
    proc = executor.execute_run(
        ["test", "-f", "/snap/bin/charmcraft"], capture_output=True
    )

    if proc.returncode == "0":
        return

    executor.execute_run(
        [
            "snap",
            "download",
            "charmcraft",
            "--basename=charmcraft",
            "--target-directory=/tmp",
        ],
        check=True,
        capture_output=True,
    )
    executor.execute_run(
        ["snap", "install", "/tmp/charmcraft.snap", "--classic", "--dangerous"],
        check=True,
        capture_output=True,
    )

    return pathlib.Path("/snap/bin/charmcraft")


def _setup_charmcraft_python_local(
    executor: Executor, host_source: pathlib.Path
) -> pathlib.Path:
    """Install developer-mode charmcraft into target."""
    assert isinstance(executor, lxd.LXDInstance) or isinstance(
        executor, multipass.MultipassInstance
    )

    target_git_path = "/root/charmcraft-git"
    executor.mount(host_source=host_source, target=pathlib.Path(target_git_path))

    # Verify the mount worked and points a python project.
    executor.execute_run(
        ["test", "-f", target_git_path + "/setup.py"],
        check=True,
        capture_output=True,
    )
    executor.execute_run(
        ["apt-get", "install", "-y", "git", "python3", "python3-pip"],
        check=True,
        capture_output=True,
    )
    executor.execute_run(
        [
            "pip3",
            "install",
            "-U",
            "-r",
            target_git_path + "/requirements.txt",
        ],
        check=True,
        capture_output=True,
    )
    executor.execute_run(
        [
            "pip3",
            "install",
            "-e",
            target_git_path,
        ],
        check=True,
        capture_output=True,
    )

    return pathlib.Path("/usr/local/bin/charmcraft")


def _setup_charmcraft_python_vcs_url(executor: Executor, vcs_url: str) -> pathlib.Path:
    """Install developer-mode charmcraft from git URL into target."""
    executor.execute_run(["pip3", "install", vcs_url], check=True, capture_output=True)

    return pathlib.Path("/usr/local/bin/charmcraft")


def _setup_charmcraft(executor: Executor) -> pathlib.Path:
    host_version = _get_host_charmcraft_python_version()
    try:
        charmcraft_path = pathlib.Path(
            executor.execute_run(
                ["which", "charmcraft"], check=True, capture_output=True, text=True
            ).stdout
        )
        target_version = _get_target_version(executor, charmcraft_path)
    except subprocess.CalledProcessError:
        # Not installed in target.
        charmcraft_path = None
        target_version = None

    if charmcraft_path is not None and target_version == host_version:
        # Default charmcraft on PATH matches, use this.
        logger.debug("Target matches host Charmcraft version, skipping setup.")
        return charmcraft_path

    developer_mode_url = os.environ.get("CHARMCRAFT_DEVELOPER_PROJECT")
    if _is_charmcraft_running_as_snap():
        charmcraft_path = _setup_charmcraft_snap_from_host(executor)
    elif developer_mode_url:
        host_source = pathlib.Path(developer_mode_url)
        if host_source.exists():
            charmcraft_path = _setup_charmcraft_python_local(executor, host_source)
        else:
            charmcraft_path = _setup_charmcraft_python_vcs_url(
                executor, developer_mode_url
            )
    else:
        # Fallback to installing from store and risk version mismatch.
        charmcraft_path = _setup_charmcraft_snap_from_store(executor)

    target_version = _get_target_version(executor, charmcraft_path)
    if host_version != target_version:
        logger.warning(
            "Charmcraft version mismatch detected between host %r and target %r.",
            host_version,
            target_version,
        )

    return charmcraft_path


def _get_command_environment() -> Dict[str, str]:
    env = bases.buildd.default_command_environment()
    env["CHARMCRAFT_BUILD_ENVIRONMENT"] = "managed-host"

    # Pass-through host environment that target may need.
    for env_key in ["http_proxy", "https_proxy"]:
        if env_key in os.environ:
            env[env_key] = os.environ[env_key]

    return env


class CharmcraftBuilddBaseConfiguration(bases.BuilddBase):
    """Base configuration for Charmcraft.

    :cvar compatibility_tag: Tag/Version for variant of build configuration and
        setup.  Any change to this version would indicate that prior [versioned]
        instances are incompatible and must be cleaned.  As such, any new value
        should be unique to old values (e.g. incrementing).
    :cvar instance_config_path: Path to persistent environment configuration
        used for compatibility checks (or other data).  Set to
        /etc/craft-instance.conf, but may be overridden for application-specific
        reasons.
    :cvar instance_config_class: Class defining instance configuration.  May be
        overridden with an application-specific subclass of InstanceConfiguration
        to enable application-specific extensions.

    :param alias: Base alias / version.
    :param environment: Environment to set in /etc/environment.
    :param hostname: Hostname to configure.
    """

    compatibility_tag: str = f"charmcraft-{bases.BuilddBase.compatibility_tag}.0"

    def setup(
        self,
        *,
        executor: Executor,
        retry_wait: float = 0.25,
        timeout: Optional[float] = None,
    ) -> None:
        super().setup(executor=executor, retry_wait=retry_wait, timeout=timeout)
