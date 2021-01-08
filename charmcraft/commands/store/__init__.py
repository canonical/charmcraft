# Copyright 2020 Canonical Ltd.
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
import logging
import os
import pathlib
import string
import textwrap
from collections import namedtuple
from operator import attrgetter

import yaml
from tabulate import tabulate

from charmcraft.cmdbase import BaseCommand, CommandError
from charmcraft.commands.utils import get_templates_environment

from .store import Store

logger = logging.getLogger('charmcraft.commands.store')

LibData = namedtuple(
    'LibData', 'lib_id api patch content content_hash full_name path lib_name charm_name')


def get_name_from_metadata():
    """Return the name if present and plausible in metadata.yaml."""
    try:
        with open('metadata.yaml', 'rb') as fh:
            metadata = yaml.safe_load(fh)
        charm_name = metadata['name']
    except (yaml.error.YAMLError, OSError, KeyError):
        return
    return charm_name


class LoginCommand(BaseCommand):
    """Login to Charmhub."""
    name = 'login'
    help_msg = "Login to Charmhub"
    overview = textwrap.dedent("""
        Login to Charmhub.

        Charmcraft will provide a URL for the Charmhub login. When you have
        successfully logged in, charmcraft will store a token for ongoing
        access to Charmhub at the CLI.

        Remember to `charmcraft logout` if you want to remove that token
        from your local system, especially in a shared environment.

        See also `charmcraft whoami` to verify that you are logged in.

    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.login()
        logger.info("Logged in as '%s'.", store.whoami().username)


class LogoutCommand(BaseCommand):
    """Clear Charmhub token."""
    name = 'logout'
    help_msg = "Logout from Charmhub and remove token"
    overview = textwrap.dedent("""
        Clear the Charmhub token.

        Charmcraft will remove the local token used for Charmhub access.
        This is important on any shared system because the token allows
        manipulation of your published charms.

        See also `charmcraft whoami` to verify that you are logged in,
        and `charmcraft login`.

    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.logout()
        logger.info("Charmhub token cleared.")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "Show your Charmhub login status"
    overview = textwrap.dedent("""
        Show your Charmhub login status.

        See also `charmcraft login` and `charmcraft logout`.
    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.whoami()

        data = [
            ('name:', result.name),
            ('username:', result.username),
            ('id:', result.userid),
        ]
        table = tabulate(data, tablefmt='plain')
        for line in table.splitlines():
            logger.info(line)


class RegisterNameCommand(BaseCommand):
    """Register a name in Charmhub."""
    name = 'register'
    help_msg = "Register a charm name in Charmhub"
    overview = textwrap.dedent("""
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

        We discuss registrations in Charmhub Discourse:

           https://discourse.charmhub.io/c/charm

        Registration will take you through login if needed.

    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('name', help="The name to register in Charmhub")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.register_name(parsed_args.name)
        logger.info("You are now the publisher of %r in Charmhub.", parsed_args.name)


class ListNamesCommand(BaseCommand):
    """List the charms registered in Charmhub"""
    name = 'names'
    help_msg = "List your registered charm names in Charmhub"
    overview = textwrap.dedent("""
        An overview of names you have registered to publish in Charmhub.

          $ charmcraft names
          Name                Visibility    Status
          sabdfl-hello-world  public        registered

        Visibility and status are shown for each name. `public` items can be
        seen by any user, while `private` items are only for you and the
        other accounts with permission to collaborate on that specific name.

        Listing names will take you through login if needed.

    """)
    common = True

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.list_registered_names()
        if not result:
            logger.info("No charms registered.")
            return

        headers = ['Name', 'Visibility', 'Status']
        data = []
        for item in result:
            visibility = 'private' if item.private else 'public'
            data.append([
                item.name,
                visibility,
                item.status,
            ])

        table = tabulate(data, headers=headers, tablefmt='plain')
        for line in table.splitlines():
            logger.info(line)


class UploadCommand(BaseCommand):
    """Upload a charm to Charmhub."""
    name = 'upload'
    help_msg = "Upload a charm to Charmhub"
    overview = textwrap.dedent("""
        Upload a charm to Charmhub.

        Push a charm to Charmhub where it will be verified for conformance
        to the packaging standard. This command will finish successfully
        once the package is approved by Charmhub.

        In the event of a failure in the verification process, charmcraft
        will report details of the failure, otherwise it will give you the
        new charm revision.

        Upload will take you through login if needed.

    """)
    common = True

    def _discover_charm(self, charm_filepath):
        """Discover the charm name and file path.

        If received path is None, a metadata.yaml will be searched in the current directory. If
        path is given the name is taken from the filename.

        """
        if charm_filepath is None:
            # discover the info using project's metadata, asume the file has the project's name
            # with a .charm extension
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Cannot find a valid charm name in metadata.yaml to upload. Check you are in "
                    "a charm directory with metadata.yaml, or use --charm-file=foo.charm.")

            charm_filepath = pathlib.Path(charm_name + '.charm').absolute()
            if not os.access(str(charm_filepath), os.R_OK):  # access doesnt support pathlib in 3.5
                raise CommandError(
                    "Cannot access charm at {!r}. Try --charm-file=foo.charm"
                    .format(str(charm_filepath)))

        else:
            # the path is given, asume the charm name is part of the file name
            # XXX Facundo 2020-06-30: Actually, we need to open the ZIP file, extract the
            # included metadata.yaml file, and read the name from there. Issue: #77.
            charm_filepath = charm_filepath.expanduser()
            if not os.access(str(charm_filepath), os.R_OK):  # access doesnt support pathlib in 3.5
                raise CommandError(
                    "Cannot access {!r}.".format(str(charm_filepath)))
            if not charm_filepath.is_file():
                raise CommandError(
                    "{!r} is not a file.".format(str(charm_filepath)))

            charm_name = charm_filepath.stem

        return charm_name, charm_filepath

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            '--charm-file', type=pathlib.Path,
            help="The charm to upload")

    def run(self, parsed_args):
        """Run the command."""
        name, path = self._discover_charm(parsed_args.charm_file)
        store = Store()
        result = store.upload(name, path)
        if result.ok:
            logger.info("Revision %s of %r created", result.revision, str(name))
        else:
            # XXX Facundo 2020-06-30: at some point in the future the Store will give us also a
            # reason why it failed, to improve the message. Issue: #78.
            logger.info("Upload failed with status %r.", result.status)


