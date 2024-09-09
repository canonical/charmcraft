# Copyright 2020-2024 Canonical Ltd.
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

"""Commands related to Charmhub."""
import argparse
import collections
import dataclasses
import os
import pathlib
import re
import shutil
import string
import tempfile
import textwrap
import typing
import zipfile
from collections.abc import Collection
from operator import attrgetter
from typing import TYPE_CHECKING, Any

import craft_platforms
import yaml
from craft_application import util
from craft_cli import ArgumentParsingError, emit
from craft_cli.errors import CraftError
from craft_parts import Step
from craft_store import attenuations, models
from craft_store.errors import CredentialsUnavailable
from craft_store.models import ResponseCharmResourceBase
from humanize import naturalsize
from tabulate import tabulate

import charmcraft.store.models
from charmcraft import const, env, errors, parts, utils
from charmcraft.application.commands.base import CharmcraftCommand
from charmcraft.models import project
from charmcraft.store import Store
from charmcraft.store.models import Entity
from charmcraft.utils import cli

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


# some types
class _EntityType(typing.NamedTuple):
    charm: str = "charm"
    bundle: str = "bundle"


class _ResourceType(typing.NamedTuple):
    file: str = "file"
    oci_image: str = "oci-image"


EntityType = _EntityType()
ResourceType = _ResourceType()
# the list of valid attenuations to restrict login credentials
VALID_ATTENUATIONS = {getattr(attenuations, x) for x in dir(attenuations) if x.isupper()}


class LoginCommand(CharmcraftCommand):
    """Login to Charmhub."""

    name = "login"
    help_msg = "Login to Charmhub"
    overview = textwrap.dedent(
        """
        Login to Charmhub.

        Charmcraft will provide a URL for the Charmhub login. When you have
        successfully logged in, Charmcraft will store a token for ongoing
        access to Charmhub at the CLI (if `--export` option was not used
        otherwise it will only save the credentials in the indicated file).

        If `--export <file>` option is used, a secret credentials file will
        be created. And the file can be used to set `CHARMCRAFT_AUTH`
        environment variable.

            export CHARMCRAFT_AUTH=$(cat secret)

        This is suitable for Linux environments without a Vault, such as
        remote servers and CI/CD pipelines.

        Please ensure the secret file and environment variable are secured.

        Remember to `charmcraft logout` if you want to remove that token
        from your local system, especially in a shared environment.

        If the credentials are exported, they can also be attenuated in
        several ways specifying their time-to-live (`--ttl`), on which
        channels would work (`--channel`), what actions will be able to
        do (`--permission`), and on which packages they will work
        (using `--charm` or `--bundle`).

        See also `charmcraft whoami` to verify that you are logged in.
    """
    )

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            "--export",
            type=pathlib.Path,
            help=("Export the Charmhub unencrypted secret credentials to a file"),
        )
        parser.add_argument(
            "--charm",
            action="append",
            help=(
                "The charm(s) on which the required credentials would work "
                "(this option can be indicated multiple times; defaults to all)"
            ),
        )
        parser.add_argument(
            "--bundle",
            action="append",
            help=(
                "The bundle(s) on which the required credentials would work "
                "(this option can be indicated multiple times; defaults to all)"
            ),
        )
        parser.add_argument(
            "--channel",
            action="append",
            help=(
                "The channel(s) on which the required credentials would work "
                "(this option can be indicated multiple times, defaults to any channel)"
            ),
        )
        parser.add_argument(
            "--permission",
            action="append",
            help=(
                "The permission(s) that the required credentials will have "
                "(this option can be indicated multiple times, defaults to all permissions)"
            ),
        )
        parser.add_argument(
            "--ttl",
            type=int,
            help=(
                "The time-to-live (in seconds) of the required credentials (defaults to 30 hours)"
            ),
        )

    def run(self, parsed_args):
        """Run the command."""
        # validate that restrictions are only used if credentials are exported
        restrictive_options = ["charm", "bundle", "channel", "permission", "ttl"]
        if any(getattr(parsed_args, option) is not None for option in restrictive_options):
            if parsed_args.export is None:
                raise ArgumentParsingError(
                    "The restrictive options 'bundle', 'channel', 'charm', 'permission' or 'ttl' "
                    "can only be used when credentials are exported."
                )
        if parsed_args.permission is not None:
            invalid = set(parsed_args.permission) - VALID_ATTENUATIONS
            if invalid:
                invalid_text = ", ".join(map(repr, sorted(invalid)))
                details = (
                    "Explore the documentation to learn about valid permissions: "
                    "https://juju.is/docs/sdk/remote-env-auth"
                )
                raise CraftError(f"Invalid permission: {invalid_text}.", details=details)

        # restrictive options, mapping the names between what is used in Namespace (singular,
        # even if it ends up being a list) and the more natural ones used in the Store layer
        restrictive_options_map = [
            ("ttl", parsed_args.ttl),
            ("channels", parsed_args.channel),
            ("permissions", parsed_args.permission),
        ]
        kwargs = {}
        for arg_name, namespace_value in restrictive_options_map:
            if namespace_value is not None:
                kwargs[arg_name] = namespace_value

        packages = (
            utils.get_packages(charms=parsed_args.charm or [], bundles=parsed_args.bundle or [])
            or None
        )

        if parsed_args.export:
            credentials = self._services.store.get_credentials(packages=packages, **kwargs)
            parsed_args.export.write_text(credentials)
            emit.message(f"Login successful. Credentials exported to {str(parsed_args.export)!r}.")
        else:
            self._services.store.login(packages=packages, **kwargs)
            username = self._services.store.get_account_info()["username"]
            emit.message(f"Logged in as {username!r}.")


class LogoutCommand(CharmcraftCommand):
    """Clear Charmhub token."""

    name = "logout"
    help_msg = "Logout from Charmhub and remove token"
    overview = textwrap.dedent(
        """
        Clear the Charmhub token.

        Charmcraft will remove the local token used for Charmhub access.
        This is important on any shared system because the token allows
        manipulation of your published charms.

        See also `charmcraft whoami` to verify that you are logged in,
        and `charmcraft login`.
    """
    )

    def run(self, parsed_args):
        """Run the command."""
        try:
            self._services.store.logout()
            emit.message("Charmhub token cleared.")
        except CredentialsUnavailable:
            emit.message("You are not logged in to Charmhub.")


class WhoamiCommand(CharmcraftCommand):
    """Show login information."""

    name = "whoami"
    help_msg = "Show your Charmhub login status"
    overview = textwrap.dedent(
        """
        Show your Charmhub login status.

        See also `charmcraft login` and `charmcraft logout`.
    """
    )
    format_option = True

    def run(self, parsed_args):
        """Run the command."""
        try:
            macaroon_info = self._services.store.client.whoami()
        except CredentialsUnavailable:
            if parsed_args.format:
                info = {"logged": False}
                emit.message(cli.format_content(info, parsed_args.format))
            else:
                emit.message("You are not logged in to Charmhub.")
            return

        human_msgs = []
        prog_info = {"logged": True}

        human_msgs.append(f"name: {macaroon_info['account']['display-name']}")
        prog_info["name"] = macaroon_info["account"]["display-name"]
        human_msgs.append(f"username: {macaroon_info['account']['username']}")
        prog_info["username"] = macaroon_info["account"]["username"]
        human_msgs.append(f"id: {macaroon_info['account']['id']}")
        prog_info["id"] = macaroon_info["account"]["id"]

        if permissions := macaroon_info.get("permissions"):
            human_msgs.append("permissions:")
            for item in permissions:
                human_msgs.append(f"- {item}")
            prog_info["permissions"] = permissions

        if packages := macaroon_info.get("packages"):
            grouped = {}
            for package in packages:
                grouped.setdefault(package.type, []).append(package)
            for package_type, title in [("charm", "charms"), ("bundle", "bundles")]:
                if package_type in grouped:
                    human_msgs.append(f"{title}:")
                    pkg_info = []
                    for item in grouped[package_type]:
                        if item.name is not None:
                            human_msgs.append(f"- name: {item.name}")
                            pkg_info.append({"name": item.name})
                        elif item.id is not None:
                            human_msgs.append(f"- id: {item.id}")
                            pkg_info.append({"id": item.id})
                    prog_info[title] = pkg_info

        if channels := macaroon_info.get("channels"):
            human_msgs.append("channels:")
            for item in channels:
                human_msgs.append(f"- {item}")
            prog_info["channels"] = channels

        if parsed_args.format:
            emit.message(cli.format_content(prog_info, parsed_args.format))
        else:
            for msg in human_msgs:
                emit.message(msg)


