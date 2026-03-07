from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

from charmcraft.application.commands.base import CharmcraftCommand
from craft_cli import emit


class PurgeCommand(CharmcraftCommand):
    name = "purge"
    help_msg = "Remove cached data and build containers"
    overview = textwrap.dedent(
        """
        Remove cached data and build containers created by Charmcraft.

        By default, this command removes the pip cache and stopped build
        containers. Running containers are preserved unless explicitly
        requested.

        Use this command to recover disk space or clean up broken build
        environments.
        """
    )

    def fill_parser(self, parser) -> None:
        super().fill_parser(parser)

        parser.add_argument(
            "--only-cache",
            action="store_true",
            help="Clear only the pip cache",
        )
        parser.add_argument(
            "--only-builders",
            action="store_true",
            help="Remove only stopped build containers",
        )
        parser.add_argument(
            "--include-running",
            action="store_true",
            help="Include running build containers",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Remove all caches and build containers, including bases",
        )

   
    # Public entry point
    

    def run(self, parsed_args) -> None:
        # Resolve behavior
        purge_cache = True
        purge_builders = True
        include_running = parsed_args.include_running

        if parsed_args.only_cache:
            purge_builders = False

        if parsed_args.only_builders:
            purge_cache = False

        if parsed_args.all:
            purge_cache = True
            purge_builders = True
            include_running = True

        # Execute
        if purge_cache:
            self._purge_cache()

        if purge_builders:
            self._purge_build_containers(include_running)

        emit.message("Purge complete.")

    
    # Cache handling
    

    def _purge_cache(self) -> None:
        cache_dir = Path.home() / ".cache" / "charmcraft"

        if not cache_dir.exists():
            emit.message("No Charmcraft cache found.")
            return

        emit.progress(f"Removing cache directory: {cache_dir}")
        shutil.rmtree(cache_dir)

    
    # LXD handling
    

    def _purge_build_containers(self, include_running: bool) -> None:
        containers = self._list_lxd_containers()
        builders = self._filter_builder_containers(
            containers, include_running=include_running
        )

        if not builders:
            emit.message("No build containers to remove.")
            return

        for name in builders:
            emit.progress(f"Removing build container: {name}")
            subprocess.run(
                ["lxc", "delete", "--force", name],
                check=True,
            )

    def _list_lxd_containers(self) -> list[dict]:
        try:
            result = subprocess.run(
                ["lxc", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            emit.warning("LXD is not installed; skipping container cleanup.")
            return []
        except subprocess.CalledProcessError as exc:
            emit.warning(f"Failed to list LXD containers: {exc}")
            return []

        return json.loads(result.stdout)

    def _filter_builder_containers(
        self, containers: list[dict], *, include_running: bool
    ) -> list[str]:
        builders: list[str] = []

        for container in containers:
            name = container.get("name", "")
            status = container.get("status", "").lower()

            # Charmcraft / craft-application builders use this prefix
            if not name.startswith("craft-"):
                continue

            if status == "running" and not include_running:
                continue

            builders.append(name)

        return builders
