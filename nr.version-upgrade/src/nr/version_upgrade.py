# coding: utf8
# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function
from nr.semver import Version

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.0'

import argparse
import collections
import copy
import datetime
import operator
import os
import re
import subprocess
import sys

Config = collections.namedtuple('Config', 'tag branch message upgrades subs')
Match = collections.namedtuple('Match', 'filename lines line_index version span')


def parse_config(filename):
  """
  Parses a versionupgrade configuration file. Example:

      tag v{VERSION}
      branch v{VERSION}
      message Prepare {VERSION} release
      upgrade setup.py:  version = '{VERSION}'
      upgrade __init__.py:__version__ = '{VERSION}'
      sub docs/changelog/v{VERSION}.md:# v{VERSION} (unreleased):# v{VERSION} ({DATE})

  Available commands:

    - tag: Create a Git tag with the specified name.
    - branch: Create a Git branch with the specified name.
    - message: The commit message for upgraded version numbers.
    - upgrade: Upgrade the version number in the file matching the pattern.
               The same file may be listed multiple times. The pattern may
               actually be a regular expression and will be searched in
               every line of the file.
    - sub: Specify a file where the part of the file matching the first string
           will be replaced by the second string.

  Returns a #Config object.
  """

  tag = None
  branch = None
  message = 'Prepare {VERSION} release.'
  upgrades = {}
  subs = {}

  with open(filename) as fp:
    for i, line in enumerate(fp):
      line = line.strip()
      if not line or line.startswith('#'): continue

      key, sep, value = line.partition(' ')
      if not key or not value:
        raise ValueError('invalid configuration file at line {}'.format(i+1))

      if key == 'tag':
        tag = value.strip()
      elif key == 'branch':
        branch = value.strip()
      elif key == 'message':
        message = value.strip()
      elif key == 'upgrade':
        filename, sep, pattern = value.partition(':')
        if not filename or not sep or not pattern or '{VERSION}' not in pattern:
          raise ValueError('invalid upgrade argument at line {}'.format(i+1))
        upgrade = upgrades.setdefault(filename, [])
        upgrade.append(pattern)
      elif key == 'sub':
        filename, sep, pattern = value.partition(':')
        pattern = pattern.partition(':')[::2]
        if not pattern[0] or not pattern[1]:
          raise ValueError('invalid sub argument at line {}'.format(i+1))
        subs.setdefault(filename, []).append(pattern)
      else:
        raise ValueError('invalid command {!r} at line {}'.format(key, i+1))

  return Config(tag, branch, message, upgrades, subs)


def match_version_pattern(filename, pattern):
  """
  Matches a single version upgrade pattern in the specified *filename*
  and returns the match information. Returns a #Match object or #None
  if the *pattern* did not match.
  """

  if "{VERSION}" not in pattern:
    raise ValueError("pattern does not contain a {VERSION} reference")
  pattern = pattern.replace('{VERSION}', '(?P<v>[\d\w\.\-_]+)')
  expr = re.compile(pattern)
  with open(filename) as fp:
    lines = fp.read().split('\n')
  for i, line in enumerate(lines):
    match = expr.search(line)
    if match:
      return Match(filename, lines, line_index=i,
          version=Version(match.group('v')), span=match.span('v'))
  return None


