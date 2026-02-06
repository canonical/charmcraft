from charmcraft.commands import BaseCommand

import subprocess
import json
import shutil
import pathlib


class PurgeCommand(BaseCommand):
    name = "purge"
    help_msg = "Remove cached data and build containers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-cache",
            action="store_true",
            help="Clear only the pip cache",
        )
        parser.add_argument(
            "--only-builders",
            action="store_true",
            help="Remove only build containers (stopped by default)",
        )
        parser.add_argument(
            "--include-running",
            action="store_true",
            help="Include running build containers",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Remove all caches and all charmcraft containers, including bases",
        )

    def run(self, parsed_args):
        # ---- flag validation ----
        exclusive = [parsed_args.only_cache, parsed_args.only_builders]
        if sum(exclusive) > 1:
            raise RuntimeError(
                "Use only one of --only-cache or --only-builders"
            )

        # ---- cache purge ----
        if parsed_args.all or parsed_args.only_cache or not parsed_args.only_builders:
            self._purge_pip_cache()

        # ---- container purge ----
        if not parsed_args.only_cache:
            self._purge_lxd_containers(
                include_running=parsed_args.include_running or parsed_args.all,
                include_bases=parsed_args.all,
            )

    # -------------------------
    # Implementation helpers
    # -------------------------

    def _purge_pip_cache(self):
        cache_dir = pathlib.Path.home() / ".cache" / "pip"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f"Removed pip cache at {cache_dir}")
        else:
            print("No pip cache found")

    def _purge_lxd_containers(self, *, include_running: bool, include_bases: bool):
        
        containers = self._list_charmcraft_containers()

        for c in containers:
            name = c["name"]
            status = c["status"]

            is_running = status.lower() == "running"
            is_base = "base" in name

            if is_base and not include_bases:
                continue

            if is_running and not include_running:
                continue

            self._delete_container(name)

    def _list_charmcraft_containers(self):
        result = subprocess.run(
            ["lxc", "list", "--project", "charmcraft", "--format=json"],
            capture_output=True,
            text=True,
            check=True,
        )
        containers = json.loads(result.stdout)

        # only containers created by charmcraft
        return [
            c for c in containers
            if c["name"].startswith("charmcraft")
        ]

    def _delete_container(self, name: str):
        print(f"Deleting container {name}")
        subprocess.run(
            ["lxc", "delete", name, "--project", "charmcraft", "--force"],
            check=False,
        )
