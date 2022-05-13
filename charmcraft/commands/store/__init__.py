# Copyright 2020-2022 Canonical Ltd.
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

import ast
import hashlib
import pathlib
import string
import tempfile
import textwrap
import zipfile
from collections import namedtuple
from operator import attrgetter

import yaml
from craft_cli import emit
from craft_cli.errors import CraftError
from craft_store import attenuations
from craft_store.errors import CredentialsUnavailable
from humanize import naturalsize
from tabulate import tabulate

from charmcraft.cmdbase import BaseCommand
from charmcraft.utils import (
    ResourceOption,
    SingleOptionEnsurer,
    format_timestamp,
    get_templates_environment,
    useful_filepath,
)

from .store import Store
from .registry import ImageHandler, OCIRegistry

# some types
EntityType = namedtuple("EntityType", "charm bundle")(charm="charm", bundle="bundle")
ResourceType = namedtuple("ResourceType", "file oci_image")(file="file", oci_image="oci-image")

LibData = namedtuple(
    "LibData",
    "lib_id api patch content content_hash full_name path lib_name charm_name",
)

# The token used in the 'init' command (as bytes for easier comparison)
INIT_TEMPLATE_TOKEN = b"TEMPLATE-TODO"

# the list of valid attenuations to restrict login credentials
VALID_ATTENUATIONS = {getattr(attenuations, x) for x in dir(attenuations) if x.isupper()}


def get_name_from_metadata():
    """Return the name if present and plausible in metadata.yaml."""
    try:
        with open("metadata.yaml", "rb") as fh:
            metadata = yaml.safe_load(fh)
        charm_name = metadata["name"]
    except (yaml.error.YAMLError, OSError, KeyError):
        return
    return charm_name


def create_importable_name(charm_name):
    """Convert a charm name to something that is importable in python."""
    return charm_name.replace("-", "_")


def create_charm_name_from_importable(charm_name):
    """Convert a charm name from the importable form to the real form."""
    # _ is invalid in charm names, so we know it's intended to be '-'
    return charm_name.replace("_", "-")