def get_changed_files(include_staged=False):
  """
  Returns a list of the files that changed in the Git repository. This is
  used to check if the files that are supposed to be upgraded have changed.
  If so, the upgrade will be prevented.
  """

  process = subprocess.Popen(['git', 'status', '--porcelain'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  stdout, __ = process.communicate()
  if process.returncode != 0:
    raise ValueError(stdout)
  files = []
  for line in stdout.decode().split('\n'):
    if not line or line.startswith('#'): continue
    assert line[2] == ' '
    if not include_staged and line[1] == ' ': continue
    files.append(line[3:])
  return files


def run(command):
  result = subprocess.call(command)
  if result != 0:
    raise ExitCodeError('command {0!r} exited with returncode {1}'.format(command[0], result))


class ExitCodeError(Exception):
  pass


def exit(*message, **kwargs):
  code = kwargs.pop('code', 0)
  for key in kwargs:
    raise TypeError('unexpected keyword argument:', key)
  if message:
    print_err(*message)
  sys.exit(code)


def print_err(*obj, **kwargs):
  kwargs['file'] = sys.stderr
  print(*obj, **kwargs)


def main(argv=None, prog=None):
  """
  A command-line tool that allows you to automatically update the version
  numbers in your project.
  """

  parser = argparse.ArgumentParser(prog=prog, description="""
  A command-line tool that allows you to automatically update the version
  numbers in your project. The configuration must be called either
  ".versionupgrade" or ".config/versionupgrade". Example config:

    tag v{VERSION}
    branch v{VERSION}
    message Prepare {VERSION} release
    upgrade setup.py:  version = '{VERSION}'
    upgrade __init__.py:__version__ = '{VERSION}'
    sub docs/changelog/v{VERSION}.md:# v{VERSION} (unreleased):# v{VERSION} ({DATE})
  """.rstrip(), formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument('version', nargs='?', type=Version)
  parser.add_argument('--dry', action='store_true', help='do not actually modify files')
  parser.add_argument('--no-commit', action='store_true', help='do not create a new Git commit')
  parser.add_argument('--show', action='store_true', help='show current version number(s)')

  args = parser.parse_args(argv)
  if not args.version and not args.show:
    parser.error('missing required argument: version')

  filename = '.config/versionupgrade'
  if not os.path.isfile(filename):
    filename = '.versionupgrade'

  # Load the configuration.
  try:
    config = parse_config(filename)
  except (OSError, IOError, ValueError) as exc:
    exit("error:", exc, code=1)

  if not config.upgrades:
    exit('fatal: no upgrades specified in ' + filename, code=1)

  # Make sure that none of the files we're going to change have
  # uncomitted changes.
  if not args.dry:
    changed_files = list(filter(lambda x: x in config.upgrades, get_changed_files()))
    if changed_files:
      print("fatal: please commit or stage changes to the following files "
            "before using `versionupgrade`")
      for filename in changed_files:
        print("  {0}".format(filename))
      return 1

  version_matches = []
  per_file_matches = {}
  for filename, patterns in config.upgrades.items():
    matches = []
    try:
      for pattern in patterns:
        match = match_version_pattern(filename, pattern)
        if not match:
          print_err("error: could not match pattern for {0!r}".format(filename))
          print_err("error: pattern: {0!r}".format(pattern))
          exit(code=1)
        matches.append(match)
      del pattern, match
    except ValueError as exc:
      print_err("error: invalid pattern for {0!r}: {1!r}".format(filename, exc))
      exit(code=1)
    except (OSError, IOError) as exc:
      exit("error:", exc, code=1)

    # Make sure the version matches with all versions that we already
    # found in the other files.
    version_matches.extend(matches)
    per_file_matches.setdefault(filename, []).extend(matches)
    for other_match in version_matches:
      if any(other_match.version != x.version for x in matches):
        print_err("fatal: inconsistent version numbers, aborting upgrade")
        for match in version_matches:
          print_err("  {0!r} with version {1!r}".format(match.filename, match.version))
        exit(code=1)

  def subvars(x):
    x = x.replace('{VERSION}', str(args.version))
    x = x.replace('{DATE}', datetime.date.today().strftime('%Y-%m-%d'))
    return x

  if args.show:
    for filename, data in per_file_matches.items():
      print(filename, *['v' + str(x.version) for x in data])
    return 0

  changed_files = []

  # Make sure the new version number is newer than the current one.
  current_version = version_matches[0].version
  if args.version < current_version:
    msg = "fatal: new version '{0}' is older than current version '{1}'"
    exit(msg.format(args.version, current_version), code=1)
  elif args.version == current_version:
    print("current version already is '{0}'".format(args.version))
    files_changed = False
  else:
    print("upgrading version from '{0}' to '{1}'".format(current_version, args.version))
    files_changed = True

    if not args.dry:
      # Update version number in files.
      for filename, matches in per_file_matches.items():
        filename = subvars(filename)
        changed_files.append(filename)

        lines = matches[0].lines
        for match in matches:
          # Replace the version number in the line.
          line_index = match.line_index
          line = lines[line_index]
          span = match.span
          line = line[:span[0]] + str(args.version) + line[span[1]:]
          lines[line_index] = line

        # Write the file back again.
        with open(match.filename, 'w') as fp:
          for index, line in enumerate(lines):
            fp.write(line)
            if index != (len(lines) - 1):
              fp.write('\n')

  # Apply substitutions.
  for filename, patterns in config.subs.items():
    filename = subvars(filename)
    changed_files.append(filename)

    with open(filename, 'r') as fp:
      text = fp.read()
    for pattern in patterns:
      pattern = subvars(pattern[0]), subvars(pattern[1])
      if pattern[0] not in text:
        exit('fatal: "{}" not found in file "{}"'.format(pattern[0], filename))
      text = text.replace(pattern[0], pattern[1])
    if not args.dry:
      with open(filename, 'w') as fp:
        fp.write(text)

  if args.dry or args.no_commit:
    return 0

  # Commit the files and create a Git tag.
  msg = subvars(config.message)
  if files_changed:
    if subprocess.call(['git', 'commit', '-m', msg] + changed_files) != 0:
      return 1

  # Create the tag and branch.
  ret = 0
  if config.tag:
    tag_name = subvars(config.tag)
    print('creating tag:', tag_name)
    if subprocess.call(['git', 'tag', tag_name]) != 0:
      ret = 1
  if config.branch:
    branch_name = subvars(config.branch)
    print('creating branch:', branch_name)
    if subprocess.call(['git', 'branch', branch_name, 'HEAD']) != 0:
      ret = 1

  return ret


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  sys.exit(main())