class RegisterCharmNameCommand(CharmcraftCommand):
    """Register a charm name in Charmhub."""

    name = "register"
    help_msg = "Register a charm name in Charmhub"
    overview = textwrap.dedent(
        """
        Register a charm name in Charmhub.

        Claim a name for your operator in Charmhub. Once you have registered
        a name, you can upload charm operator packages for that name and
        release them for wider consumption.

        Charmhub operates on the 'principle of least surprise' with regard
        to naming. A charm with a well-known name should provide the best
        operator for the microservice most people associate with that name.
        Charms can be renamed in the Charmhub, but we would nonetheless ask
        you to use a qualified name, such as `yourname-charmname` if you are
        in any doubt about your ability to meet that standard.

        We discuss registrations on Charmhub's Discourse:

           https://discourse.charmhub.io/c/charm

        Registration will take you through login if needed.
    """
    )
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name to register in Charmhub")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        store.register_name(parsed_args.name, EntityType.charm)
        emit.message(f"You are now the publisher of charm {parsed_args.name!r} in Charmhub.")


class RegisterBundleNameCommand(CharmcraftCommand):
    """Register a bundle name in the Store."""

    name = "register-bundle"
    help_msg = "Register a bundle name in the Store"
    overview = textwrap.dedent(
        """
        Register a bundle name in the Store.

        Claim a name for your bundle in Charmhub. Once you have registered
        a name, you can upload bundle packages for that name and
        release them for wider consumption.

        Charmhub operates on the 'principle of least surprise' with regard
        to naming. A bundle with a well-known name should provide the best
        system for the service most people associate with that name.  Bundles
        can be renamed in the Charmhub, but we would nonetheless ask
        you to use a qualified name, such as `yourname-bundlename` if you are
        in any doubt about your ability to meet that standard.

        We discuss registrations on Charmhub's Discourse:

           https://discourse.charmhub.io/c/charm

        Registration will take you through login if needed.
    """
    )

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name to register in Charmhub")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        store.register_name(parsed_args.name, EntityType.bundle)
        emit.message(f"You are now the publisher of bundle {parsed_args.name!r} in Charmhub.")


class UnregisterNameCommand(CharmcraftCommand):
    """Unregister a name in the Store."""

    name = "unregister"
    help_msg = "Unregister a name in the Store"
    overview = textwrap.dedent(
        """
        Unregister a name in the Store.

        Unregister a name from Charmhub if no revisions have been uploaded.

        A package cannot be unregistered if something has been uploaded to
        the name. This command is only for unregistering names that have
        never been used. Unregistering must be done by the publisher.
        Attempting to unregister a charm or bundle as a collaborator will
        fail.

        We discuss registrations on Charmhub's Discourse:

           https://discourse.charmhub.io/c/charm
    """
    )

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name to unregister from Charmhub")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config(), needs_auth=True)
        store.unregister_name(parsed_args.name)
        emit.message(f"Name {parsed_args.name!r} has been removed from Charmhub.")


class ListNamesCommand(CharmcraftCommand):
    """List the entities registered in Charmhub."""

    name = "names"
    help_msg = "List your registered charm and bundle names in Charmhub"
    overview = textwrap.dedent(
        """
        An overview of names you have registered to publish in Charmhub.

          $ charmcraft names
          Name                Type    Visibility    Status
          sabdfl-hello-world  charm   public        registered

        Visibility and status are shown for each name. `public` items can be
        seen by any user, while `private` items are only for you and the
        other accounts with permission to collaborate on that specific name.

        The --include-collaborations option can be included to also list those
        names you collaborate with; in that case the publisher will be included
        in the output.

        Listing names will take you through login if needed.
    """
    )
    common = True
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument(
            "--include-collaborations",
            action="store_true",
            help="Include the names you are a collaborator of",
        )

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        with_collab = parsed_args.include_collaborations
        result = store.list_registered_names(include_collaborations=with_collab)

        # build the structure that we need for both human and programmatic output
        headers = ["Name", "Type", "Visibility", "Status"]
        prog_keys = ["name", "type", "visibility", "status"]
        if with_collab:
            headers.append("Publisher")
            prog_keys.append("publisher")
        data = []
        for item in result:
            visibility = "private" if item.private else "public"
            datum = [
                item.name,
                item.entity_type,
                visibility,
                item.status,
            ]
            if with_collab:
                datum.append(item.publisher_display_name)
            data.append(datum)

        if parsed_args.format:
            info = [dict(zip(prog_keys, item)) for item in data]
            emit.message(cli.format_content(info, parsed_args.format))
            return

        if not result:
            emit.message("No charms or bundles registered.")
            return

        table = tabulate(data, headers=headers, tablefmt="plain")
        for line in table.splitlines():
            emit.message(line)


def get_name_from_zip(filepath):
    """Get the charm/bundle name from a zip file."""
    try:
        zf = zipfile.ZipFile(str(filepath))
    except zipfile.BadZipFile as err:
        raise CraftError(f"Cannot open {str(filepath)!r} (bad zip file).") from err

    # get the name from the given file (trying first if it's a charm, then a bundle,
    # otherwise it's an error)
    if "metadata.yaml" in zf.namelist():
        try:
            name = yaml.safe_load(zf.read("metadata.yaml"))["name"]
        except Exception as err:
            raise CraftError(
                f"Bad 'metadata.yaml' file inside charm zip {str(filepath)!r}: must be a valid YAML with "
                "a 'name' key."
            ) from err
    elif "bundle.yaml" in zf.namelist():
        try:
            name = yaml.safe_load(zf.read("bundle.yaml"))["name"]
        except Exception as err:
            raise CraftError(
                f"Bad 'bundle.yaml' file inside bundle zip {str(filepath)!r}: must be a valid YAML with "
                "a 'name' key."
            ) from err
    else:
        raise CraftError(
            f"The indicated zip file {str(filepath)!r} is not a charm ('metadata.yaml' not found) "
            "nor a bundle ('bundle.yaml' not found)."
        )

    return name


class UploadCommand(CharmcraftCommand):
    """Upload a charm or bundle to Charmhub."""

    name = "upload"
    help_msg = "Upload a charm or bundle to Charmhub"
    overview = textwrap.dedent(
        """
        Upload a charm or bundle to Charmhub.

        Push a charm or bundle to Charmhub where it will be verified.
        This command will finish successfully once the package is
        approved by Charmhub.

        In the event of a failure in the verification process, charmcraft
        will report details of the failure, otherwise it will give you the
        new charm or bundle revision.

        Upload will take you through login if needed.
    """
    )
    common = True
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)

        parser.add_argument(
            "filepath", type=utils.useful_filepath, help="The charm or bundle to upload"
        )
        parser.add_argument(
            "--release",
            action="append",
            help="The channel(s) to release to (this option can be indicated multiple times)",
        )
        parser.add_argument(
            "--name",
            type=str,
            help="Name of the charm or bundle on Charmhub to upload to",
        )
        parser.add_argument(
            "--resource",
            action="append",
            type=utils.ResourceOption(),
            default=[],
            help=(
                "The resource(s) to attach to the release, in the <name>:<revision> format "
                "(this option can be indicated multiple times)"
            ),
        )

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            name = parsed_args.name
        else:
            name = get_name_from_zip(parsed_args.filepath)
        store = Store(env.get_store_config())
        result = store.upload(name, parsed_args.filepath)

        if not result.ok:
            if parsed_args.format:
                errors = [{"code": err.code, "message": err.message} for err in result.errors]
                info = {"errors": errors}
                emit.message(cli.format_content(info, parsed_args.format))
            else:
                emit.message(f"Upload failed with status {result.status!r}:")
                for error in result.errors:
                    emit.message(f"- {error.code}: {error.message}")
            return 1

        if parsed_args.release:
            # also release!
            store.release(name, result.revision, parsed_args.release, parsed_args.resource)

        if parsed_args.format:
            info = {"revision": result.revision}
            emit.message(cli.format_content(info, parsed_args.format))
        else:
            emit.message(f"Revision {result.revision} of {str(name)!r} created")
            if parsed_args.release:
                msg = "Revision released to {}"
                args = [", ".join(parsed_args.release)]
                if parsed_args.resource:
                    msg += " (attaching resources: {})"
                    args.append(
                        ", ".join(f"{r.name!r} r{r.revision}" for r in parsed_args.resource)
                    )
                emit.message(msg.format(*args))
        return 0


