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

import io
import textwrap

from charmcraft import jujuignore


def test_jujuignore_only_dir():
    ignore = jujuignore.JujuIgnore(['target/'])
    assert ignore.match('target', is_dir=True)
    assert ignore.match('foo/target', is_dir=True)
    assert not ignore.match('foo/1target', is_dir=True)
    assert not ignore.match('foo/target', is_dir=False)


def test_jujuignore_any_target():
    ignore = jujuignore.JujuIgnore(['target'])
    assert ignore.match('target', is_dir=True)
    assert ignore.match('/foo/target', is_dir=True)
    assert not ignore.match('/foo/1target', is_dir=True)
    assert ignore.match('/foo/target', is_dir=False)


def test_jujuignore_only_root_target_dir():
    ignore = jujuignore.JujuIgnore(['/target/'])
    assert ignore.match('/target', is_dir=True)
    assert not ignore.match('/foo/target', is_dir=True)
    assert not ignore.match('/foo/1target', is_dir=True)
    assert not ignore.match('/foo/target', is_dir=False)
    assert not ignore.match('/target', is_dir=False)


def test_jujuignore_only_root_target_file_or_dir():
    ignore = jujuignore.JujuIgnore(['/target'])
    assert ignore.match('/target', is_dir=True)
    assert not ignore.match('/foo/target', is_dir=True)
    assert not ignore.match('/foo/1target', is_dir=True)
    assert not ignore.match('/foo/target', is_dir=False)
    assert ignore.match('/target', is_dir=False)


def test_jujuignore_all_py_files():
    ignore = jujuignore.JujuIgnore(['*.py'])
    assert not ignore.match('/target', is_dir=True)
    assert ignore.match('/target.py', is_dir=True)
    assert ignore.match('/target.py', is_dir=False)
    assert ignore.match('/foo/target.py', is_dir=True)
    assert ignore.match('/foo/target.py', is_dir=False)
    assert not ignore.match('/target.pyT', is_dir=True)
    assert not ignore.match('/target.pyT', is_dir=False)


def test_jujuignore_all_py_files_in_foo():
    ignore = jujuignore.JujuIgnore(['/foo/*.py'])
    assert not ignore.match('/target.py', is_dir=True)
    assert not ignore.match('/target.py', is_dir=False)
    assert ignore.match('/foo/target.py', is_dir=True)
    assert ignore.match('/foo/target.py', is_dir=False)
    assert not ignore.match('/foo/sub/target.py', is_dir=False)


def test_jujuignore_ignore_comment():
    ignore = jujuignore.JujuIgnore([
        '#comment',
        'target',
    ])
    assert ignore.match('/target', is_dir=True)
    assert not ignore.match('/comment', is_dir=False)
    assert not ignore.match('/#comment', is_dir=False)
    assert not ignore.match('#comment', is_dir=False)
    assert not ignore.match('/foo/comment', is_dir=False)
    assert not ignore.match('/foo/#comment', is_dir=False)


def test_jujuignore_escaped_comment():
    ignore = jujuignore.JujuIgnore([
        '\\#comment',
        'target',
    ])
    assert ignore.match('/target', is_dir=True)
    assert ignore.match('/#comment', is_dir=False)
    assert ignore.match('#comment', is_dir=False)
    assert not ignore.match('/foo/comment', is_dir=False)
    assert ignore.match('/foo/#comment', is_dir=False)


def test_jujuignore_subdirectory_match():
    ignore = jujuignore.JujuIgnore(['apps/logs/'])
    assert not ignore.match('/logs', is_dir=True)
    assert not ignore.match('/apps', is_dir=True)
    assert ignore.match('/apps/logs', is_dir=True)
    assert not ignore.match('/apps/logs', is_dir=False)
    assert not ignore.match('/apps/foo/logs', is_dir=True)