class ListRevisionsCommand(BaseCommand):
    """List revisions for a charm."""
    name = 'revisions'
    help_msg = "List revisions for a charm in Charmhub"
    overview = textwrap.dedent("""
        Show version, date and status for each revision in Charmhub.

        For example:

           $ charmcraft revisions
           Revision    Version    Created at    Status
           1           1          2020-11-15    released

        Listing revisions will take you through login if needed.

    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="The name of the charm")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Cannot find a valid charm name in metadata.yaml. Check you are in a charm "
                    "directory with metadata.yaml, or use --name=foo.")

        store = Store()
        result = store.list_revisions(charm_name)
        if not result:
            logger.info("No revisions found.")
            return

        headers = ['Revision', 'Version', 'Created at', 'Status']
        data = []
        for item in sorted(result, key=attrgetter('revision'), reverse=True):
            # use just the status or include error message/code in it (if exist)
            if item.errors:
                errors = ("{0.message} [{0.code}]".format(e) for e in item.errors)
                status = "{}: {}".format(item.status, '; '.join(errors))
            else:
                status = item.status

            data.append([
                item.revision,
                item.version,
                item.created_at.strftime('%Y-%m-%d'),
                status,
            ])

        table = tabulate(data, headers=headers, tablefmt='plain', numalign='left')
        for line in table.splitlines():
            logger.info(line)


class ReleaseCommand(BaseCommand):
    """Release a charm revision to specific channels."""
    name = 'release'
    help_msg = "Release a charm revision in one or more channels"
    overview = textwrap.dedent("""
        Release a charm revision in the channel(s) provided.

        Charm revisions are not published for anybody else until you release
        them in a channel. When you release a revision into a channel, users
        who deploy the charm from that channel will get see the new revision
        as a potential update.

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

        Listing revisions will take you through login if needed.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'revision', type=int, help='The revision to release')
        parser.add_argument(
            'channels', metavar='channel', nargs='+',
            help="The channel(s) to release to")
        parser.add_argument('--name', help="The name of the charm")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()

        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Cannot find a valid charm name in metadata.yaml. Check you are in a charm "
                    "directory with metadata.yaml, or use --name=foo.")

        store.release(charm_name, parsed_args.revision, parsed_args.channels)
        logger.info(
            "Revision %d of charm %r released to %s",
            parsed_args.revision, charm_name, ", ".join(parsed_args.channels))