class ListRevisionsCommand(CharmcraftCommand):
    """List revisions for a charm or a bundle."""

    name = "revisions"
    help_msg = "List revisions for a charm or a bundle in Charmhub"
    overview = textwrap.dedent(
        """
        Show version, date and status for each revision in Charmhub.

        For example:

           $ charmcraft revisions mycharm
           Revision    Version    Created at              Status
           1           1          2020-11-15T11:13:15Z    released

        Listing revisions will take you through login if needed.
    """
    )
    common = True
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument("name", help="The name of the charm or bundle")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        result = store.list_revisions(parsed_args.name)

        # build the structure that we need for both human and programmatic output
        headers = ["Revision", "Version", "Created at", "Status"]
        human_data = []
        prog_data = []
        for item in sorted(result, key=attrgetter("revision"), reverse=True):
            # use just the status or include error message/code in it (if exist)
            if item.errors:
                errors = (f"{e.message} [{e.code}]" for e in item.errors)
                status = "{}: {}".format(item.status, "; ".join(errors))
            else:
                status = item.status

            tstamp = utils.format_timestamp(item.created_at)
            human_data.append(
                [
                    item.revision,
                    item.version,
                    tstamp,
                    status,
                ]
            )

            prog_info = {
                "revision": item.revision,
                "version": item.version,
                "created_at": tstamp,
                "status": item.status,
            }
            if item.errors:
                prog_info["errors"] = [{"message": e.message, "code": e.code} for e in item.errors]
            prog_data.append(prog_info)

        if parsed_args.format:
            emit.message(cli.format_content(prog_data, parsed_args.format))
            return

        if not result:
            emit.message("No revisions found.")
            return

        table = tabulate(human_data, headers=headers, tablefmt="plain", numalign="left")
        for line in table.splitlines():
            emit.message(line)


class ReleaseCommand(CharmcraftCommand):
    """Release a charm or bundle revision to specific channels."""

    name = "release"
    help_msg = "Release a charm or bundle revision in one or more channels"
    overview = textwrap.dedent(
        """
        Release a charm or bundle revision in the channel(s) provided.

        Charm or bundle revisions are not published for anybody else until you
        release them in a channel. When you release a revision into a channel,
        users who deploy the charm or bundle from that channel will get see
        the new revision as a potential update.

        A channel is made up of `track/risk/branch` with both the track and
        the branch as optional items, so formally:

          [track/]risk[/branch]

        Channel risk must be one of stable, candidate, beta or edge. The
        track defaults to `latest` and branch has no default.

        It is enough just to provide a channel risk, like `stable` because
        the track will be assumed to be `latest` and branch is not required.

        Some channel examples:

            stable
            edge
            2.0/candidate
            beta/hotfix-23425
            1.3/beta/feature-foo

        When releasing a charm, one or more resources can be attached to that
        release, using the `--resource` option, indicating in each case the
        resource name and specific revision. For example, to include the
        resource `thedb` revision 4 in the charm release, do:

            charmcraft release mycharm --revision=14 \\
                --channel=beta --resource=thedb:4

        Releasing a revision will take you through login if needed.
    """
    )
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name of charm or bundle")
        parser.add_argument(
            "-r",
            "--revision",
            type=utils.SingleOptionEnsurer(int),
            required=True,
            help="The revision to release",
        )
        parser.add_argument(
            "-c",
            "--channel",
            action="append",
            required=True,
            help="The channel(s) to release to (this option can be indicated multiple times)",
        )
        parser.add_argument(
            "--resource",
            action="append",
            type=utils.ResourceOption(),
            default=[],
            help=(
                "The resource(s) to attach to the release, in the <name>:<revision> format "
                "(this option can be indicated multiple times)"
            ),
        )

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        store.release(
            parsed_args.name,
            parsed_args.revision,
            parsed_args.channel,
            parsed_args.resource,
        )

        msg = "Revision {:d} of {!r} released to {}"
        args = [parsed_args.revision, parsed_args.name, ", ".join(parsed_args.channel)]
        if parsed_args.resource:
            msg += " (attaching resources: {})"
            args.append(", ".join(f"{r.name!r} r{r.revision}" for r in parsed_args.resource))
        emit.message(msg.format(*args))


