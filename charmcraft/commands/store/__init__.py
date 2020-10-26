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

"""Commands related to the Store, a thin layer above real functionality."""

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

from .store import Store

logger = logging.getLogger('charmcraft.commands.store')

LibData = namedtuple(
    'LibData', 'lib_id api patch content content_hash full_name path lib_name charm_name')

LIBRARY_TEMPLATE = """
\"""TEMPLATE FIXME: Add a proper docstring here.

This is the main documentation of the library, will be exposed by Charmhub after
the lib is published.

Markdown is supported.
\"""

# Never change this field, it's the unique identifier to track the library in
# all systems
LIBID = "{lib_id}"

# Update this API version when introducing backwards incompatible
# changes in the library.
LIBAPI = 0

# Update this version for every change in the library before (re)publishing it
# (except for the initial content).
LIBPATCH = 1

# TEMPLATE FIXME: add your code here! Happy coding!
"""


def get_name_from_metadata():
    """Return the name (if present) from metadata file (if there and readable and sane)."""
    try:
        with open('metadata.yaml', 'rb') as fh:
            metadata = yaml.safe_load(fh)
        charm_name = metadata['name']
    except (yaml.error.YAMLError, OSError, KeyError):
        return
    return charm_name


class LoginCommand(BaseCommand):
    """Log into the store."""
    name = 'login'
    help_msg = "Login to Ubuntu Single Sign On."
    overview = textwrap.dedent("""
        Log in to the Store using Ubuntu Single Sign On.

        It will open a browser window where you will need to provide the
        relevant credentials.

        See also the "whoami" command to verify you're properly logged in,
        and the "logout" command to clear the session credentials.
    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.login()
        logger.info("Login successful.")


class LogoutCommand(BaseCommand):
    """Clear store-related credentials."""
    name = 'logout'
    help_msg = "Clear session credentials."
    overview = textwrap.dedent("""
        Clear the Store session credentials.

        Because of the authentication mechanism used there is no Store-side state
        to clear, so this operation does not contact the Store.

        See also the "whoami" command to verify you're properly logged in,
        and the "login" command to log in to the Store.
    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.logout()
        logger.info("Credentials cleared.")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "Return your login information relevant to the Store."
    overview = textwrap.dedent("""
        Show login information for the current Store user.

        See also the "login" and "logout" commands for more information about
        the authentication cycle.
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
    """Register a name in the Store."""
    name = 'register'
    help_msg = "Register a charm name in the Store."
    overview = textwrap.dedent("""
        Register a charm name in the Store.

        This is the first step when developing a charm, and needed only once
        for that charm.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('name', help="The name to register in the Store.")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.register_name(parsed_args.name)
        logger.info("Congrats! You are now the publisher of %r.", parsed_args.name)


class ListNamesCommand(BaseCommand):
    """List the charms registered in the Store."""
    name = 'names'
    help_msg = "List the charm names registered in the Store."
    overview = textwrap.dedent("""
        List the names registered to the current Store user, together
        with each package's type, visibility and status.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.list_registered_names()
        if not result:
            logger.info("Nothing found.")
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
    """Upload a charm file to the Store."""
    name = 'upload'
    help_msg = "Upload a charm file to the Store."
    overview = textwrap.dedent("""
        Upload the charm file to the Store.

        This command covers both pushing the charm itelf, as well as the
        subsequent status verification actions, and will finish successfully once
        the package is approved by the Store (otherwise it will report the
        verification failure reasons).

        It will automatically take you through the login process if
        your credentials are missing or too old.
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
                    "Can't access name in 'metadata.yaml' file. The 'upload' command needs to be "
                    "executed in a valid project's directory, or point to a charm file with "
                    "the --charm-file option.")

            charm_filepath = pathlib.Path(charm_name + '.charm').absolute()
            if not os.access(str(charm_filepath), os.R_OK):  # access doesnt support pathlib in 3.5
                raise CommandError(
                    "Can't access charm file {!r}. You can indicate a charm file with "
                    "the --charm-file option.".format(str(charm_filepath)))

        else:
            # the path is given, asume the charm name is part of the file name
            # XXX Facundo 2020-06-30: Actually, we need to open the ZIP file, extract the
            # included metadata.yaml file, and read the name from there. Issue: #77.
            charm_filepath = charm_filepath.expanduser()
            if not os.access(str(charm_filepath), os.R_OK):  # access doesnt support pathlib in 3.5
                raise CommandError(
                    "Can't access the indicated charm file: {!r}".format(str(charm_filepath)))
            if not charm_filepath.is_file():
                raise CommandError(
                    "The indicated charm is not a file: {!r}".format(str(charm_filepath)))

            charm_name = charm_filepath.stem

        return charm_name, charm_filepath

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            '--charm-file', type=pathlib.Path,
            help="The path to the charm file to upload.")

    def run(self, parsed_args):
        """Run the command."""
        # FIXME: check in this command if all "own libraries" are properly updated in the Store
        name, path = self._discover_charm(parsed_args.charm_file)
        store = Store()
        result = store.upload(name, path)
        if result.ok:
            logger.info("Revision %s of %r created", result.revision, str(name))
        else:
            # XXX Facundo 2020-06-30: at some point in the future the Store will give us also a
            # reason why it failed, to improve the message. Issue: #78.
            logger.info("Upload failed: got status %r", result.status)


class ListRevisionsCommand(BaseCommand):
    """List existing revisions for a charm."""
    name = 'revisions'
    help_msg = "List existing revisions for a charm in the Store."
    overview = textwrap.dedent("""
        List existing revisions for a charm in the Store, along with the version
        and status for each, and when they were created.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="The name of the charm.")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'revisions' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --name option.")

        store = Store()
        result = store.list_revisions(charm_name)
        if not result:
            logger.info("Nothing found")
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
    help_msg = "Release a charm revision to one or more channels."
    overview = textwrap.dedent("""
        Release a charm revision to the indicated channels (one or many).

        Each channel has the [track/]risk[/branch] structure, where the risk
        (stable, candidate, beta or edge) is mandatory, while track (default
        to "latest") and branch are optional.

        Some channel examples:

            stable
            edge
            2.0/candidate
            beta/hotfix

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'revision', type=int, help='The revision to release.')
        parser.add_argument(
            'channels', metavar='channel', nargs='+',
            help="The channel(s) to release to.")
        parser.add_argument('--name', help="The name of the charm.")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()

        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'release' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --name option.")

        store.release(charm_name, parsed_args.revision, parsed_args.channels)
        logger.info(
            "Revision %d of charm %r released to %s",
            parsed_args.revision, charm_name, ", ".join(parsed_args.channels))


class StatusCommand(BaseCommand):
    """List released revisions for a charm."""
    name = 'status'
    help_msg = "List released revisions of a package."
    overview = textwrap.dedent("""
        List the released revisions for a package.

        It will show each risk (with all its relevant information) for the
        different tracks, series, etc.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="The name of the charm.")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'status' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --name option.")

        store = Store()
        channel_map, channels, revisions = store.list_releases(charm_name)
        if not channel_map:
            logger.info("Nothing found")
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


def _convert_lib_to_path(full_name):
    """Convert a lib name with dots to the full path, including lib dir and Python extension.

    E.g.: charms.mycharm.v4.foo -> lib/charms/mycharm/v4/foo.py
    """
    return pathlib.Path('lib') / pathlib.Path(full_name.replace('.', os.sep) + '.py')


def _get_lib_info(full_name, libpath): #FIXME test all this function
    """Get the whole lib info from the path/file."""
    # FIXME: this function probably shouldn't raise ValueError but something like CommandError
    bad_structure_msg = (
        "Library path {!r} must conform to the lib/charms/<charm>/v<API>/<libname>.py "
        "structure.".format(libpath))
    try:
        libsdir, charmsdir, charm_name, v_api, libfile = libpath.parts
    except ValueError:
        raise ValueError(bad_structure_msg)

    if libsdir != 'lib' or charmsdir != 'charms':
        raise ValueError(bad_structure_msg)

    if v_api[0] != 'v' or not v_api[1:].isdigit():
        raise ValueError("The API version in the library path must be 'vN' where N is an integer.")
    api_from_path = int(v_api[1:])

    lib_name = full_name.split('.')[-1]
    if not libpath.exists():
        return LibData(
            lib_id=None, api=api_from_path, patch=-1, content_hash=None, content=None,
            full_name=full_name, path=libpath, lib_name=lib_name, charm_name=charm_name)

    # parse the file and extract metadata from it, while hashing
    metadata_fields = (b'LIBAPI', b'LIBPATCH', b'LIBID')
    metadata = dict.fromkeys(metadata_fields)
    hasher = hashlib.sha256()
    with libpath.open('rb') as fh:
        for line in fh:
            if line.startswith(metadata_fields):
                try:
                    field, value = [x.strip() for x in line.split(b'=')]
                except ValueError:
                    raise ValueError("Bad metadata line in {}: {!r}".format(libpath, line))
                metadata[field] = value
            else:
                hasher.update(line)

    missing = [k.decode('ascii') for k, v in metadata.items() if v is None]
    if missing:
        raise ValueError(
            "Library {} is missing the mandatory metadata fields: {}"
            .format(libpath, ', '.join(missing)))

    def _get_positive_int(key):
        """Convert the raw value for api/patch into a positive integer."""
        value = metadata[key].decode('ascii')
        value = int(value)
        if value < 0:
            raise ValueError('negative')
        return value

    bad_api_patch_msg = "Library {} metadata field {} is not zero or a positive integer."
    try:
        libapi = _get_positive_int(b'LIBAPI')
    except Exception:
        raise ValueError(bad_api_patch_msg.format(libpath, 'LIBAPI'))
    try:
        libpatch = _get_positive_int(b'LIBPATCH')
    except Exception:
        raise ValueError(bad_api_patch_msg.format(libpath, 'LIBPATCH'))

    if libapi == 0 and libpatch == 0:
        raise ValueError(
            "Library {} metadata fields LIBAPI and LIBPATCH can not be both zero."
            .format(libpath))

    if libapi != api_from_path:
        raise ValueError(
            "Library {} metadata field LIBAPI is different than the version in the path."
            .format(libpath))

    try:
        libid = ast.literal_eval(metadata[b'LIBID'].decode('ascii'))
    except (ValueError, UnicodeDecodeError):
        raise ValueError(
            "Library {} metadata field LIBID must be a non-empty string.".format(libpath))

    content_hash = hasher.hexdigest()
    content = libpath.read_text()

    return LibData(
        lib_id=libid, api=libapi, patch=libpatch, content_hash=content_hash, content=content,
        full_name=full_name, path=libpath, lib_name=lib_name, charm_name=charm_name)


class CreateLibCommand(BaseCommand):
    """Create a charm library."""
    name = 'create-lib'
    help_msg = "Create a charm library."
    overview = textwrap.dedent("""
        Create a charm library.

        It will request a unique ID from Charmhub and bootstrap a
        template file in the proper local directory.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('lib-name', help="The name of the library file (e.g. 'db').")

    def run(self, parsed_args):
        """Run the command."""
        lib_name = parsed_args.lib_name
        valid_chars = set(string.ascii_lowercase + string.digits + '_')
        if set(lib_name) - valid_chars or lib_name[0] not in string.ascii_lowercase:
            raise CommandError(
                "Invalid library name (can be only lowercase alphanumeric "
                "characters and underscore, starting with alpha).")

        charm_name = get_name_from_metadata()
        if charm_name is None:
            raise CommandError(
                "Can't access name in 'metadata.yaml' file. The 'create-lib' command needs to "
                "be executed in a valid project's directory.")

        full_name = 'charms.{}.v0.{}'.format(charm_name, lib_name)
        lib_path = _convert_lib_to_path(full_name)
        if lib_path.exists():
            raise CommandError('The indicated library already exists on {}'.format(lib_path))

        store = Store()
        lib_id = store.create_library_id(charm_name, lib_name)

        lib_path.parent.mkdir(parents=True, exist_ok=True)
        lib_path.write_text(LIBRARY_TEMPLATE.format(lib_id=lib_id))

        logger.info("Library %s created with id %s.", full_name, lib_id)
        logger.info("Make sure to add the library file to your project: %s", lib_path)


class PublishLibCommand(BaseCommand):
    """Publish one or more charm libraries."""
    name = 'publish-lib'
    help_msg = "Publish one or more charm libraries."
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
            help="Library to publish (e.g. charms.mycharm.v2.foo.); optional, default to all.")

    def run(self, parsed_args):
        """Run the command."""
        charm_name = get_name_from_metadata()
        if charm_name is None:
            raise CommandError(
                "Can't access name in 'metadata.yaml' file. The 'publish-lib' command needs to "
                "be executed in a valid project's directory.")

        if parsed_args.library:
            libpath = _convert_lib_to_path(parsed_args.library)
            if not libpath.exists():
                raise CommandError(
                    "The specified library was not found at path {}.".format(libpath))
            lib_data = _get_lib_info(parsed_args.library, libpath)
            if lib_data.charm_name != charm_name:
                raise CommandError(
                    "The library {} does not belong to this charm {!r}.".format(
                        lib_data.full_name, charm_name))
            local_libs_data = [lib_data]
        else:
            base_dir = pathlib.Path('lib') / 'charms' / charm_name
            local_libs_data = []
            if base_dir.exists():
                for v_dir in sorted(base_dir.iterdir()):
                    if v_dir.is_dir() and v_dir.name[0] == 'v' and v_dir.name[1:].isdigit():
                        for libfile in sorted(v_dir.glob('*.py')):
                            full_name = '.'.join(('charms', charm_name, v_dir.stem, libfile.stem))
                            lib_data = _get_lib_info(full_name, libfile)
                            local_libs_data.append(lib_data)

            found_libs = [lib_data.full_name for lib_data in local_libs_data]
            logger.debug("Libraries found under %s: %s", base_dir, found_libs)

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
                    "fetch the updates before publish.", lib_data.full_name, tip.api, tip.patch)
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
    help_msg = "Fetch one or more charm libraries."
    overview = textwrap.dedent("""
        Fetch charm libraries.

        It will download the library the first time, and update it the next times.
    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'library', nargs='?',
            help="Library to fetch (e.g. charms.mycharm.v2.foo.); optional, default to all.")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.library:
            libpath = _convert_lib_to_path(parsed_args.library)
            libraries = [(parsed_args.library, libpath)]
        else:
            base_dir = pathlib.Path('lib') / 'charms'
            libraries = []
            if base_dir.exists():
                for charm_dir in sorted(base_dir.iterdir()):
                    for v_dir in sorted(charm_dir.iterdir()):
                        if v_dir.is_dir() and v_dir.name[0] == 'v' and v_dir.name[1:].isdigit():
                            for libfile in sorted(v_dir.glob('*.py')):
                                full_name = '.'.join(
                                    ('charms', charm_dir.stem, v_dir.stem, libfile.stem))
                                libraries.append((full_name, libfile))

            found_libs = [full_name for full_name, _ in libraries]
            logger.debug("Libraries found under %s: %s", base_dir, found_libs)

        # get the libraries info
        local_libs_data = [_get_lib_info(name, path) for name, path in libraries]

        # get tips from the Store
        store = Store()
        to_query = []
        for lib in local_libs_data:
            if lib.lib_id is None:
                d = dict(charm_name=lib.charm_name, lib_name=lib.lib_name)
            else:
                d = dict(lib_id=lib.lib_id)
            d['api'] = lib.api
            to_query.append(d)
        libs_tips = store.get_libraries_tips(to_query)

        # check if something needs to be done
        to_fetch = []
        for lib_data in local_libs_data:
            logger.debug("Verifying local lib %s", lib_data)
            # if locally we didn't have the lib id, let's fix it from the Store info
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
                # the store is more advanced than local
                to_fetch.append(lib_data)
            elif tip.patch < lib_data.patch:
                # the store has smaller version numbers than local
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
            if lib_data.content is None:
                # locally new
                downloaded = store.get_library(
                    lib_data.charm_name, lib_data.lib_id, lib_data.api)
                lib_data.path.parent.mkdir(parents=True, exist_ok=True)
                lib_data.path.write_text(downloaded.content)
                logger.info(
                    "Library %s version %d.%d downloaded.",
                    lib_data.full_name, downloaded.api, downloaded.patch)
            else:
                downloaded = store.get_library(
                    lib_data.charm_name, lib_data.lib_id, lib_data.api)
                # XXX Facundo 2020-10-23: manage the case where the library was renamed
                lib_data.path.write_text(downloaded.content)
                logger.info(
                    "Library %s updated to version %d.%d.",
                    lib_data.full_name, downloaded.api, downloaded.patch)


class ListLibCommand(BaseCommand):
    """List all libraries belonging to a charm."""
    name = 'list-lib'
    help_msg = "List all libraries from a charm."
    overview = textwrap.dedent("""
        List all libraries from a charm.

        For each library, it will show the name and the api and patch versions
        for its tip.
    """)

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--charm-name', help="The name of the charm.")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.charm_name:
            charm_name = parsed_args.charm_name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'list-lib' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --charm-name option.")

        # get tips from the Store
        store = Store()
        to_query = [{'charm_name': charm_name}]
        libs_tips = store.get_libraries_tips(to_query)

        if not libs_tips:
            logger.info("Nothing found.")
            return

        headers = ['Library name', 'API', 'Patch']
        data = sorted((item.lib_name, item.api, item.patch) for item in libs_tips.values())

        table = tabulate(data, headers=headers, tablefmt='plain', numalign='left')
        for line in table.splitlines():
            logger.info(line)