class LoginCommand(BaseCommand):
    """Login to Charmhub."""

    name = "login"
    help_msg = "Login to Charmhub"
    overview = textwrap.dedent(
        """
        Login to Charmhub.

        Charmcraft will provide a URL for the Charmhub login. When you have
        successfully logged in, charmcraft will store a token for ongoing
        access to Charmhub at the CLI (if `--export` option was not used
        otherwise it will only save the credentials in the indicated file).

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
            "--export", type=pathlib.Path, help="The file to save the credentials to"
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
                # XXX Facundo 2021-11-17: This is imported here to break a cyclic import. It will
                # go away when we move this error to craft-cli lib.
                from charmcraft.main import ArgumentParsingError

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
            ("charms", parsed_args.charm),
            ("bundles", parsed_args.bundle),
            ("permissions", parsed_args.permission),
        ]
        kwargs = {}
        for arg_name, namespace_value in restrictive_options_map:
            if namespace_value is not None:
                kwargs[arg_name] = namespace_value

        ephemeral = parsed_args.export is not None
        store = Store(self.config.charmhub, ephemeral=ephemeral)
        credentials = store.login(**kwargs)
        if parsed_args.export is None:
            macaroon_info = store.whoami()
            emit.message(f"Logged in as '{macaroon_info.account.username}'.")
        else:
            parsed_args.export.write_text(credentials)
            emit.message(f"Login successful. Credentials exported to {str(parsed_args.export)!r}.")


class LogoutCommand(BaseCommand):
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
        store = Store(self.config.charmhub)
        try:
            store.logout()
            emit.message("Charmhub token cleared.")
        except CredentialsUnavailable:
            emit.message("You are not logged in to Charmhub.")


class WhoamiCommand(BaseCommand):
    """Show login information."""

    name = "whoami"
    help_msg = "Show your Charmhub login status"
    overview = textwrap.dedent(
        """
        Show your Charmhub login status.

        See also `charmcraft login` and `charmcraft logout`.
    """
    )

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        try:
            macaroon_info = store.whoami()
        except CredentialsUnavailable:
            emit.message("You are not logged in to Charmhub.")
            return

        emit.message(f"name: {macaroon_info.account.name}")
        emit.message(f"username: {macaroon_info.account.username}")
        emit.message(f"id: {macaroon_info.account.id}")

        if macaroon_info.permissions:
            emit.message("permissions:")
            for item in macaroon_info.permissions:
                emit.message(f"- {item}")

        if macaroon_info.packages:
            grouped = {}
            for package in macaroon_info.packages:
                grouped.setdefault(package.type, []).append(package)
            for package_type, title in [("charm", "charms"), ("bundle", "bundles")]:
                if package_type in grouped:
                    emit.message(f"{title}:")
                    for item in grouped[package_type]:
                        if item.name is not None:
                            emit.message(f"- name: {item.name}")
                        elif item.id is not None:
                            emit.message(f"- id: {item.id}")

        if macaroon_info.channels:
            emit.message("channels:")
            for item in macaroon_info.channels:
                emit.message(f"- {item}")


class RegisterCharmNameCommand(BaseCommand):
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
        store = Store(self.config.charmhub)
        store.register_name(parsed_args.name, EntityType.charm)
        emit.message(f"You are now the publisher of charm {parsed_args.name!r} in Charmhub.")


class RegisterBundleNameCommand(BaseCommand):
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
        store = Store(self.config.charmhub)
        store.register_name(parsed_args.name, EntityType.bundle)
        emit.message(f"You are now the publisher of bundle {parsed_args.name!r} in Charmhub.")


class ListNamesCommand(BaseCommand):
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

        Listing names will take you through login if needed.
    """
    )
    common = True

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        result = store.list_registered_names()
        if not result:
            emit.message("No charms or bundles registered.")
            return

        headers = ["Name", "Type", "Visibility", "Status"]
        data = []
        for item in result:
            visibility = "private" if item.private else "public"
            data.append(
                [
                    item.name,
                    item.entity_type,
                    visibility,
                    item.status,
                ]
            )

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
                "Bad 'metadata.yaml' file inside charm zip {!r}: must be a valid YAML with "
                "a 'name' key.".format(str(filepath))
            ) from err
    elif "bundle.yaml" in zf.namelist():
        try:
            name = yaml.safe_load(zf.read("bundle.yaml"))["name"]
        except Exception as err:
            raise CraftError(
                "Bad 'bundle.yaml' file inside bundle zip {!r}: must be a valid YAML with "
                "a 'name' key.".format(str(filepath))
            ) from err
    else:
        raise CraftError(
            "The indicated zip file {!r} is not a charm ('metadata.yaml' not found) "
            "nor a bundle ('bundle.yaml' not found).".format(str(filepath))
        )

    return name


class UploadCommand(BaseCommand):
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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("filepath", type=useful_filepath, help="The charm or bundle to upload")
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
            type=ResourceOption(),
            default=[],
            help=(
                "The resource(s) to attach to the release, in the <name>:<revision> format "
                "(this option can be indicated multiple times)"
            ),
        )

    def _validate_template_is_handled(self, filepath):
        """Verify the zip does not have any file with the 'init' template TODO marker.

        This is important to avoid uploading low-quality charms that are just
        bootstrapped and not corrected.
        """
        # we're already sure we can open it ok
        zf = zipfile.ZipFile(str(filepath))

        tainted_filenames = []
        for name in zf.namelist():
            content = zf.read(name)
            if INIT_TEMPLATE_TOKEN in content:
                tainted_filenames.append(name)

        if tainted_filenames:
            raise CraftError(
                "Cannot upload the charm as it include the following files with a leftover "
                "TEMPLATE-TODO token from when the project was created using the 'init' "
                "command: {}".format(", ".join(tainted_filenames))
            )

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            name = parsed_args.name
        else:
            name = get_name_from_zip(parsed_args.filepath)
        self._validate_template_is_handled(parsed_args.filepath)
        store = Store(self.config.charmhub)
        result = store.upload(name, parsed_args.filepath)
        if result.ok:
            emit.message(f"Revision {result.revision} of {str(name)!r} created")
            if parsed_args.release:
                # also release!
                store.release(name, result.revision, parsed_args.release, parsed_args.resource)
                msg = "Revision released to {}"
                args = [", ".join(parsed_args.release)]
                if parsed_args.resource:
                    msg += " (attaching resources: {})"
                    args.append(
                        ", ".join(f"{r.name!r} r{r.revision}" for r in parsed_args.resource)
                    )
                emit.message(msg.format(*args))
            retcode = 0
        else:
            emit.message(f"Upload failed with status {result.status!r}:")
            for error in result.errors:
                emit.message(f"- {error.code}: {error.message}")
            retcode = 1
        return retcode