class PromoteBundleCommand(CharmcraftCommand):
    """Promote a bundle in the Store."""

    name = "promote-bundle"
    help_msg = "Promote a bundle to another channel in the Store"
    overview = textwrap.dedent(
        """
        Promote a bundle to another channel in the Store.

        This command must be run from the bundle project directory to be
        promoted.
        """
    )
    always_load_project = True

    def fill_parser(self, parser: "ArgumentParser") -> None:
        """Add promote-bundle parameters to the general parser."""
        parser.add_argument(
            "--from-channel",
            type=utils.SingleOptionEnsurer(str),
            required=True,
            help="The channel from which to promote the bundle",
        )
        parser.add_argument(
            "--to-channel",
            type=utils.SingleOptionEnsurer(str),
            required=True,
            help="The target channel for the promoted bundle",
        )
        parser.add_argument(
            "--output-bundle",
            type=pathlib.Path,
            help="A path where the created bundle.yaml file can be written",
        )
        parser.add_argument(
            "--exclude",
            action="append",
            default=[],
            help="Any charms to exclude from the promotion process",
        )

    def run(self, parsed_args: "Namespace") -> None:
        """Run the command."""
        if not isinstance(self._services.project, project.Bundle):
            raise CraftError("promote-bundle must be run on a bundle.")

        # Check snapcraft for equiv logic
        from_channel = charmcraft.store.models.ChannelData.from_str(parsed_args.from_channel)
        to_channel = charmcraft.store.models.ChannelData.from_str(parsed_args.to_channel)

        if to_channel == from_channel:
            raise CraftError("Cannot promote from a channel to the same channel.")
        if to_channel.risk > from_channel.risk:
            command_parts = [
                "charmcraft",
                "promote-bundle",
                to_channel.name,
                from_channel.name,
            ]
            if parsed_args.output_bundle:
                command_parts.extend(["--output-bundle", parsed_args.output_bundle])
            for exclusion in parsed_args.exclude:
                command_parts.extend(["--exclude", exclusion])
            command = " ".join(command_parts)
            raise CraftError(
                f"Target channel ({to_channel.name}) must be lower risk "
                f"than the source channel ({from_channel.name}).\n"
                f"Did you mean: {command}"
            )
        if to_channel.track != from_channel.track:
            emit.message(
                "Promoting to a different track (from "
                f"{from_channel.track} to {to_channel.track})"
            )

        output_bundle: pathlib.Path | None = parsed_args.output_bundle
        if output_bundle is not None and output_bundle.exists():
            if output_bundle.is_file() or output_bundle.is_symlink():
                emit.verbose(f"Overwriting existing bundle file: {str(output_bundle)}")
            elif output_bundle.is_dir():
                emit.debug(f"Creating bundle file in {str(output_bundle)}")
                output_bundle /= "bundle.yaml"
            else:
                raise CraftError(f"Not a valid bundle output path: {str(output_bundle)}")
        elif output_bundle is not None:
            if not output_bundle.suffix:
                output_bundle /= "bundle.yaml"
            for parent in output_bundle.parents:
                if parent.exists():
                    if os.access(parent, os.W_OK):
                        break
                    raise CraftError(f"Bundle output directory not writable: {str(parent)}")

        # Load bundle
        # TODO: When this goes into the StoreService, use the service's own project_path
        bundle_path = self._services.package.project_dir / "bundle.yaml"
        bundle_config = utils.load_yaml(bundle_path)
        if bundle_config is None:
            raise CraftError(f"Missing or invalid main bundle file: {(str(bundle_path))}")
        bundle_name = bundle_config.get("name")
        if not bundle_name:
            raise CraftError(
                "Invalid bundle config; missing a 'name' field indicating the bundle's name in "
                f"file {str(bundle_path)!r}."
            )
        emit.progress("Determining charms to promote")
        charms = [c["charm"] for c in bundle_config.get("applications", {}).values()]
        errant_excludes = []
        for excluded in parsed_args.exclude:
            try:
                charms.remove(excluded)
            except ValueError:
                errant_excludes.append(excluded)
        if errant_excludes:
            bad_charms = utils.humanize_list(errant_excludes, "and")
            raise CraftError(
                f"Bundle does not contain the following excluded charms: {bad_charms}"
            )

        store = Store(env.get_store_config())
        registered_names: list[Entity] = store.list_registered_names(include_collaborations=True)
        name_map = {entity.name: entity for entity in registered_names}

        if bundle_name not in name_map:
            raise CraftError(
                f"Cannot modify bundle {bundle_name}. Ensure the bundle exists and that you have "
                "been made a collaborator."
            )
        elif name_map[bundle_name].entity_type != EntityType.bundle:
            entity_type = name_map[bundle_name].entity_type
            raise CraftError(f"Store Entity {bundle_name} is a {entity_type}, not a bundle.")

        invalid_charms = []
        non_charms = []
        for charm_name in charms:
            if charm_name not in name_map:
                invalid_charms.append(charm_name)
            elif name_map[charm_name].entity_type != EntityType.charm:
                non_charms.append(charm_name)
        if invalid_charms:
            charm_list = utils.humanize_list(invalid_charms, "and")
            raise CraftError(
                "The following entities do not exist or you are not a collaborator on them: "
                f"{charm_list}"
            )
        if non_charms:
            non_charm_list = utils.humanize_list(non_charms, "and")
            raise CraftError(f"The following store entities are not charms: {non_charm_list}")

        # Revision in the source channel
        channel_map, *_ = store.list_releases(bundle_name)
        bundle_revision = None
        for release in channel_map:
            if release.channel == from_channel.name:
                bundle_revision = release.revision
                break
        if bundle_revision is None:
            raise CraftError("Cannot find a bundle released to the given source channel.")

        # Get source channel charms
        charm_revisions: dict[str, int] = {}
        charm_resources: dict[str, list[str]] = collections.defaultdict(list)
        error_charms = []
        for charm_name in charms:
            channel_map, *_ = store.list_releases(charm_name)
            for release in channel_map:
                if release.channel == from_channel.name:
                    charm_revisions[charm_name] = release.revision
                    if release.resources:
                        charm_resources[charm_name] = release.resources
                    break
            else:
                error_charms.append(charm_name)
        if error_charms:
            charm_list = utils.humanize_list(error_charms, "and")
            raise CraftError(f"Not found in channel {from_channel.name}: {charm_list}")

        for application in bundle_config.get("applications", {}).values():
            application["channel"] = to_channel.name

        if parsed_args.output_bundle:
            with parsed_args.output_bundle.open("w+") as bundle_file:
                yaml.dump(bundle_config, bundle_file)

        for charm_name, charm_revision in charm_revisions.items():
            store.release(
                charm_name,
                charm_revision,
                channels=[to_channel.name],
                resources=charm_resources[charm_name],
            )

        # Export a temporary bundle file with the charms in the target channel
        with tempfile.TemporaryDirectory(prefix="charmcraft-") as bundle_dir:
            bundle_dir_path = pathlib.Path(bundle_dir) / bundle_name
            shutil.copytree(self._services.package.project_dir, bundle_dir_path)
            bundle_path = bundle_dir_path / "bundle.yaml"
            with bundle_path.open("w+") as bundle_file:
                yaml.dump(bundle_config, bundle_file)

            # Pack the bundle using the modified bundle file
            emit.verbose(f"Packing temporary bundle in {bundle_dir}...")
            lifecycle = parts.PartsLifecycle(
                {},
                work_dir=bundle_dir_path / "build",
                project_dir=bundle_dir_path,
                project_name=bundle_name,
                ignore_local_sources=[bundle_name + ".zip"],
            )
            try:
                lifecycle.run(Step.PRIME)
            except (RuntimeError, CraftError) as error:
                emit.debug(f"Error when running PRIME step: {error}")
                raise

            self._services.package.write_metadata(lifecycle.prime_dir)

            zipname = bundle_dir_path / (bundle_name + ".zip")
            utils.build_zip(zipname, lifecycle.prime_dir)

            # Upload the bundle and release it to the target channel.
            store.upload(bundle_name, zipname)
        release_info = store.release(bundle_name, bundle_revision, [parsed_args.to_channel], [])

        # There should only be one revision.
        release_info = release_info["released"][0]
        emit.message(
            f"Created revision {release_info['revision']!r} and "
            f"released it to the {release_info['channel']!r} channel"
        )


class CloseCommand(CharmcraftCommand):
    """Close a channel for a charm or bundle."""

    name = "close"
    help_msg = "Close a channel for a charm or bundle"
    overview = textwrap.dedent(
        """
        Close the specified channel for a charm or bundle.

        The channel is made up of `track/risk/branch` with both the track and
        the branch as optional items, so formally:

          [track/]risk[/branch]

        Channel risk must be one of stable, candidate, beta or edge. The
        track defaults to `latest` and branch has no default.

        Closing a channel will take you through login if needed.
    """
    )
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name of charm or bundle")
        parser.add_argument("channel", help="The channel to close")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        revision = None  # revision None will actually close the channel
        channels = [parsed_args.channel]  # the API accepts multiple channels, we have only one
        resources = []  # not really used when closing channels
        store.release(parsed_args.name, revision, channels, resources)
        emit.message(f"Closed {parsed_args.channel!r} channel for {parsed_args.name!r}.")


class StatusCommand(CharmcraftCommand):
    """Show channel status for a charm or bundle."""

    name = "status"
    help_msg = "Show channel and released revisions"
    overview = textwrap.dedent(
        """
        Show channels and released revisions in Charmhub.

        Charm revisions are not available to users until they are released
        into a channel. This command shows the various channels for a charm
        and whether there is a charm released.

        For example::

          $ charmcraft status
          Track    Base                   Channel    Version    Revision
          latest   ubuntu 20.04 (amd64)   stable     -          -
                                          candidate  -          -
                                          beta       -          -
                                          edge       1          1

        Showing channels will take you through login if needed.
    """
    )
    common = True
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument("name", help="The name of the charm or bundle")

    def _build_resources_repr(self, resources):
        """Build a representation of a list of resources."""
        if resources:
            result = ", ".join(f"{r.name} (r{r.revision})" for r in resources)
        else:
            result = "-"
        return result

    def _build_resources_prog(self, resources):
        """Build the programmatic object for a list of resources."""
        return [{"name": res.name, "revision": res.revision} for res in resources]

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        channel_map, channels, revisions = store.list_releases(parsed_args.name)
        if not channel_map:
            if parsed_args.format:
                emit.message(cli.format_content({}, parsed_args.format))
            else:
                emit.message("Nothing has been released yet.")
            return

        # group released revision by track and base
        releases_by_track = {}
        for item in channel_map:
            track = item.channel.split("/")[0]
            by_base = releases_by_track.setdefault(track, {})
            by_channel = by_base.setdefault(item.base, {})
            by_channel[item.channel] = item

        # group revision objects by revision number
        revisions_by_revno = {item.revision: item for item in revisions}

        # process and order the channels, while preserving the tracks order
        per_track = {}
        branch_present = False
        for channel in channels:
            # the branches list is really a dict just to deduplicate them (sometimes they come
            # repeated because of a Charmhub bug) without losing their order (that's why
            # a set is not used)
            nonbranches_list, branches = per_track.setdefault(channel.track, ([], {}))
            if channel.branch is None:
                # insert branch right after its fallback
                for idx, stored in enumerate(nonbranches_list, 1):
                    if stored.name == channel.fallback:
                        nonbranches_list.insert(idx, channel)
                        break
                else:
                    nonbranches_list.append(channel)
            else:
                branches[channel] = None
                branch_present = True

        headers = ["Track", "Base", "Channel", "Version", "Revision"]
        resources_present = any(release.resources for release in channel_map)
        if resources_present:
            headers.append("Resources")
        if branch_present:
            headers.append("Expires at")

        # show everything, grouped by tracks and bases, with regular channels at first and
        # branches (if any) after those
        human_data = []
        prog_data = []
        unreleased_track = {None: {}}  # base in None with no releases at all
        for track, (channels, branches) in per_track.items():
            prog_channels_info = []
            prog_data.append({"track": track, "mappings": prog_channels_info})

            releases_by_base = releases_by_track.get(track, unreleased_track)
            shown_track = track

            # bases are shown alphabetically ordered
            sorted_bases = sorted(
                releases_by_base, key=lambda b: b and (b.name, b.channel, b.architecture)
            )
            for base in sorted_bases:
                releases_by_channel = releases_by_base[base]
                if base is None:
                    shown_base = "-"
                    prog_base = None
                else:
                    shown_base = f"{base.name} {base.channel} ({base.architecture})"
                    prog_base = {
                        "name": base.name,
                        "channel": base.channel,
                        "architecture": base.architecture,
                    }

                prog_releases_info = []
                prog_channels_info.append({"base": prog_base, "releases": prog_releases_info})

                release_shown_for_this_track_base = False

                for channel in channels:
                    # get the release of the channel, fallbacking accordingly
                    release = releases_by_channel.get(channel.name)
                    if release is None:
                        version = revno = resources = (
                            "↑" if release_shown_for_this_track_base else "-"
                        )
                        prog_version = prog_revno = prog_resources = None
                        prog_status = "tracking" if release_shown_for_this_track_base else "closed"
                    else:
                        release_shown_for_this_track_base = True
                        revno = prog_revno = release.revision
                        revision = revisions_by_revno[revno]
                        version = prog_version = revision.version
                        resources = self._build_resources_repr(release.resources)
                        prog_resources = self._build_resources_prog(release.resources)
                        prog_status = "open"

                    datum = [shown_track, shown_base, channel.risk, version, revno]
                    if resources_present:
                        datum.append(resources)
                    human_data.append(datum)

                    prog_releases_info.append(
                        {
                            "status": prog_status,
                            "channel": channel.name,
                            "version": prog_version,
                            "revision": prog_revno,
                            "resources": prog_resources,
                            "expires_at": None,
                        }
                    )

                    # stop showing the track and base for the rest of the struct
                    shown_track = ""
                    shown_base = ""

                for branch in branches:
                    release = releases_by_channel.get(branch.name)
                    if release is None:
                        # not for this base!
                        continue
                    description = "/".join((branch.risk, branch.branch))
                    expiration = utils.format_timestamp(release.expires_at)
                    revision = revisions_by_revno[release.revision]
                    datum = ["", "", description, revision.version, release.revision]
                    if resources_present:
                        datum.append(self._build_resources_repr(release.resources))
                    datum.append(expiration)
                    human_data.append(datum)

                    prog_releases_info.append(
                        {
                            "status": "open",
                            "channel": branch.name,
                            "version": revision.version,
                            "revision": release.revision,
                            "resources": self._build_resources_prog(release.resources),
                            "expires_at": expiration,
                        }
                    )

        if parsed_args.format:
            emit.message(cli.format_content(prog_data, parsed_args.format))
        else:
            table = tabulate(human_data, headers=headers, tablefmt="plain", numalign="left")
            for line in table.splitlines():
                emit.message(line)