class StatusCommand(BaseCommand):
    """Show channel status for a charm."""
    name = 'channels'
    help_msg = "Show channel and released revisions"
    overview = textwrap.dedent("""
        Show channels and released revisions in Charmhub

        Charm revisions are not available to users until they are released
        into a channel. This command shows the various channels for a charm
        and whether there is a charm released.

        For example:

          $ charmcraft status
          Track    Channel    Version    Revision
          latest   stable     -          -
                   candidate  -          -
                   beta       -          -
                   edge       1          1

        Showing channels will take you through login if needed.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="The name of the charm")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Cannot find a valid charm name in metadata.yaml. Check you are in a charm "
                    "directory with metadata.yaml, or use --name=foo.")

        store = Store()
        channel_map, channels, revisions = store.list_releases(charm_name)
        if not channel_map:
            logger.info("Nothing has been released yet.")
            return

        # build easier to access structures
        releases_by_channel = {item.channel: item for item in channel_map}
        revisions_by_revno = {item.revision: item for item in revisions}

        # process and order the channels, while preserving the tracks order
        all_tracks = []
        per_track = {}
        branch_present = False
        for channel in channels:
            # it's super rare to have a more than just a bunch of tracks (furthermore, normally
            # there's only one), so it's ok to do this sequential search
            if channel.track not in all_tracks:
                all_tracks.append(channel.track)

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

        headers = ['Track', 'Channel', 'Version', 'Revision']
        if branch_present:
            headers.append('Expires at')

        # show everything, grouped by tracks, with regular channels at first and
        # branches (if any) after those
        data = []
        for track in all_tracks:
            release_shown_for_this_track = False
            shown_track = track
            channels, branches = per_track[track]

            for channel in channels:
                description = channel.risk

                # get the release of the channel, fallbacking accordingly
                release = releases_by_channel.get(channel.name)
                if release is None:
                    version = revno = '↑' if release_shown_for_this_track else '-'
                else:
                    release_shown_for_this_track = True
                    revno = release.revision
                    revision = revisions_by_revno[revno]
                    version = revision.version

                data.append([shown_track, description, version, revno])

                # stop showing the track name for the rest of the track
                shown_track = ''

            for branch in branches:
                description = '/'.join((branch.risk, branch.branch))
                release = releases_by_channel[branch.name]
                expiration = release.expires_at.isoformat()
                revision = revisions_by_revno[release.revision]
                data.append(['', description, revision.version, release.revision, expiration])

        table = tabulate(data, headers=headers, tablefmt='plain', numalign='left')
        for line in table.splitlines():
            logger.info(line)


class _BadLibraryPathError(CommandError):
    """Subclass to provide a specific error for a bad library path."""
    def __init__(self, path):
        super().__init__(
            "Charm library path {} must conform to lib/charms/<charm>/vN/<libname>.py"
            "".format(path))


class _BadLibraryNameError(CommandError):
    """Subclass to provide a specific error for a bad library name."""
    def __init__(self, name):
        super().__init__(
            "Charm library name {!r} must conform to charms.<charm>.vN.<libname>"
            .format(name))


def _get_positive_int(raw_value):
    """Convert the raw value for api/patch into a positive integer."""
    value = int(raw_value)
    if value < 0:
        raise ValueError('negative')
    return value


def _get_lib_info(*, full_name=None, lib_path=None):
    """Get the whole lib info from the path/file."""
    if full_name is None:
        # get it from the lib_path
        try:
            libsdir, charmsdir, charm_name, v_api = lib_path.parts[:-1]
        except ValueError:
            raise _BadLibraryPathError(lib_path)
        if libsdir != 'lib' or charmsdir != 'charms' or lib_path.suffix != '.py':
            raise _BadLibraryPathError(lib_path)
        full_name = '.'.join((charmsdir, charm_name, v_api, lib_path.stem))

    else:
        # build the path! convert a lib name with dots to the full path, including lib
        # dir and Python extension.
        #    e.g.: charms.mycharm.v4.foo -> lib/charms/mycharm/v4/foo.py
        try:
            charmsdir, charm_name, v_api, libfile = full_name.split('.')
        except ValueError:
            raise _BadLibraryNameError(full_name)
        if charmsdir != 'charms':
            raise _BadLibraryNameError(full_name)
        lib_path = pathlib.Path('lib') / charmsdir / charm_name / v_api / (libfile + '.py')

    if v_api[0] != 'v' or not v_api[1:].isdigit():
        raise CommandError(
            "The API version in the library path must be 'vN' where N is an integer.")
    api_from_path = int(v_api[1:])

    lib_name = lib_path.stem
    if not lib_path.exists():
        return LibData(
            lib_id=None, api=api_from_path, patch=-1, content_hash=None, content=None,
            full_name=full_name, path=lib_path, lib_name=lib_name, charm_name=charm_name)

    # parse the file and extract metadata from it, while hashing
    metadata_fields = (b'LIBAPI', b'LIBPATCH', b'LIBID')
    metadata = dict.fromkeys(metadata_fields)
    hasher = hashlib.sha256()
    with lib_path.open('rb') as fh:
        for line in fh:
            if line.startswith(metadata_fields):
                try:
                    field, value = [x.strip() for x in line.split(b'=')]
                except ValueError:
                    raise CommandError("Bad metadata line in {}: {!r}".format(lib_path, line))
                metadata[field] = value
            else:
                hasher.update(line)

    missing = [k.decode('ascii') for k, v in metadata.items() if v is None]
    if missing:
        raise CommandError(
            "Library {} is missing the mandatory metadata fields: {}."
            .format(lib_path, ', '.join(sorted(missing))))

    bad_api_patch_msg = "Library {} metadata field {} is not zero or a positive integer."
    try:
        libapi = _get_positive_int(metadata[b'LIBAPI'])
    except ValueError:
        raise CommandError(bad_api_patch_msg.format(lib_path, 'LIBAPI'))
    try:
        libpatch = _get_positive_int(metadata[b'LIBPATCH'])
    except ValueError:
        raise CommandError(bad_api_patch_msg.format(lib_path, 'LIBPATCH'))

    if libapi == 0 and libpatch == 0:
        raise CommandError(
            "Library {} metadata fields LIBAPI and LIBPATCH cannot both be zero."
            .format(lib_path))

    if libapi != api_from_path:
        raise CommandError(
            "Library {} metadata field LIBAPI is different from the version in the path."
            .format(lib_path))

    bad_libid_msg = "Library {} metadata field LIBID must be a non-empty ASCII string."
    try:
        libid = ast.literal_eval(metadata[b'LIBID'].decode('ascii'))
    except (ValueError, UnicodeDecodeError):
        raise CommandError(bad_libid_msg.format(lib_path))
    if not libid or not isinstance(libid, str):
        raise CommandError(bad_libid_msg.format(lib_path))

    content_hash = hasher.hexdigest()
    content = lib_path.read_text()

    return LibData(
        lib_id=libid, api=libapi, patch=libpatch, content_hash=content_hash, content=content,
        full_name=full_name, path=lib_path, lib_name=lib_name, charm_name=charm_name)


def _get_libs_from_tree(charm_name=None):
    """Get library info from the directories tree (for a specific charm if specified).

    It only follows/uses the the directories/files for a correct charmlibs
    disk structure.
    """
    local_libs_data = []

    if charm_name is None:
        base_dir = pathlib.Path('lib') / 'charms'
        charm_dirs = sorted(base_dir.iterdir()) if base_dir.is_dir() else []
    else:
        base_dir = pathlib.Path('lib') / 'charms' / charm_name
        charm_dirs = [base_dir] if base_dir.is_dir() else []

    for charm_dir in charm_dirs:
        for v_dir in sorted(charm_dir.iterdir()):
            if v_dir.is_dir() and v_dir.name[0] == 'v' and v_dir.name[1:].isdigit():
                for libfile in sorted(v_dir.glob('*.py')):
                    local_libs_data.append(_get_lib_info(lib_path=libfile))

    found_libs = [lib_data.full_name for lib_data in local_libs_data]
    logger.debug("Libraries found under %s: %s", base_dir, found_libs)
    return local_libs_data


class CreateLibCommand(BaseCommand):
    """Create a charm library."""
    name = 'create-lib'
    help_msg = "Create a charm library"
    overview = textwrap.dedent("""
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

    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'name', metavar='name',
            help="The name of the library file (e.g. 'db')")

    def run(self, parsed_args):
        """Run the command."""
        lib_name = parsed_args.name
        valid_all_chars = set(string.ascii_lowercase + string.digits + '_')
        valid_first_char = string.ascii_lowercase
        if set(lib_name) - valid_all_chars or not lib_name or lib_name[0] not in valid_first_char:
            raise CommandError(
                "Invalid library name. Must only use lowercase alphanumeric "
                "characters and underscore, starting with alpha.")

        charm_name = get_name_from_metadata()
        if charm_name is None:
            raise CommandError(
                "Cannot find a valid charm name in metadata.yaml. Check you are in a charm "
                "directory with metadata.yaml.")

        # all libraries born with API version 0
        full_name = 'charms.{}.v0.{}'.format(charm_name, lib_name)
        lib_data = _get_lib_info(full_name=full_name)
        lib_path = lib_data.path
        if lib_path.exists():
            raise CommandError('This library already exists: {}'.format(lib_path))

        store = Store()
        lib_id = store.create_library_id(charm_name, lib_name)

        # create the new library file from the template
        env = get_templates_environment('charmlibs')
        template = env.get_template('new_library.py.j2')
        context = dict(lib_id=lib_id)
        try:
            lib_path.parent.mkdir(parents=True, exist_ok=True)
            lib_path.write_text(template.render(context))
        except OSError as exc:
            raise CommandError(
                "Error writing the library in {}: {!r}.".format(lib_path, exc))

        logger.info("Library %s created with id %s.", full_name, lib_id)
        logger.info("Consider 'git add %s'.", lib_path)