class ListRevisionsCommand(BaseCommand):
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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name of the charm or bundle")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        result = store.list_revisions(parsed_args.name)
        if not result:
            emit.message("No revisions found.")
            return

        headers = ["Revision", "Version", "Created at", "Status"]
        data = []
        for item in sorted(result, key=attrgetter("revision"), reverse=True):
            # use just the status or include error message/code in it (if exist)
            if item.errors:
                errors = ("{0.message} [{0.code}]".format(e) for e in item.errors)
                status = "{}: {}".format(item.status, "; ".join(errors))
            else:
                status = item.status

            data.append(
                [
                    item.revision,
                    item.version,
                    format_timestamp(item.created_at),
                    status,
                ]
            )

        table = tabulate(data, headers=headers, tablefmt="plain", numalign="left")
        for line in table.splitlines():
            emit.message(line)


class ReleaseCommand(BaseCommand):
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
            type=SingleOptionEnsurer(int),
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
            type=ResourceOption(),
            default=[],
            help=(
                "The resource(s) to attach to the release, in the <name>:<revision> format "
                "(this option can be indicated multiple times)"
            ),
        )

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        store.release(
            parsed_args.name,
            parsed_args.revision,
            parsed_args.channel,
            parsed_args.resource,
        )

        msg = "Revision {:d} of charm {!r} released to {}"
        args = [parsed_args.revision, parsed_args.name, ", ".join(parsed_args.channel)]
        if parsed_args.resource:
            msg += " (attaching resources: {})"
            args.append(", ".join(f"{r.name!r} r{r.revision}" for r in parsed_args.resource))
        emit.message(msg.format(*args))


class CloseCommand(BaseCommand):
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
        store = Store(self.config.charmhub)
        revision = None  # revision None will actually close the channel
        channels = [parsed_args.channel]  # the API accepts multiple channels, we have only one
        resources = []  # not really used when closing channels
        store.release(parsed_args.name, revision, channels, resources)
        emit.message(f"Closed {parsed_args.channel!r} channel for {parsed_args.name!r}.")