class CreateLibCommand(CharmcraftCommand):
    """Create a charm library."""

    name = "create-lib"
    help_msg = "Create a charm library"
    overview = textwrap.dedent(
        """
        Create a charm library.

        Charmcraft manages charm libraries, which are published by charmers
        to help other charmers integrate their charms. This command creates
        a new library in your charm which you are publishing for others.

        This command MUST be run inside your charm directory with a valid
        metadata.yaml. It will create the Python library with API version 0
        initially:

          lib/charms/<yourcharm>/v0/<name>.py

        Each library has a unique identifier assigned by Charmhub that
        supports accurate updates of libraries even if charms are renamed.
        Charmcraft will request a unique ID from Charmhub and initialise a
        template Python library.

        Creating a charm library will take you through login if needed.
    """
    )
    format_option = True
    always_load_project = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument("name", help="The name of the library file (e.g. 'db')")

    def run(self, parsed_args):
        """Run the command."""
        lib_name = parsed_args.name
        valid_all_chars = set(string.ascii_lowercase + string.digits + "_")
        valid_first_char = string.ascii_lowercase
        if set(lib_name) - valid_all_chars or not lib_name or lib_name[0] not in valid_first_char:
            raise CraftError(
                "Invalid library name. Must only use lowercase alphanumeric "
                "characters and underscore, starting with alpha."
            )

        charm_name = self._services.project.name or utils.get_name_from_metadata()
        if charm_name is None:
            raise CraftError(
                "Cannot find a valid charm name in charm definition. "
                "Check that you are using the correct project directory."
            )

        # '-' is valid in charm names, but not in a python import
        # mutate the name so the path is a valid import
        importable_charm_name = utils.create_importable_name(charm_name)

        # all libraries born with API version 0
        full_name = f"charms.{importable_charm_name}.v0.{lib_name}"
        lib_data = utils.get_lib_info(full_name=full_name)
        lib_path = lib_data.path
        if lib_path.exists():
            raise CraftError(f"This library already exists: {str(lib_path)!r}.")

        emit.progress(f"Creating library {lib_name}.")
        store = Store(env.get_store_config())
        lib_id = store.create_library_id(charm_name, lib_name)

        # create the new library file from the template
        environment = utils.get_templates_environment("charmlibs")
        template = environment.get_template("new_library.py.j2")
        context = {"lib_id": lib_id}
        try:
            lib_path.parent.mkdir(parents=True, exist_ok=True)
            lib_path.write_text(template.render(context))
        except OSError as exc:
            raise CraftError(f"Error writing the library in {str(lib_path)!r}: {exc!r}.")

        if parsed_args.format:
            info = {"library_id": lib_id}
            emit.message(cli.format_content(info, parsed_args.format))
        else:
            emit.message(f"Library {full_name} created with id {lib_id}.")
            emit.message(f"Consider 'git add {lib_path}'.")


class PublishLibCommand(CharmcraftCommand):
    """Publish one or more charm libraries."""

    name = "publish-lib"
    help_msg = "Publish one or more charm libraries"
    overview = textwrap.dedent(
        """
        Publish charm libraries.

        Upload and release in Charmhub the new api/patch version of the
        indicated library, or all the charm libraries if <library> is not
        provided.

        It will automatically take you through the login process if
        your credentials are missing or too old.

        Note that in order to be able to publish a charm library, you need
        to be signed into Charmcraft as a user that has permissions to
        publish libraries to this charm. In particular you need to be the
        owner of this charm or registered as a contributor to the
        charm (a status that can be requested via Discourse).
    """
    )
    format_option = True
    always_load_project = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument(
            "library",
            nargs="?",
            help="Library to publish (e.g. charms.mycharm.v2.foo.); optional, default to all",
        )

    def run(self, parsed_args):
        """Run the command."""
        charm_name = self._services.project.name or utils.get_name_from_metadata()
        if charm_name is None:
            raise CraftError(
                "Cannot find a valid charm name in charm definition. "
                "Check that you are using the correct project directory."
            )

        if parsed_args.library:
            lib_data = utils.get_lib_info(full_name=parsed_args.library)
            if not lib_data.path.exists():
                raise CraftError(
                    f"The specified library was not found at path {str(lib_data.path)!r}."
                )
            if lib_data.charm_name != charm_name:
                raise CraftError(
                    f"The library {lib_data.full_name} does not belong to this charm {charm_name!r}."
                )
            local_libs_data = [lib_data]
        else:
            local_libs_data = utils.get_libs_from_tree(charm_name)
            found_libs = [lib_data.full_name for lib_data in local_libs_data]
            (charmlib_path,) = {lib_data.path.parent.parent for lib_data in local_libs_data}
            emit.debug(f"Libraries found under {str(charmlib_path)!r}: {found_libs}")

        # check if something needs to be done
        store = Store(env.get_store_config())
        to_query = [{"lib_id": lib.lib_id, "api": lib.api} for lib in local_libs_data]
        libs_tips = store.get_libraries_tips(to_query)
        analysis = []
        for lib_data in local_libs_data:
            emit.debug(f"Verifying local lib {lib_data}")
            tip = libs_tips.get((lib_data.lib_id, lib_data.api))
            emit.debug(f"Store tip: {tip}")

            # big decision branch to analyse if the library needs publishing or there is a reason
            # not to (to be actioned later in consideration of having a error situation or not)
            error_message = None
            if tip is None:
                # needs to first publish
                pass
            elif tip.patch > lib_data.patch:
                # the store is more advanced than local
                error_message = (
                    f"Library {lib_data.full_name} is out-of-date locally, Charmhub has "
                    f"version {tip.api:d}.{tip.patch:d}, please "
                    "fetch the updates before publishing."
                )
            elif tip.patch == lib_data.patch:
                # the store has same version numbers than local
                if tip.content_hash == lib_data.content_hash:
                    error_message = f"Library {lib_data.full_name} is already updated in Charmhub."
                else:
                    # but shouldn't as hash is different!
                    error_message = (
                        f"Library {lib_data.full_name} version {tip.api:d}.{tip.patch:d} "
                        "is the same than in Charmhub but content is different"
                    )
            elif tip.patch + 1 == lib_data.patch:
                # local is correctly incremented
                if tip.content_hash == lib_data.content_hash:
                    # but shouldn't as hash is the same!
                    error_message = (
                        f"Library {lib_data.full_name} LIBPATCH number was incorrectly "
                        "incremented, Charmhub has the "
                        f"same content in version {tip.api:d}.{tip.patch:d}."
                    )
            else:
                error_message = (
                    f"Library {lib_data.full_name} has a wrong LIBPATCH number, it's too high "
                    "and needs to be consecutive, Charmhub "
                    f"highest version is {tip.api:d}.{tip.patch:d}."
                )
            analysis.append((lib_data, error_message))

        # work on the analysis result, showing messages to the user if not programmatic output
        for lib_data, error_message in analysis:
            if error_message is None:
                store.create_library_revision(
                    lib_data.charm_name,
                    lib_data.lib_id,
                    lib_data.api,
                    lib_data.patch,
                    lib_data.content,
                    lib_data.content_hash,
                )
                message = (
                    f"Library {lib_data.full_name} sent to the store with "
                    f"version {lib_data.api:d}.{lib_data.patch:d}"
                )
            else:
                message = error_message
            if not parsed_args.format:
                emit.message(message)

        if parsed_args.format:
            output_data = []
            for lib_data, error_message in analysis:
                datum = {
                    "charm_name": lib_data.charm_name,
                    "library_name": lib_data.lib_name,
                    "library_id": lib_data.lib_id,
                    "api": lib_data.api,
                }
                if error_message is None:
                    datum["published"] = {
                        "patch": lib_data.patch,
                        "content_hash": lib_data.content_hash,
                    }
                else:
                    datum["error_message"] = error_message
                output_data.append(datum)
            emit.message(cli.format_content(output_data, parsed_args.format))