def test_jujuignore_sub_subdirectory_match():
    ignore = jujuignore.JujuIgnore(['apps/*/logs/'])
    assert not ignore.match('/logs', is_dir=True)
    assert not ignore.match('/apps', is_dir=True)
    assert not ignore.match('/apps/logs', is_dir=True)
    assert not ignore.match('/apps/logs', is_dir=False)
    assert ignore.match('/apps/foo/logs', is_dir=True)
    assert ignore.match('/apps/bar/logs', is_dir=True)
    assert not ignore.match('/apps/baz/logs', is_dir=False)
    assert not ignore.match('/apps/foo/bar/logs', is_dir=True)


def test_jujuignore_any_subdirectory_match():
    ignore = jujuignore.JujuIgnore(['apps/**/logs/'])
    assert not ignore.match('/logs', is_dir=True)
    assert not ignore.match('/apps', is_dir=True)
    assert ignore.match('/apps/logs', is_dir=True)
    assert not ignore.match('/apps/logs', is_dir=False)
    assert ignore.match('/apps/foo/logs', is_dir=True)
    assert ignore.match('/apps/bar/logs', is_dir=True)
    assert ignore.match('/apps/bar/bing/logs', is_dir=True)
    assert not ignore.match('/apps/baz/logs', is_dir=False)


def test_jujuignore_everything_under_foo():
    ignore = jujuignore.JujuIgnore(['foo/**'])
    assert not ignore.match('/foo', is_dir=True)
    assert ignore.match('/foo/a', is_dir=True)
    assert ignore.match('/foo/a', is_dir=False)
    assert ignore.match('/foo/a/b', is_dir=False)


def test_jujuignore_everything_under_foo_but_readme():
    ignore = jujuignore.JujuIgnore([
        'foo/**',
        '!foo/README.md',
    ])
    assert not ignore.match('/foo', is_dir=True)
    assert ignore.match('/foo/a', is_dir=True)
    assert ignore.match('/foo/a', is_dir=False)
    assert ignore.match('/foo/a/b', is_dir=False)
    assert not ignore.match('/foo/README.md', is_dir=False)


def test_jujuignore_negation():
    ignore = jujuignore.JujuIgnore([
        '*.py',
        '!foo.py',
        '!!!bar.py',
    ])
    assert not ignore.match('bar.py', is_dir=False)
    assert not ignore.match('foo.py', is_dir=False)
    assert ignore.match('baz.py', is_dir=False)
    assert not ignore.match('foo/bar.py', is_dir=False)
    assert not ignore.match('foo/foo.py', is_dir=False)
    assert ignore.match('foo/baz.py', is_dir=False)


def test_jujuignore_multiple_doublestar():
    ignore = jujuignore.JujuIgnore(['foo/**/bar/**/baz'])
    assert ignore.match('/foo/1/2/bar/baz', is_dir=True)
    assert ignore.match('/foo/1/2/bar/1/2/baz', is_dir=True)
    assert ignore.match('/foo/bar/1/2/baz', is_dir=True)
    assert ignore.match('/foo/1/bar/baz', is_dir=True)
    assert ignore.match('/foo/bar/baz', is_dir=True)


def test_jujuignore_trim_unescaped_trailing_space():
    ignore = jujuignore.JujuIgnore([
        r'foo  ',
        r'bar\ \ ',
    ])
    assert ignore.match('/foo', is_dir=True)
    assert not ignore.match('/bar', is_dir=True)
    assert ignore.match('/bar  ', is_dir=True)


def test_jujuignore_escaped_bang():
    ignore = jujuignore.JujuIgnore([
        r'foo',
        r'!/foo',
        r'\!foo',
    ])
    assert not ignore.match('/foo', is_dir=True)
    assert ignore.match('/bar/foo', is_dir=True)
    assert ignore.match('!foo', is_dir=True)