class StatusCommand(BaseCommand):
    """Show channel status for a charm or bundle."""

    name = "status"
    help_msg = "Show channel and released revisions"
    overview = textwrap.dedent(
        """
        Show channels and released revisions in Charmhub.

        Charm revisions are not available to users until they are released
        into a channel. This command shows the various channels for a charm
        and whether there is a charm released.

        For example:

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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("name", help="The name of the charm or bundle")

    def _build_resources_repr(self, resources):
        """Build a representation of a list of resources."""
        if resources:
            result = ", ".join("{} (r{})".format(r.name, r.revision) for r in resources)
        else:
            result = "-"
        return result

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        channel_map, channels, revisions = store.list_releases(parsed_args.name)
        if not channel_map:
            emit.message("Nothing has been released yet.")
            return

        # group released revision by track and base
        releases_by_track = {}
        for item in channel_map:
            track = item.channel.split("/")[0]
            by_base = releases_by_track.setdefault(track, {})
            if item.base is None:
                base_str = "-"
            else:
                base_str = "{0.name} {0.channel} ({0.architecture})".format(item.base)
            by_channel = by_base.setdefault(base_str, {})
            by_channel[item.channel] = item

        # groupe revision objects by revision number
        revisions_by_revno = {item.revision: item for item in revisions}

        # process and order the channels, while preserving the tracks order
        per_track = {}
        branch_present = False
        for channel in channels:
            nonbranches_list, branches_list = per_track.setdefault(channel.track, ([], []))
            if channel.branch is None:
                # insert branch right after its fallback
                for idx, stored in enumerate(nonbranches_list, 1):
                    if stored.name == channel.fallback:
                        nonbranches_list.insert(idx, channel)
                        break
                else:
                    nonbranches_list.append(channel)
            else:
                branches_list.append(channel)
                branch_present = True

        headers = ["Track", "Base", "Channel", "Version", "Revision"]
        resources_present = any(release.resources for release in channel_map)
        if resources_present:
            headers.append("Resources")
        if branch_present:
            headers.append("Expires at")

        # show everything, grouped by tracks and bases, with regular channels at first and
        # branches (if any) after those
        data = []
        unreleased_track = {"-": {}}  # show a dash in "base" and no releases at all
        for track, (channels, branches) in per_track.items():
            releases_by_base = releases_by_track.get(track, unreleased_track)
            shown_track = track

            # bases are shown alphabetically ordered
            for base in sorted(releases_by_base):
                releases_by_channel = releases_by_base[base]
                shown_base = base

                release_shown_for_this_track_base = False

                for channel in channels:
                    description = channel.risk

                    # get the release of the channel, fallbacking accordingly
                    release = releases_by_channel.get(channel.name)
                    if release is None:
                        version = revno = resources = (
                            "↑" if release_shown_for_this_track_base else "-"
                        )
                    else:
                        release_shown_for_this_track_base = True
                        revno = release.revision
                        revision = revisions_by_revno[revno]
                        version = revision.version
                        resources = self._build_resources_repr(release.resources)

                    datum = [shown_track, shown_base, description, version, revno]
                    if resources_present:
                        datum.append(resources)
                    data.append(datum)

                    # stop showing the track and base for the rest of the struct
                    shown_track = ""
                    shown_base = ""

                for branch in branches:
                    release = releases_by_channel.get(branch.name)
                    if release is None:
                        # not for this base!
                        continue
                    description = "/".join((branch.risk, branch.branch))
                    expiration = format_timestamp(release.expires_at)
                    revision = revisions_by_revno[release.revision]
                    datum = ["", "", description, revision.version, release.revision]
                    if resources_present:
                        datum.append(self._build_resources_repr(release.resources))
                    datum.append(expiration)
                    data.append(datum)

        table = tabulate(data, headers=headers, tablefmt="plain", numalign="left")
        for line in table.splitlines():
            emit.message(line)


class _BadLibraryPathError(CraftError):
    """Subclass to provide a specific error for a bad library path."""

    def __init__(self, path):
        super().__init__(
            "Charm library path {} must conform to lib/charms/<charm>/vN/<libname>.py"
            "".format(path)
        )


class _BadLibraryNameError(CraftError):
    """Subclass to provide a specific error for a bad library name."""

    def __init__(self, name):
        super().__init__(
            "Charm library name {!r} must conform to charms.<charm>.vN.<libname>".format(name)
        )


def _get_positive_int(raw_value):
    """Convert the raw value for api/patch into a positive integer."""
    value = int(raw_value)
    if value < 0:
        raise ValueError("negative")
    return value


def _get_lib_info(*, full_name=None, lib_path=None):
    """Get the whole lib info from the path/file.

    This will perform mutation of the charm name to create importable paths.
    * `charm_name` and `libdata.charm_name`: `foo-bar`
    * `full_name` and `libdata.full_name`: `charms.foo_bar.v0.somelib`
    * paths, including `libdata.path`: `lib/charms/foo_bar/v0/somelib`

    """
    if full_name is None:
        # get it from the lib_path
        try:
            libsdir, charmsdir, importable_charm_name, v_api = lib_path.parts[:-1]
        except ValueError:
            raise _BadLibraryPathError(lib_path)
        if libsdir != "lib" or charmsdir != "charms" or lib_path.suffix != ".py":
            raise _BadLibraryPathError(lib_path)
        full_name = ".".join((charmsdir, importable_charm_name, v_api, lib_path.stem))

    else:
        # build the path! convert a lib name with dots to the full path, including lib
        # dir and Python extension.
        #    e.g.: charms.mycharm.v4.foo -> lib/charms/mycharm/v4/foo.py
        try:
            charmsdir, charm_name, v_api, libfile = full_name.split(".")
        except ValueError:
            raise _BadLibraryNameError(full_name)

        # the lib full_name includes the charm_name which might not be importable (dashes)
        importable_charm_name = create_importable_name(charm_name)

        if charmsdir != "charms":
            raise _BadLibraryNameError(full_name)
        path = pathlib.Path("lib")
        lib_path = path / charmsdir / importable_charm_name / v_api / (libfile + ".py")

    # charm names in the path can contain '_' to be importable
    # these should be '-', so change them back
    charm_name = create_charm_name_from_importable(importable_charm_name)

    if v_api[0] != "v" or not v_api[1:].isdigit():
        raise CraftError("The API version in the library path must be 'vN' where N is an integer.")
    api_from_path = int(v_api[1:])

    lib_name = lib_path.stem
    if not lib_path.exists():
        return LibData(
            lib_id=None,
            api=api_from_path,
            patch=-1,
            content_hash=None,
            content=None,
            full_name=full_name,
            path=lib_path,
            lib_name=lib_name,
            charm_name=charm_name,
        )

    # parse the file and extract metadata from it, while hashing
    metadata_fields = (b"LIBAPI", b"LIBPATCH", b"LIBID")
    metadata = dict.fromkeys(metadata_fields)
    hasher = hashlib.sha256()
    with lib_path.open("rb") as fh:
        for line in fh:
            if line.startswith(metadata_fields):
                try:
                    field, value = [x.strip() for x in line.split(b"=")]
                except ValueError:
                    raise CraftError("Bad metadata line in {!r}: {!r}".format(str(lib_path), line))
                metadata[field] = value
            else:
                hasher.update(line)

    missing = [k.decode("ascii") for k, v in metadata.items() if v is None]
    if missing:
        raise CraftError(
            "Library {!r} is missing the mandatory metadata fields: {}.".format(
                str(lib_path), ", ".join(sorted(missing))
            )
        )

    bad_api_patch_msg = "Library {!r} metadata field {} is not zero or a positive integer."
    try:
        libapi = _get_positive_int(metadata[b"LIBAPI"])
    except ValueError:
        raise CraftError(bad_api_patch_msg.format(str(lib_path), "LIBAPI"))
    try:
        libpatch = _get_positive_int(metadata[b"LIBPATCH"])
    except ValueError:
        raise CraftError(bad_api_patch_msg.format(str(lib_path), "LIBPATCH"))

    if libapi == 0 and libpatch == 0:
        raise CraftError(
            "Library {!r} metadata fields LIBAPI and LIBPATCH cannot both be zero.".format(
                str(lib_path)
            )
        )

    if libapi != api_from_path:
        raise CraftError(
            "Library {!r} metadata field LIBAPI is different from the version in the path.".format(
                str(lib_path)
            )
        )

    bad_libid_msg = "Library {!r} metadata field LIBID must be a non-empty ASCII string."
    try:
        libid = ast.literal_eval(metadata[b"LIBID"].decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        raise CraftError(bad_libid_msg.format(str(lib_path)))
    if not libid or not isinstance(libid, str):
        raise CraftError(bad_libid_msg.format(str(lib_path)))

    content_hash = hasher.hexdigest()
    content = lib_path.read_text()

    return LibData(
        lib_id=libid,
        api=libapi,
        patch=libpatch,
        content_hash=content_hash,
        content=content,
        full_name=full_name,
        path=lib_path,
        lib_name=lib_name,
        charm_name=charm_name,
    )


def _get_libs_from_tree(charm_name=None):
    """Get library info from the directories tree (for a specific charm if specified).

    It only follows/uses the the directories/files for a correct charmlibs
    disk structure.

    This can take charm_name as both importable and normal form.
    """
    local_libs_data = []

    if charm_name is None:
        base_dir = pathlib.Path("lib") / "charms"
        charm_dirs = sorted(base_dir.iterdir()) if base_dir.is_dir() else []
    else:
        importable_charm_name = create_importable_name(charm_name)
        base_dir = pathlib.Path("lib") / "charms" / importable_charm_name
        charm_dirs = [base_dir] if base_dir.is_dir() else []

    for charm_dir in charm_dirs:
        for v_dir in sorted(charm_dir.iterdir()):
            if v_dir.is_dir() and v_dir.name[0] == "v" and v_dir.name[1:].isdigit():
                for libfile in sorted(v_dir.glob("*.py")):
                    local_libs_data.append(_get_lib_info(lib_path=libfile))

    found_libs = [lib_data.full_name for lib_data in local_libs_data]
    emit.trace(f"Libraries found under {str(base_dir)!r}: {found_libs}")
    return local_libs_data


class CreateLibCommand(BaseCommand):
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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
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

        charm_name = get_name_from_metadata()
        if charm_name is None:
            raise CraftError(
                "Cannot find a valid charm name in metadata.yaml. Check you are in a charm "
                "directory with metadata.yaml."
            )

        # '-' is valid in charm names, but not in a python import
        # mutate the name so the path is a valid import
        importable_charm_name = create_importable_name(charm_name)

        # all libraries born with API version 0
        full_name = "charms.{}.v0.{}".format(importable_charm_name, lib_name)
        lib_data = _get_lib_info(full_name=full_name)
        lib_path = lib_data.path
        if lib_path.exists():
            raise CraftError("This library already exists: {!r}.".format(str(lib_path)))

        emit.progress(f"Creating library {lib_name}.")
        store = Store(self.config.charmhub)
        lib_id = store.create_library_id(charm_name, lib_name)

        # create the new library file from the template
        env = get_templates_environment("charmlibs")
        template = env.get_template("new_library.py.j2")
        context = dict(lib_id=lib_id)
        try:
            lib_path.parent.mkdir(parents=True, exist_ok=True)
            lib_path.write_text(template.render(context))
        except OSError as exc:
            raise CraftError("Error writing the library in {!r}: {!r}.".format(str(lib_path), exc))

        emit.message(f"Library {full_name} created with id {lib_id}.")
        emit.message(f"Consider 'git add {lib_path}'.")


class PublishLibCommand(BaseCommand):
    """Publish one or more charm libraries."""

    name = "publish-lib"
    help_msg = "Publish one or more charm libraries"
    overview = textwrap.dedent(
        """
        Publish charm libraries.

        Upload and release in Charmhub the new api/patch version of the
        indicated library, or all the charm libraries if --all is used.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """
    )

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            "library",
            nargs="?",
            help="Library to publish (e.g. charms.mycharm.v2.foo.); optional, default to all",
        )

    def run(self, parsed_args):
        """Run the command."""
        charm_name = get_name_from_metadata()
        if charm_name is None:
            raise CraftError(
                "Can't access name in 'metadata.yaml' file. The 'publish-lib' command needs to "
                "be executed in a valid project's directory."
            )

        if parsed_args.library:
            lib_data = _get_lib_info(full_name=parsed_args.library)
            if not lib_data.path.exists():
                raise CraftError(
                    "The specified library was not found at path {!r}.".format(str(lib_data.path))
                )
            if lib_data.charm_name != charm_name:
                raise CraftError(
                    "The library {} does not belong to this charm {!r}.".format(
                        lib_data.full_name, charm_name
                    )
                )
            local_libs_data = [lib_data]
        else:
            local_libs_data = _get_libs_from_tree(charm_name)

        # check if something needs to be done
        store = Store(self.config.charmhub)
        to_query = [dict(lib_id=lib.lib_id, api=lib.api) for lib in local_libs_data]
        libs_tips = store.get_libraries_tips(to_query)
        to_publish = []
        for lib_data in local_libs_data:
            emit.trace(f"Verifying local lib {lib_data}")
            tip = libs_tips.get((lib_data.lib_id, lib_data.api))
            emit.trace(f"Store tip: {tip}")
            if tip is None:
                # needs to first publish
                to_publish.append(lib_data)
                continue

            if tip.patch > lib_data.patch:
                # the store is more advanced than local
                emit.message(
                    f"Library {lib_data.full_name} is out-of-date locally, Charmhub has "
                    f"version {tip.api:d}.{tip.patch:d}, please "
                    "fetch the updates before publishing.",
                )
            elif tip.patch == lib_data.patch:
                # the store has same version numbers than local
                if tip.content_hash == lib_data.content_hash:
                    emit.message(f"Library {lib_data.full_name} is already updated in Charmhub.")
                else:
                    # but shouldn't as hash is different!
                    emit.message(
                        f"Library {lib_data.full_name} version {tip.api:d}.{tip.patch:d} "
                        "is the same than in Charmhub but content is different",
                    )
            elif tip.patch + 1 == lib_data.patch:
                # local is correctly incremented
                if tip.content_hash == lib_data.content_hash:
                    # but shouldn't as hash is the same!
                    emit.message(
                        f"Library {lib_data.full_name} LIBPATCH number was incorrectly "
                        "incremented, Charmhub has the "
                        f"same content in version {tip.api:d}.{tip.patch:d}.",
                    )
                else:
                    to_publish.append(lib_data)
            else:
                emit.message(
                    f"Library {lib_data.full_name} has a wrong LIBPATCH number, it's too high, "
                    f"Charmhub highest version is {tip.api:d}.{tip.patch:d}.",
                )

        for lib_data in to_publish:
            store.create_library_revision(
                lib_data.charm_name,
                lib_data.lib_id,
                lib_data.api,
                lib_data.patch,
                lib_data.content,
                lib_data.content_hash,
            )
            emit.message(
                f"Library {lib_data.full_name} sent to the store with "
                f"version {lib_data.api:d}.{lib_data.patch:d}",
            )


class FetchLibCommand(BaseCommand):
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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            "library",
            nargs="?",
            help="Library to fetch (e.g. charms.mycharm.v2.foo.); optional, default to all",
        )

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.library:
            local_libs_data = [_get_lib_info(full_name=parsed_args.library)]
        else:
            local_libs_data = _get_libs_from_tree()

        # get tips from the Store
        store = Store(self.config.charmhub)
        to_query = []
        for lib in local_libs_data:
            if lib.lib_id is None:
                item = dict(charm_name=lib.charm_name, lib_name=lib.lib_name)
            else:
                item = dict(lib_id=lib.lib_id)
            item["api"] = lib.api
            to_query.append(item)
        libs_tips = store.get_libraries_tips(to_query)

        # check if something needs to be done
        to_fetch = []
        for lib_data in local_libs_data:
            emit.trace(f"Verifying local lib {lib_data}")
            # fix any missing lib id using the Store info
            if lib_data.lib_id is None:
                for tip in libs_tips.values():
                    if lib_data.charm_name == tip.charm_name and lib_data.lib_name == tip.lib_name:
                        lib_data = lib_data._replace(lib_id=tip.lib_id)
                        break

            tip = libs_tips.get((lib_data.lib_id, lib_data.api))
            emit.trace(f"Store tip: {tip}")
            if tip is None:
                emit.message(f"Library {lib_data.full_name} not found in Charmhub.")
                continue

            if tip.patch > lib_data.patch:
                # the store has a higher version than local
                to_fetch.append(lib_data)
            elif tip.patch < lib_data.patch:
                # the store has a lower version numbers than local
                emit.message(
                    f"Library {lib_data.full_name} has local changes, cannot be updated.",
                )
            else:
                # same versions locally and in the store
                if tip.content_hash == lib_data.content_hash:
                    emit.message(
                        f"Library {lib_data.full_name} was already up to date in "
                        f"version {tip.api:d}.{tip.patch:d}.",
                    )
                else:
                    emit.message(
                        f"Library {lib_data.full_name} has local changes, cannot be updated.",
                    )

        for lib_data in to_fetch:
            downloaded = store.get_library(lib_data.charm_name, lib_data.lib_id, lib_data.api)
            if lib_data.content is None:
                # locally new
                lib_data.path.parent.mkdir(parents=True, exist_ok=True)
                lib_data.path.write_text(downloaded.content)
                emit.message(
                    f"Library {lib_data.full_name} version "
                    f"{downloaded.api:d}.{downloaded.patch:d} downloaded.",
                )
            else:
                # XXX Facundo 2020-12-17: manage the case where the library was renamed
                # (related GH issue: #214)
                lib_data.path.write_text(downloaded.content)
                emit.message(
                    f"Library {lib_data.full_name} updated to version "
                    f"{downloaded.api:d}.{downloaded.patch:d}.",
                )


class ListLibCommand(BaseCommand):
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

        To fetch one of the shown libraries you can use the fetch-lib command.
    """
    )

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
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
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CraftError(
                    "Can't access name in 'metadata.yaml' file. The 'list-lib' command must "
                    "either be executed from a valid project directory, or specify a charm "
                    "name using the --charm-name option."
                )

        # get tips from the Store
        store = Store(self.config.charmhub)
        to_query = [{"charm_name": charm_name}]
        libs_tips = store.get_libraries_tips(to_query)

        if not libs_tips:
            emit.message(f"No libraries found for charm {charm_name}.")
            return

        headers = ["Library name", "API", "Patch"]
        data = sorted((item.lib_name, item.api, item.patch) for item in libs_tips.values())

        table = tabulate(data, headers=headers, tablefmt="plain", numalign="left")
        for line in table.splitlines():
            emit.message(line)