class FetchLibCommand(CharmcraftCommand):
    """Fetch one or more charm libraries."""

    name = "fetch-lib"
    help_msg = "Fetch one or more charm libraries"
    overview = textwrap.dedent(
        """
        Fetch charm libraries.

        The first time a library is downloaded the command will create the needed
        directories to place it, subsequent fetches will just update the local copy.

        You can specify the library to update or download by building its fully
        qualified name with the charm and library names, and the desired API
        version. For example, to fetch the API version 3 of library 'somelib'
        from charm `specialcharm`, do:

            $ charmcraft fetch-lib charms.specialcharm.v3.somelib
            Library charms.specialcharm.v3.somelib version 3.7 downloaded.

        If the command is executed without parameters, it will update all the currently
        downloaded libraries.
    """
    )
    format_option = True
    always_load_project = True
    hidden = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument(
            "library",
            nargs="?",
            help="Library to fetch (e.g. charms.mycharm.v2.foo.); optional, default to all",
        )

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Run the command."""
        if parsed_args.library:
            local_libs_data = [utils.get_lib_info(full_name=parsed_args.library)]
        else:
            local_libs_data = utils.get_libs_from_tree()
            found_libs = [lib_data.full_name for lib_data in local_libs_data]
            emit.debug(f"Libraries found under 'lib/charms': {found_libs}")

        # get tips from the Store
        store = Store(env.get_store_config(), needs_auth=False)
        to_query = []
        for lib in local_libs_data:
            if lib.lib_id is None:
                item = {"charm_name": lib.charm_name, "lib_name": lib.lib_name, "api": lib.api}
            else:
                item = {"lib_id": lib.lib_id, "api": lib.api}
            to_query.append(item)
        libs_tips = store.get_libraries_tips(to_query)

        # check if something needs to be done
        analysis = []
        for lib_data in local_libs_data:
            emit.debug(f"Verifying local lib {lib_data}")
            # fix any missing lib id using the Store info
            if lib_data.lib_id is None:
                for tip in libs_tips.values():
                    if lib_data.charm_name == tip.charm_name and lib_data.lib_name == tip.lib_name:
                        lib_data = dataclasses.replace(lib_data, lib_id=tip.lib_id)
                        break

            tip = libs_tips.get((lib_data.lib_id, lib_data.api))
            emit.debug(f"Store tip: {tip}")
            error_message = None
            if tip is None:
                error_message = f"Library {lib_data.full_name} not found in Charmhub."
            elif tip.patch > lib_data.patch:
                # the store has a higher version than local
                pass
            elif tip.patch < lib_data.patch:
                # the store has a lower version numbers than local
                error_message = (
                    f"Library {lib_data.full_name} has local changes, cannot be updated."
                )
            else:
                # same versions locally and in the store
                if tip.content_hash == lib_data.content_hash:
                    error_message = (
                        f"Library {lib_data.full_name} was already up to date in "
                        f"version {tip.api:d}.{tip.patch:d}."
                    )
                else:
                    error_message = (
                        f"Library {lib_data.full_name} has local changes, cannot be updated."
                    )
            analysis.append((lib_data, error_message))

        full_lib_data = []
        for lib_data, error_message in analysis:
            if error_message is None:
                downloaded = store.get_library(lib_data.charm_name, lib_data.lib_id, lib_data.api)
                if lib_data.content is None:
                    # locally new
                    lib_data.path.parent.mkdir(parents=True, exist_ok=True)
                    lib_data.path.write_text(downloaded.content)
                    message = (
                        f"Library {lib_data.full_name} version "
                        f"{downloaded.api:d}.{downloaded.patch:d} downloaded."
                    )
                else:
                    # XXX Facundo 2020-12-17: manage the case where the library was renamed
                    # (related GH issue: #214)
                    lib_data.path.write_text(downloaded.content)
                    message = (
                        f"Library {lib_data.full_name} updated to version "
                        f"{downloaded.api:d}.{downloaded.patch:d}."
                    )

                # fix lib_data with new info so it's later available
                # for the case of programmatic output
                lib_data = dataclasses.replace(
                    lib_data,
                    patch=downloaded.patch,
                    content=downloaded.content,
                    content_hash=downloaded.content_hash,
                )
            else:
                message = error_message
            full_lib_data.append((lib_data, error_message))

            if not parsed_args.format:
                emit.message(message)

        if parsed_args.format:
            output_data = []
            for lib_data, error_message in full_lib_data:
                datum: dict[str, Any] = {
                    "charm_name": lib_data.charm_name,
                    "library_name": lib_data.lib_name,
                    "library_id": lib_data.lib_id,
                    "api": lib_data.api,
                }
                if error_message is None:
                    datum["fetched"] = {
                        "patch": lib_data.patch,
                        "content_hash": lib_data.content_hash,
                    }
                else:
                    datum["error_message"] = error_message
                output_data.append(datum)
            emit.message(cli.format_content(output_data, parsed_args.format))


class FetchLibs(CharmcraftCommand):
    """Fetch libraries defined in charmcraft.yaml."""

    name = "fetch-libs"
    help_msg = "Fetch one or more charm libraries"
    overview = textwrap.dedent(
        """
        Fetch charm libraries defined in charmcraft.yaml.

        For each library in the top-level `charm-libs` key, fetch the latest library
        version matching those requirements.

        For example::

            charm-libs:
            # Fetch lib with API version 0.
            # If `fetch-libs` is run and a newer minor version is available,
            # it will be fetched from the store.
            - lib: postgresql.postgres_client
              version: "0"
            # Always fetch precisely version 0.57.
            - lib: mysql.client
              version: "0.57"
        """
    )
    format_option = True
    always_load_project = True

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Fetch libraries."""
        store = self._services.store
        charm_libs = self._services.project.charm_libs
        if not charm_libs:
            raise errors.LibraryError(
                message="No dependent libraries declared in charmcraft.yaml.",
                resolution="Add a 'charm-libs' section to charmcraft.yaml.",
                retcode=78,  # EX_CONFIG: configuration error
            )
        emit.progress("Getting library metadata from charmhub")
        libs_metadata = store.get_libraries_metadata_by_name(charm_libs)
        declared_libs = {lib.lib: lib for lib in charm_libs}
        missing_store_libs = declared_libs.keys() - libs_metadata.keys()
        if missing_store_libs:
            missing_libs_source = [
                declared_libs[lib].model_dump() for lib in sorted(missing_store_libs)
            ]
            libs_yaml = util.dump_yaml(missing_libs_source)
            raise errors.CraftError(
                f"Could not find the following libraries on charmhub:\n{libs_yaml}",
                resolution="Use 'charmcraft list-lib' to check library names and versions.",
                reportable=False,
                logpath_report=False,
            )

        emit.trace(f"Library metadata retrieved: {libs_metadata}")
        local_libs = {
            f"{lib.charm_name}.{lib.lib_name}": lib for lib in utils.get_libs_from_tree()
        }
        emit.trace(f"Local libraries: {local_libs}")

        downloaded_libs = 0
        for lib_md in libs_metadata.values():
            lib_name = f"{lib_md.charm_name}.{lib_md.lib_name}"
            local_lib = local_libs.get(lib_name)
            if local_lib and local_lib.content_hash == lib_md.content_hash:
                emit.progress(
                    f"Skipping {lib_name} because the same file already exists on "
                    f"disk (hash: {lib_md.content_hash}). "
                    "Delete the file and re-run 'charmcraft fetch-libs' to force re-download.",
                    permanent=True,
                )
                continue
            lib_name = utils.get_lib_module_name(lib_md.charm_name, lib_md.lib_name, lib_md.api)
            emit.progress(f"Downloading {lib_name}")
            lib = store.get_library(
                charm_name=lib_md.charm_name,
                library_id=lib_md.lib_id,
                api=lib_md.api,
                patch=lib_md.patch,
            )
            if lib.content is None:
                raise errors.CraftError(
                    f"Store returned no content for '{lib.charm_name}.{lib.lib_name}'"
                )
            downloaded_libs += 1
            lib_path = utils.get_lib_path(lib_md.charm_name, lib_md.lib_name, lib_md.api)
            lib_path.parent.mkdir(exist_ok=True, parents=True)
            lib_path.write_text(lib.content)
            emit.debug(f"Downloaded {lib_name}.")

        emit.message(f"Downloaded {downloaded_libs} charm libraries.")