def test_jujuignore_leading_whitespace():
    ignore = jujuignore.JujuIgnore([
        r'foo',
        r' bar',
        r' #comment',
    ])
    assert ignore.match('/foo', is_dir=True)
    assert ignore.match('/bar', is_dir=True)
    assert ignore.match('/bar/foo', is_dir=True)
    assert not ignore.match('#comment', is_dir=True)
    assert not ignore.match('comment', is_dir=True)


def test_jujuignore_bracket():
    ignore = jujuignore.JujuIgnore([
        r'*.py[cod]',
    ])
    assert not ignore.match('foo.py', is_dir=False)
    assert ignore.match('foo.pyc', is_dir=False)
    assert ignore.match('foo.pyo', is_dir=False)
    assert ignore.match('foo.pyd', is_dir=False)


def test_jujuignore_simple_match():
    ignore = jujuignore.JujuIgnore([
        r'foo',
    ])
    assert ignore.match('/foo', is_dir=True)
    assert ignore.match('/bar/foo', is_dir=True)
    assert not ignore.match('/bar/bfoo', is_dir=True)
    assert not ignore.match('/bfoo', is_dir=True)


def test_jujuignore_star_match():
    ignore = jujuignore.JujuIgnore([
        r'foo*.py',
    ])
    assert ignore.match('/foo.py', is_dir=False)
    assert ignore.match('/foo2.py', is_dir=False)
    assert ignore.match('/foobar.py', is_dir=False)
    assert ignore.match('/bar/foo.py', is_dir=False)
    assert not ignore.match('/foo/2.py', is_dir=False)


def test_jujuignore_paths_with_newlines():
    ignore = jujuignore.JujuIgnore([
        r'bar/**/*.py'
    ])
    assert ignore.match('/bar/foo.py', is_dir=False)
    assert ignore.match('/bar/f\noo.py', is_dir=False)
    assert ignore.match('/bar/baz/f\noo.py', is_dir=False)
    assert ignore.match('/bar/b\nz/f\noo.py', is_dir=False)


def test_rstrip_unescaped():
    assert jujuignore._rstrip_unescaped(r'') == ''
    assert jujuignore._rstrip_unescaped(r' ') == ''
    assert jujuignore._rstrip_unescaped(r'a') == 'a'
    assert jujuignore._rstrip_unescaped(r'a ') == 'a'
    assert jujuignore._rstrip_unescaped(r'a  ') == 'a'
    assert jujuignore._rstrip_unescaped(r'a\  ') == r'a\ '
    assert jujuignore._rstrip_unescaped(r'a foo\  ') == r'a foo\ '


def test_unescape_rule():
    assert jujuignore._unescape_rule(r'') == ''
    assert jujuignore._unescape_rule(r' ') == ''
    assert jujuignore._unescape_rule(r'\#') == '#'
    assert jujuignore._unescape_rule(r'\!') == '!'
    assert jujuignore._unescape_rule(r'\ ') == ' '
    assert jujuignore._unescape_rule(r' foo\ ') == 'foo '


def test_from_file():
    content = io.StringIO(textwrap.dedent('''\
    foo
    /bar
    '''))
    ignore = jujuignore.JujuIgnore(content)
    assert ignore.match('foo', is_dir=False)
    assert ignore.match('/foo', is_dir=False)
    assert ignore.match('/bar', is_dir=False)
    assert not ignore.match('/foo/bar', is_dir=False)


def assertMatchedAndNonMatched(globs, matched, unmatched):
    """For a given set of globs, check that it does and doesn't match as expected"""
    ignore = jujuignore.JujuIgnore(globs)
    for m in matched:
        assert ignore.match(m, is_dir=False)
    for m in unmatched:
        assert not ignore.match(m, is_dir=False)


def test_star_vs_star_start():
    assertMatchedAndNonMatched(
        ['/*.py', '**/foo'],
        # Only top level .py files, but foo at any level
        ['a.py', 'b.py', 'foo', 'bar/foo'],
        ['foo/a.py', 'bar/b.py']
    )