class ListResourcesCommand(BaseCommand):
    """List the resources associated with a given charm in Charmhub."""

    name = "resources"
    help_msg = "List the resources associated with a given charm in Charmhub"
    overview = textwrap.dedent(
        """
        An overview of the resources associated with a given charm in Charmhub.

        Listing resources will take you through login if needed.

    """
    )

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument("charm_name", metavar="charm-name", help="The name of the charm")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        result = store.list_resources(parsed_args.charm_name)
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


class UploadResourceCommand(BaseCommand):
    """Upload a resource to Charmhub."""

    name = "upload-resource"
    help_msg = "Upload a resource to Charmhub"
    overview = textwrap.dedent(
        """
        Upload a resource to Charmhub.

        Push a resource content to Charmhub, associating it to the
        specified charm. This charm needs to have the resource declared
        in its metadata (in a previously uploaded to Charmhub revision).

        The resource can be a file from your computer (use the '--filepath'
        option) or an OCI Image (use the '--image' option to indicate the
        image digest), which can be already in Canonical's registry and
        used directly, or locally in your computer and will be uploaded
        and used.

        Upload will take you through login if needed.
    """
    )
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            "charm_name",
            metavar="charm-name",
            help="The charm name to associate the resource",
        )
        parser.add_argument("resource_name", metavar="resource-name", help="The resource name")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--filepath",
            type=SingleOptionEnsurer(useful_filepath),
            help="The file path of the resource content to upload",
        )
        group.add_argument(
            "--image",
            type=SingleOptionEnsurer(str),
            help="The digest of the OCI image",
        )

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)

        if parsed_args.filepath:
            resource_filepath = parsed_args.filepath
            resource_filepath_is_temp = False
            resource_type = ResourceType.file
            emit.progress(f"Uploading resource directly from file {str(resource_filepath)!r}.")
        elif parsed_args.image:
            image_digest = parsed_args.image
            credentials = store.get_oci_registry_credentials(
                parsed_args.charm_name, parsed_args.resource_name
            )

            # convert the standard OCI registry image name (which is something like
            # 'registry.jujucharms.com/charm/45kk8smbiyn2e/redis-image') to the image
            # name that we use internally (just remove the initial "server host" part)
            image_name = credentials.image_name.split("/", 1)[1]
            emit.progress(f"Uploading resource from image {image_name} @ {image_digest}.")

            # build the image handler
            registry = OCIRegistry(
                self.config.charmhub.registry_url,
                image_name,
                username=credentials.username,
                password=credentials.password,
            )
            ih = ImageHandler(registry)

            # check if the specific image is already in Canonical's registry
            already_uploaded = ih.check_in_registry(image_digest)
            if already_uploaded:
                emit.message("Using OCI image from Canonical's registry.", intermediate=True)
            else:
                # upload it from local registry
                emit.message(
                    "Remote image not found, uploading from local registry.", intermediate=True
                )
                image_digest = ih.upload_from_local(image_digest)
                if image_digest is None:
                    emit.message(
                        f"Image with digest {parsed_args.image} is not available in "
                        "the Canonical's registry nor locally.",
                        intermediate=True,
                    )
                    return
                emit.message(
                    f"Image uploaded, new remote digest: {image_digest}.", intermediate=True
                )

            # all is green, get the blob to upload to Charmhub
            content = store.get_oci_image_blob(
                parsed_args.charm_name, parsed_args.resource_name, image_digest
            )
            tfd, tname = tempfile.mkstemp(prefix="image-resource", suffix=".json")
            with open(tfd, "wt", encoding="utf-8") as fh:  # reuse the file descriptor and close it
                fh.write(content)
            resource_filepath = pathlib.Path(tname)
            resource_filepath_is_temp = True
            resource_type = ResourceType.oci_image

        result = store.upload_resource(
            parsed_args.charm_name,
            parsed_args.resource_name,
            resource_type,
            resource_filepath,
        )

        # clean the filepath if needed
        if resource_filepath_is_temp:
            resource_filepath.unlink()

        if result.ok:
            emit.message(
                f"Revision {result.revision} created of "
                f"resource {parsed_args.resource_name!r} for charm {parsed_args.charm_name!r}.",
            )
            retcode = 0
        else:
            emit.message(f"Upload failed with status {result.status!r}:")
            for error in result.errors:
                emit.message(f"- {error.code}: {error.message}")
            retcode = 1
        return retcode


class ListResourceRevisionsCommand(BaseCommand):
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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            "charm_name",
            metavar="charm-name",
            help="The charm name to associate the resource",
        )
        parser.add_argument("resource_name", metavar="resource-name", help="The resource name")

    def run(self, parsed_args):
        """Run the command."""
        store = Store(self.config.charmhub)
        result = store.list_resource_revisions(parsed_args.charm_name, parsed_args.resource_name)
        if not result:
            emit.message("No revisions found.")
            return

        headers = ["Revision", "Created at", "Size"]
        custom_alignment = ["left", "left", "right"]
        result.sort(key=attrgetter("revision"), reverse=True)
        data = [
            (
                item.revision,
                format_timestamp(item.created_at),
                naturalsize(item.size, gnu=True),
            )
            for item in result
        ]

        table = tabulate(data, headers=headers, tablefmt="plain", colalign=custom_alignment)
        for line in table.splitlines():
            emit.message(line)