class ListLibCommand(CharmcraftCommand):
    """List all libraries belonging to a charm."""

    name = "list-lib"
    help_msg = "List all libraries from a charm"
    overview = textwrap.dedent(
        """
        List all libraries from a charm.

        For each library, it will show the name and the api and patch versions
        for its tip.

        For example:

            $ charmcraft list-lib my-charm
            Library name    API    Patch
            my_great_lib    0      3
            my_great_lib    1      0
            other_lib       0      5

        To fetch one of the shown libraries you can use the `fetch-lib` command.
    """
    )
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument(
            "name",
            nargs="?",
            help=(
                "The name of the charm (optional, will get the name from"
                "metadata.yaml if not given)"
            ),
        )

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = utils.get_name_from_metadata()
            if charm_name is None:
                raise CraftError(
                    "Can't access name in 'metadata.yaml' file. The 'list-lib' command must "
                    "either be executed from a valid project directory, or specify a charm "
                    "name using the --charm-name option."
                )

        # get tips from the Store
        store = Store(env.get_store_config(), needs_auth=False)
        to_query = [{"charm_name": charm_name}]
        libs_tips = store.get_libraries_tips(to_query)

        # order it
        libs_data = sorted(libs_tips.values(), key=attrgetter("lib_name", "api", "patch"))

        if parsed_args.format:
            info = [
                {
                    "charm_name": item.charm_name,
                    "library_name": item.lib_name,
                    "library_id": item.lib_id,
                    "api": item.api,
                    "patch": item.patch,
                    "content_hash": item.content_hash,
                }
                for item in libs_data
            ]
            emit.message(cli.format_content(info, parsed_args.format))
            return

        if not libs_tips:
            emit.message(f"No libraries found for charm {charm_name}.")
            return

        headers = ["Library name", "API", "Patch"]
        data = [(item.lib_name, item.api, item.patch) for item in libs_data]

        table = tabulate(data, headers=headers, tablefmt="plain", numalign="left")
        for line in table.splitlines():
            emit.message(line)


class ListResourcesCommand(CharmcraftCommand):
    """List the resources associated with a given charm in Charmhub."""

    name = "resources"
    help_msg = "List the resources associated with a given charm in Charmhub"
    overview = textwrap.dedent(
        """
        An overview of the resources associated with a given charm in Charmhub.

        Listing resources will take you through login if needed.

    """
    )
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument("charm_name", metavar="charm-name", help="The name of the charm")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        result = store.list_resources(parsed_args.charm_name)

        if parsed_args.format:
            info = [
                {
                    "charm_revision": item.revision,
                    "name": item.name,
                    "type": item.resource_type,
                    "optional": item.optional,
                }
                for item in result
            ]
            emit.message(cli.format_content(info, parsed_args.format))
            return

        if not result:
            emit.message(f"No resources associated to {parsed_args.charm_name}.")
            return

        headers = ["Charm Rev", "Resource", "Type", "Optional"]
        by_revision = {}
        for item in result:
            by_revision.setdefault(item.revision, []).append(item)
        data = []
        for revision, items in sorted(by_revision.items(), reverse=True):
            initial, *rest = sorted(items, key=attrgetter("name"))
            data.append((revision, initial.name, initial.resource_type, initial.optional))
            data.extend(("", item.name, item.resource_type, item.optional) for item in rest)

        table = tabulate(data, headers=headers, tablefmt="plain", numalign="left")
        for line in table.splitlines():
            emit.message(line)