class PublishLibCommand(BaseCommand):
    """Publish one or more charm libraries."""
    name = 'publish-lib'
    help_msg = "Publish one or more charm libraries"
    overview = textwrap.dedent("""
        Publish charm libraries.

        Upload and release in Charmhub the new api/patch version of the
        indicated library, or all the charm libraries if --all is used.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'library', nargs='?',
            help="Library to publish (e.g. charms.mycharm.v2.foo.); optional, default to all")

    def run(self, parsed_args):
        """Run the command."""
        charm_name = get_name_from_metadata()
        if charm_name is None:
            raise CommandError(
                "Can't access name in 'metadata.yaml' file. The 'publish-lib' command needs to "
                "be executed in a valid project's directory.")

        if parsed_args.library:
            lib_data = _get_lib_info(full_name=parsed_args.library)
            if not lib_data.path.exists():
                raise CommandError(
                    "The specified library was not found at path {}.".format(lib_data.path))
            if lib_data.charm_name != charm_name:
                raise CommandError(
                    "The library {} does not belong to this charm {!r}.".format(
                        lib_data.full_name, charm_name))
            local_libs_data = [lib_data]
        else:
            local_libs_data = _get_libs_from_tree(charm_name)

        # check if something needs to be done
        store = Store()
        to_query = [dict(lib_id=lib.lib_id, api=lib.api) for lib in local_libs_data]
        libs_tips = store.get_libraries_tips(to_query)
        to_publish = []
        for lib_data in local_libs_data:
            logger.debug("Verifying local lib %s", lib_data)
            tip = libs_tips.get((lib_data.lib_id, lib_data.api))
            logger.debug("Store tip: %s", tip)
            if tip is None:
                # needs to first publish
                to_publish.append(lib_data)
                continue

            if tip.patch > lib_data.patch:
                # the store is more advanced than local
                logger.info(
                    "Library %s is out-of-date locally, Charmhub has version %d.%d, please "
                    "fetch the updates before publishing.", lib_data.full_name, tip.api, tip.patch)
            elif tip.patch == lib_data.patch:
                # the store has same version numbers than local
                if tip.content_hash == lib_data.content_hash:
                    logger.info("Library %s is already updated in Charmhub.", lib_data.full_name)
                else:
                    # but shouldn't as hash is different!
                    logger.info(
                        "Library %s version %d.%d is the same than in Charmhub but content is "
                        "different", lib_data.full_name, tip.api, tip.patch)
            elif tip.patch + 1 == lib_data.patch:
                # local is correctly incremented
                if tip.content_hash == lib_data.content_hash:
                    # but shouldn't as hash is the same!
                    logger.info(
                        "Library %s LIBPATCH number was incorrectly incremented, Charmhub has the "
                        "same content in version %d.%d.", lib_data.full_name, tip.api, tip.patch)
                else:
                    to_publish.append(lib_data)
            else:
                logger.info(
                    "Library %s has a wrong LIBPATCH number, it's too high, Charmhub "
                    "highest version is %d.%d.", lib_data.full_name, tip.api, tip.patch)

        for lib_data in to_publish:
            store.create_library_revision(
                lib_data.charm_name, lib_data.lib_id, lib_data.api, lib_data.patch,
                lib_data.content, lib_data.content_hash)
            logger.info(
                "Library %s sent to the store with version %d.%d",
                lib_data.full_name, lib_data.api, lib_data.patch)


class FetchLibCommand(BaseCommand):
    """Fetch one or more charm libraries."""
    name = 'fetch-lib'
    help_msg = "Fetch one or more charm libraries"
    overview = textwrap.dedent("""
        Fetch charm libraries.

        The first time a library is downloaded the command will create the needed
        directories to place it, subsequent fetches will just update the local copy.
    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'library', nargs='?',
            help="Library to fetch (e.g. charms.mycharm.v2.foo.); optional, default to all")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.library:
            local_libs_data = [_get_lib_info(full_name=parsed_args.library)]
        else:
            local_libs_data = _get_libs_from_tree()

        # get tips from the Store
        store = Store()
        to_query = []
        for lib in local_libs_data:
            if lib.lib_id is None:
                item = dict(charm_name=lib.charm_name, lib_name=lib.lib_name)
            else:
                item = dict(lib_id=lib.lib_id)
            item['api'] = lib.api
            to_query.append(item)
        libs_tips = store.get_libraries_tips(to_query)

        # check if something needs to be done
        to_fetch = []
        for lib_data in local_libs_data:
            logger.debug("Verifying local lib %s", lib_data)
            # fix any missing lib id using the Store info
            if lib_data.lib_id is None:
                for tip in libs_tips.values():
                    if lib_data.charm_name == tip.charm_name and lib_data.lib_name == tip.lib_name:
                        lib_data = lib_data._replace(lib_id=tip.lib_id)
                        break

            tip = libs_tips.get((lib_data.lib_id, lib_data.api))
            logger.debug("Store tip: %s", tip)
            if tip is None:
                logger.info("Library %s not found in Charmhub.", lib_data.full_name)
                continue

            if tip.patch > lib_data.patch:
                # the store has a higher version than local
                to_fetch.append(lib_data)
            elif tip.patch < lib_data.patch:
                # the store has a lower version numbers than local
                logger.info(
                    "Library %s has local changes, can not be updated.", lib_data.full_name)
            else:
                # same versions locally and in the store
                if tip.content_hash == lib_data.content_hash:
                    logger.info(
                        "Library %s was already up to date in version %d.%d.",
                        lib_data.full_name, tip.api, tip.patch)
                else:
                    logger.info(
                        "Library %s has local changes, can not be updated.", lib_data.full_name)

        for lib_data in to_fetch:
            downloaded = store.get_library(lib_data.charm_name, lib_data.lib_id, lib_data.api)
            if lib_data.content is None:
                # locally new
                lib_data.path.parent.mkdir(parents=True, exist_ok=True)
                lib_data.path.write_text(downloaded.content)
                logger.info(
                    "Library %s version %d.%d downloaded.",
                    lib_data.full_name, downloaded.api, downloaded.patch)
            else:
                # XXX Facundo 2020-12-17: manage the case where the library was renamed
                # (related GH issue: #214)
                lib_data.path.write_text(downloaded.content)
                logger.info(
                    "Library %s updated to version %d.%d.",
                    lib_data.full_name, downloaded.api, downloaded.patch)


class ListLibCommand(BaseCommand):
    """List all libraries belonging to a charm."""
    name = 'list-lib'
    help_msg = "List all libraries from a charm"
    overview = textwrap.dedent("""
        List all libraries from a charm.

        For each library, it will show the name and the api and patch versions
        for its tip.
    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'name', nargs='?', help=(
                "The name of the charm (optional, will get the name from"
                "metadata.yaml if not given)"))

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'list-lib' command must "
                    "either be executed from a valid project directory, or specify a charm "
                    "name using the --charm-name option.")

        # get tips from the Store
        store = Store()
        to_query = [{'charm_name': charm_name}]
        libs_tips = store.get_libraries_tips(to_query)

        if not libs_tips:
            logger.info("No libraries found for charm %s.", charm_name)
            return

        headers = ['Library name', 'API', 'Patch']
        data = sorted((item.lib_name, item.api, item.patch) for item in libs_tips.values())

        table = tabulate(data, headers=headers, tablefmt='plain', numalign='left')
        for line in table.splitlines():
            logger.info(line)