class UploadResourceCommand(CharmcraftCommand):
    """Upload a resource to Charmhub."""

    name = "upload-resource"
    help_msg = "Upload a resource to Charmhub"
    overview = textwrap.dedent(
        """
        Upload a resource to Charmhub.

        Push a resource content to Charmhub, associating it to the
        specified charm. This charm needs to have the resource declared
        in its metadata (in a previously uploaded to Charmhub revision).

        The resource can be a file from your computer (use the `--filepath`
        option) or an OCI Image (use the `--image` option to indicate the
        image digest or id), which can be already in Canonical's registry
        and used directly, or locally in your computer and will be uploaded
        and used.

        Upload will take you through login if needed.
    """
    )
    common = True
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument(
            "charm_name",
            metavar="charm-name",
            help="The charm name to associate the resource",
        )
        parser.add_argument("resource_name", metavar="resource-name", help="The resource name")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--filepath",
            type=utils.SingleOptionEnsurer(utils.useful_filepath),
            help="The file path of the resource content to upload",
        )
        group.add_argument(
            "--image",
            type=utils.SingleOptionEnsurer(str),
            help=(
                'The digest (remote or local) or id (local, exclude "sha256:") of the OCI image'
            ),
        )
        parser.add_argument(
            "--arch",
            type=utils.ChoicesList(const.SUPPORTED_ARCHITECTURES | {"all"}),
            help="The architectures valid for this file resource. If none are provided, the resource is uploaded without architecture information.",
        )

    def run(self, parsed_args: argparse.Namespace) -> int:
        """Run the command."""
        store = Store(env.get_store_config())

        if parsed_args.arch:
            if parsed_args.image:
                raise ArgumentParsingError(
                    "Cannot specify an architecture for an OCI image. OCI images contain architecture metadata that is used."
                )
            architectures = parsed_args.arch
            utils.validate_architectures(architectures, allow_all=True)
        else:
            architectures = ["all"]

        if parsed_args.filepath:
            emit.progress(f"Uploading resource directly from file {str(parsed_args.filepath)!r}.")
            bases = [{"name": "all", "channel": "all", "architectures": architectures}]
            result = store.upload_resource(
                parsed_args.charm_name,
                parsed_args.resource_name,
                ResourceType.file,
                parsed_args.filepath,
                bases=bases,
            )
        elif parsed_args.image:
            emit.progress("Getting image")
            emit.debug("Trying to get image from Docker")
            image_service = self._services.image
            # Check Docker first for backwards compatibility - prefer to get from
            # Docker than from a local path if Docker contains the image.
            if digest := image_service.get_maybe_id_from_docker(parsed_args.image):
                emit.debug("Image is available via the local Docker daemon.")
                source_path = f"docker-daemon:{digest}"
            elif (image_path := pathlib.Path(parsed_args.image)).exists():
                emit.debug("Image is a path.")
                if image_path.is_file():
                    emit.debug("Image is a rock or other OCI archive.")
                    source_path = f"oci-archive:{image_path.as_posix()}"
                elif image_path.is_dir():
                    emit.debug("Image is an OCI directory.")
                    source_path = f"oci:{image_path.as_posix()}"
                else:
                    raise CraftError(
                        f"Not a valid file or directory: {image_path.as_posix()!r}",
                        resolution="Pass an OCI archive file such as a rock.",
                    )
            elif re.match("^[a-z-]+:", parsed_args.image):
                emit.debug("Presuming an OCI path that skopeo understands.")
                source_path = parsed_args.image
            else:
                raise CraftError(
                    "Unknown OCI image reference.",
                    details="Passed image reference is not a Docker image ID, image digest, existing file or container transport string.",
                    resolution="Pass a valid container transport string.",
                )
            emit.debug(f"Using source path {source_path!r}")

            emit.progress("Inspecting source image")
            image_metadata = image_service.inspect(source_path)

            credentials = store.get_oci_registry_credentials(
                parsed_args.charm_name, parsed_args.resource_name
            )

            if const.STORE_REGISTRY_ENV_VAR in os.environ:
                # If the user has specified a registry to use, replace what the store
                # gives with that registry.
                registry_url = os.environ[const.STORE_REGISTRY_ENV_VAR]
                registry_url_without_scheme = registry_url.partition("://")[2]
                image_name = credentials.image_name.split("/", 1)[1]
                dest_path = f"docker://{registry_url_without_scheme}/{image_name}"
            else:
                dest_path = f"docker://{credentials.image_name}"

            with emit.open_stream("Uploading") as stream:
                image_service.copy(
                    source_path,
                    dest_path,
                    stream,
                    dest_username=credentials.username,
                    dest_password=credentials.password,
                )

            image_arch = [
                craft_platforms.DebianArchitecture.from_machine(arch).value
                for arch in image_metadata.architectures
            ]
            bases = [{"name": "all", "channel": "all", "architectures": image_arch}]

            # all is green, get the blob to upload to Charmhub
            content = store.get_oci_image_blob(
                parsed_args.charm_name, parsed_args.resource_name, image_metadata.digest
            )
            with tempfile.NamedTemporaryFile(
                mode="w+", prefix="image-resource", suffix=".json"
            ) as resource_file:
                resource_file.write(content)
                resource_file.flush()

                result = store.upload_resource(
                    parsed_args.charm_name,
                    parsed_args.resource_name,
                    ResourceType.oci_image,
                    pathlib.Path(resource_file.name),
                    bases=bases,
                )
        else:
            raise CraftError("Either a file path or an image descriptor must be passed.")

        if result.ok:
            if parsed_args.format:
                info = {"revision": result.revision}
                emit.message(cli.format_content(info, parsed_args.format))
            else:
                emit.message(
                    f"Revision {result.revision} created of resource "
                    f"{parsed_args.resource_name!r} for charm {parsed_args.charm_name!r}.",
                )
            retcode = 0
        else:
            if parsed_args.format:
                info = {
                    "errors": [
                        {"code": error.code, "message": error.message} for error in result.errors
                    ]
                }
                emit.message(cli.format_content(info, parsed_args.format))
            else:
                emit.message(f"Upload failed with status {result.status!r}:")
                for error in result.errors:
                    emit.message(f"- {error.code}: {error.message}")
            retcode = 1
        return retcode


class SetResourceArchitecturesCommand(CharmcraftCommand):
    """Set the architectures for a resource revision."""

    name = "set-resource-architectures"
    help_msg = "Set the architectures for a resource revision in Charmhub"
    overview = textwrap.dedent(
        """
        Set the architectures for a resource revision in Charmhub.

        Each resource revision is tagged with one or more architectures. If a
        revision is incorrectly tagged, this command can modify the architecture
        tags for that resource revision.

        For example:

            $ charmcraft resource-revisions my-charm my-resource
            Revision    Created at               Size  Architectures
            1           2020-11-15 T11:13:15Z  183151  riscv64
            $ charmcraft set-resource-architectures my-charm my-resource --revision=1 arm64,armhf
            Revision 1 of 'my-resource' on charm 'my-charm' set to architectures: arm64,armhf
            $ charmcraft resource-revisions my-charm my-resource
            Revision    Created at               Size  Architectures
            1           2020-11-15 T11:13:15Z  183151  arm64,armhf
        """
    )
    format_option = True

    def fill_parser(self, parser) -> None:
        """Add set-resource-architectures specific command parameters."""
        super().fill_parser(parser)
        parser.add_argument(
            "charm_name",
            metavar="charm-name",
            help="The name of the charm",
        )
        parser.add_argument("resource_name", metavar="resource-name", help="The resource name")
        parser.add_argument(
            "--revision",
            dest="revisions",
            action="append",
            type=int,
            required=True,
            help="A revision to update",
        )
        parser.add_argument(
            "arch",
            type=utils.ChoicesList(const.SUPPORTED_ARCHITECTURES | {"all"}),
            help="Comma-separated list of architectures",
        )

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Run the command."""
        store = self._services.store

        updates = store.set_resource_revisions_architectures(
            name=parsed_args.charm_name,
            resource_name=parsed_args.resource_name,
            updates={revision: parsed_args.arch for revision in parsed_args.revisions},
        )

        fmt = parsed_args.format or cli.OutputFormat.TABLE
        self.write_output(fmt, updates)

    @staticmethod
    def write_output(
        fmt: cli.OutputFormat,
        updates: Collection[models.resource_revision_model.CharmResourceRevision],
    ) -> None:
        """Write formatted output for this command to the terminal."""
        if fmt == cli.OutputFormat.TABLE:
            if not updates:
                emit.message("No revisions updated.")
                return

            emit.progress(f"{len(updates)} revision(s) updated.", permanent=True)

            updates_dicts = [
                {
                    "Revision": update.revision,
                    "Updated At": (
                        utils.format_timestamp(update.updated_at)
                        if update.updated_at is not None
                        else "--"
                    ),
                    "Architectures": ",".join(_get_architectures_from_bases(update.bases)),
                }
                for update in sorted(updates, key=lambda rev: int(rev.revision), reverse=True)
            ]
        else:
            updates_dicts = [
                {
                    "revision": update.revision,
                    "updated_at": (
                        update.updated_at.isoformat() if update.updated_at is not None else None
                    ),
                    "architectures": _get_architectures_from_bases(update.bases),
                }
                for update in updates
            ]

        emit.message(cli.format_content(updates_dicts, fmt))


class ListResourceRevisionsCommand(CharmcraftCommand):
    """List revisions for a resource of a charm."""

    name = "resource-revisions"
    help_msg = "List revisions for a resource associated to a charm in Charmhub"
    overview = textwrap.dedent(
        """
        Show size and date for each resource revision in Charmhub.

        For example:

           $ charmcraft resource-revisions my-charm my-resource
           Revision    Created at               Size
           1           2020-11-15 T11:13:15Z  183151

        Listing revisions will take you through login if needed.
    """
    )
    format_option = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        super().fill_parser(parser)
        parser.add_argument(
            "charm_name",
            metavar="charm-name",
            help="The charm name to associate the resource",
        )
        parser.add_argument("resource_name", metavar="resource-name", help="The resource name")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(env.get_store_config())
        result = store.list_resource_revisions(parsed_args.charm_name, parsed_args.resource_name)

        if parsed_args.format:
            info = [
                {
                    "revision": item.revision,
                    "created at": item.created_at.isoformat(),
                    "size": item.size,
                    "bases": [base.model_dump() for base in item.bases],
                }
                for item in result
            ]
            emit.message(cli.format_content(info, parsed_args.format))
            return

        if not result:
            emit.message("No revisions found.")
            return

        headers = ["Revision", "Created at", "Size", "Architectures"]
        custom_alignment = ["left", "left", "right"]
        result.sort(key=attrgetter("revision"), reverse=True)
        data = [
            (
                item.revision,
                utils.format_timestamp(item.created_at),
                naturalsize(item.size, gnu=True),
                ",".join(_get_architectures_from_bases(item.bases)),
            )
            for item in result
        ]

        table = tabulate(data, headers=headers, tablefmt="plain", colalign=custom_alignment)
        for line in table.splitlines():
            emit.message(line)


def _get_architectures_from_bases(bases: typing.Iterable[ResponseCharmResourceBase]) -> list[str]:
    """Get a list of all architectures from an iterable of resource bases."""
    architectures = set()
    for base in bases:
        for architecture in base.architectures:
            architectures.add(architecture)
    return sorted(architectures)
