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

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.0'

import argparse
import json
import os
import posixpath
import re
import subprocess
import shutil
import stat
import sys
import uuid

try:
  from urllib.parse import urlparse
except ImportError:
  from urlparse import urlparse

try:
  from configparser import SafeConfigParser
except ImportError:
  from ConfigParser import SafeConfigParser


CONFIG_FILENAME = '.gitsubrepos'


def chdir_to_project_root():
  prefix = os.getenv('GIT_PREFIX', '')
  if prefix:
    assert os.path.exists('.git'), "GIT_PREFIX set but CWD has no .git directory/file"
    return prefix

  # Change to the local .git repository.
  path, prev = os.getcwd(), None
  while not os.path.exists(os.path.join(path, '.git')):
    if prev == path:
      print('fatal: Git directory not found', file=sys.stderr)
      sys.exit(1)
    prev = path
    path = os.path.dirname(path)

  prefix = os.path.relpath(os.getcwd(), path)
  os.chdir(path)
  return prefix


def read_config():
  if not os.path.isfile(CONFIG_FILENAME):
    return {}
  with open(CONFIG_FILENAME) as fp:
    while True:
      pos = fp.tell()
      if fp.readline().startswith('#'): continue
      fp.seek(pos)
      break
    return json.load(fp)


def write_config(config):
  if config:
    with open(CONFIG_FILENAME, 'w') as fp:
      json.dump(config, fp, indent=2, sort_keys=True)
  elif os.path.isfile(CONFIG_FILENAME):
    os.remove(CONFIG_FILENAME)


def read_gitmodules():
  parser = SafeConfigParser()
  parser.read('.gitmodules')
  modules = {}
  for section in parser.sections():
    path = parser.get(section, 'path')
    url = parser.get(section, 'url')
    modules[path] = {'url': url}
  return modules


def rmtree_onerror_retry_remove(func, path, exc_info):
  os.chmod(path, stat.S_IWRITE)
  func(path)


def git_get_num_stashes(path):
  out = subprocess.check_output(['git', '-C', path, 'stash', 'list']).decode().strip()
  if not out:
    return 0
  return out.count('\n') + 1


class Subrepo(object):

  @staticmethod
  def get_argument_parser(prog):
    parser = argparse.ArgumentParser(prog, description=main.__doc__)
    parser.add_argument('--version', action='version', version=__version__)
    subparsers = parser.add_subparsers(dest='command')

    add_parser = subparsers.add_parser('add', description='add a sub repository and stage the contents')
    add_parser.add_argument('repository', help='the repository url')
    add_parser.add_argument('path', help='the path to add the subrepo', nargs='?')
    add_parser.add_argument('-b', '--branch', help='the branch or ref to check out')
    add_parser.add_argument('-s', '--stage', action='store_true', help='stage the new sub repository')
    add_parser.add_argument('--recursive', action='store_true', help='clone submodules in the sub repository')

    rename_parser = subparsers.add_parser('rename', description='rename a sub repository')
    rename_parser.add_argument('old', help='the current path to the sub repository')
    rename_parser.add_argument('new', help='the new path of sub repository')

    rm_parser = subparsers.add_parser('rm', description='remove a sub repository')
    rm_parser.add_argument('path', help='the path to the sub repository')

    update_parser = subparsers.add_parser('update', description='restore the git worktree status for sub repositories')
    update_parser.add_argument('path', help='the path to the sub repository', nargs='?')

    stage_parser = subparsers.add_parser('stage', description='stage all changes in a sub repository -- can be used with untracked repositories that are already checked out')
    stage_parser.add_argument('--all', action='store_true', help='stage all sub repositories')
    stage_parser.add_argument('path', help='the path to the sub repository', nargs='?')

    prune_parser = subparsers.add_parser('prune', description='remove all cloned sub repositories in the .git/subrepos folder')

    convert_module_parser = subparsers.add_parser('convert-module',
      description='convert one or multiple Git submodules to sub repositories.\n'
                  'note: the command is not fully tested and potentially dangerous.')
    convert_module_parser.add_argument('--all', action='store_true', help='convert all Git submodules')
    convert_module_parser.add_argument('--yes', action='store_true', help='continue without confirmation')
    convert_module_parser.add_argument('-s', '--stage', action='store_true', help='stage the new sub repository')
    convert_module_parser.add_argument('--recursive', action='store_true', help='clone submodules in the sub repository')
    convert_module_parser.add_argument('path', help='the path to the Git submodule to convert', nargs='?')

    return parser

  def main(self, argv=None, prog=None):
    self.parser = self.get_argument_parser(prog)
    self.args = self.parser.parse_args(argv)
    self.prefix = chdir_to_project_root()
    self.config = read_config()
    if not self.args.command:
      self.handle_list()
      return 0
    return getattr(self, 'handle_' + self.args.command.replace('-', '_'))()

  @property
  def path(self):
    if not getattr(self.args, 'path', None):
      return None
    return self.get_path(self.args.path)

  def get_path(self, path):
    path = os.path.normpath(os.path.join(self.prefix, path))
    if os.name == 'nt':
      path = path.replace('\\', '/')
    return path

  def fatal(self, message):
    print('fatal:', message, file=sys.stderr)
    sys.exit(1)

  def restore_worktree(self, path, ref):
    bare_path = os.path.join('.git', 'subrepos', path)
    git_dir = os.path.join(bare_path, 'worktrees', os.path.basename(path))
    git_dir = os.path.abspath(git_dir).replace('\\', '/')
    git_file = os.path.join(path, '.git')

    # Create the worktree directory.
    if not os.path.isdir(git_dir) or not os.path.exists(path):
      cmd = ['git', '-C', bare_path, 'worktree', 'prune']
      res = subprocess.call(cmd)
      if res != 0:
        return res

      # If the directory where the worktree is to be created already exists,
      # we need to temporarily rename it so that the worktree creation succeeds.
      temp_name = None
      if os.path.exists(path):
        temp_name = path.rstrip('/').rstrip('\\') + '-' + str(uuid.uuid4())[:8]
        os.rename(path, temp_name)

      try:
        cmd = ['git', '-C', bare_path, 'worktree', 'add', '--detach', os.path.abspath(path)]
        res = subprocess.call(cmd)
        if res != 0:
          return res
        if not os.path.isdir(git_dir):
          self.fatal('{}: worktree add did not create git_dir {!r}'.format(path, git_dir))
      finally:
        if temp_name is not None:
          os.rename(os.path.join(path, '.git'), os.path.join(temp_name, '.git'))
          shutil.rmtree(path, onerror=rmtree_onerror_retry_remove)
          os.rename(temp_name, path)
          # Re-stat all files, otherwise git diff-index HEAD -- will return
          # that files changed even if they didn't.
          subprocess.call(['git', '-C', path, 'add', '.'])
          subprocess.call(['git', '-C', path, 'reset', '--quiet'])

    # Ensure that the .git file points to the worktree directory.
    # Only write to the file if its contents are incorrect.
    if os.path.isfile(git_file):
      with open(git_file) as fp:
        contents = fp.read()
    else:
      contents = None
    if not contents or not contents.strip().endswith(git_dir):
      with open(git_file, 'w') as fp:
        fp.write('gitdir: {}\n'.format(git_dir))

    # Make sure we checked out the correct ref in the repository.
    if ref is not None:
      has_changes = (subprocess.call(['git', '-C', path, 'diff-index', '--quiet', 'HEAD', '--']) != 0)
      if has_changes:
        # Get the number of saved stashes. If the push operation does not
        # add a new one on top, we know that nothing was stashed. This can
        # occur for example if a submodule appears as deleted in the worktree.
        stashes = git_get_num_stashes(path)
        subprocess.check_call(['git', '-C', path, 'stash', 'push', '--all', '--quiet'])
        if stashes == git_get_num_stashes(path):
          has_changes = False
      try:
        res = subprocess.call(['git', '-C', path, 'checkout', '--quiet', ref])
        if res != 0:
          print('  unable to check out {}'.format(ref))
      finally:
        if has_changes:
          subprocess.check_call(['git', '-C', path, 'stash', 'pop', '--quiet'])

  def handle_add(self):
    if not self.args.path:
      # Determine the directory to create the sub repository in from
      # the repository URL.
      if '\\' in self.args.repository and os.name == 'nt':
        self.args.path = os.path.basename(self.args.repository)
      else:
        self.args.path = posixpath.basename(urlparse(self.args.repository).path)
      if self.args.path.endswith('.git'):
        self.args.path = self.args.path[:-4]

    if self.path in self.config:
      self.fatal('subrepo {} already exists'.format(self.args.path))

    self.config[self.path] = repo = {'url': self.args.repository, 'ref': None}
    res = self.handle_update()
    if res not in (0, None):
      return res

    self.restore_worktree(self.path, self.args.branch)

    cmd = ['git', '-C', self.path, 'rev-parse', 'HEAD']
    repo['ref'] = subprocess.check_output(cmd).decode().strip()

    if self.args.recursive:
      cmd = ['git', '-C', self.path, 'submodule', 'update', '--init']
      subprocess.call(cmd)
      self.config[self.path]['recursive'] = True

    if self.args.stage:
      self.args.all = False
      self.handle_stage()

    write_config(self.config)

  def handle_rename(self):
    old = self.get_path(self.args.old)
    new = self.get_path(self.args.new)
    if old not in self.config:
      self.fatal('{} is not a sub repository'.format(old))
    if new in self.config:
      self.fatal('{} is already a sub repository'.format(new))

    cmd = ['git', 'mv', old, new]
    res = subprocess.call(cmd)
    if res != 0:
      return res

    self.config[new] = self.config.pop(old)
    write_config(self.config)

    cmd = ['git', 'add', CONFIG_FILENAME]
    res = subprocess.call(cmd)
    if res != 0:
      self.fatal('unabled to stage {}'.format(CONFIG_FILENAME))

  def handle_update(self):
    if self.path and self.path not in self.config:
      self.fatal('{} is not a subrepo'.format(self.args.path))
    if self.path:
      paths = [self.path]
    else:
      paths = self.config.keys()

    for path in paths:
      repo = self.config[path]
      bare_path = os.path.join('.git', 'subrepos', path)
      if not os.path.isdir(bare_path):
        print('Cloning {} ...'.format(path))
        cmd = ['git', 'clone', '--bare', repo['url'], bare_path, '--quiet']
        res = subprocess.call(cmd)
        if res != 0:
          return res
      else:
        print('Fetching {} ...'.format(path))
        cmd = ['git', 'fetch', '--quiet']
        res = subprocess.call(cmd, cwd=bare_path)
        if res != 0:
          return res
      self.restore_worktree(path, repo['ref'])
      print()

  def handle_rm(self):
    if self.path not in self.config:
      self.fatal('{} is not a subrepo'.format(self.args.path))
      return 1
    del self.config[self.path]

    bare_path = os.path.join('.git', 'subrepos', self.path)
    if os.path.exists(bare_path):
      shutil.rmtree(bare_path, onerror=rmtree_onerror_retry_remove)
    if os.path.exists(self.path):
      shutil.rmtree(self.path)

    write_config(self.config)

  def handle_stage(self):
    if self.args.all:
      paths = self.config.keys()
    else:
      if not self.args.path:
        self.fatal('specify --all or the path to a sub repository')
      paths = [self.path]

    for path in paths:
      cmd = ['git', '-C', path, 'rev-parse', 'HEAD']
      ref = subprocess.check_output(cmd).decode().strip()
      if path not in self.config:
        cmd = ['git', '-C', path, 'remote', 'get-url', 'origin']
        url = subprocess.check_output(cmd).decode().strip()
        print('Now tracking sub repository "{}"'.format(path))
        self.config[path] = {'url': url, 'ref': ref}
      else:
        self.config[path]['ref'] = ref
      write_config(self.config)

      # We need to remove the worktree file temporarily, otherwise Git
      # will add ony a reference to the repository instead of all its files.
      git_file = os.path.join(path, '.git')
      if os.path.isfile(git_file):
        os.remove(git_file)
      try:
        cmd = ['git', 'add', path, CONFIG_FILENAME]
        res = subprocess.call(cmd)
        if res != 0:
          if self.args.all:
            print('error: unable to stage', path)
          else:
            return res
      finally:
        self.restore_worktree(path, None)

  def handle_list(self):
    for path, repo in self.config.items():
      print('{} ({}@{})'.format(path, repo['url'], repo['ref']))

  def handle_prune(self):
    path = '.git/subrepos'
    if os.path.isdir(path):
      shutil.rmtree(path, onerror=rmtree_onerror_retry_remove)
    for path in self.config.keys():
      git_file = os.path.join(path, '.git')
      if os.path.isfile(git_file):
        os.remove(git_file)

  def handle_convert_module(self):
    if not self.args.path and not self.args.all:
      self.parser.error('expected --all option or path argument')

    modules = read_gitmodules()
    if self.args.all:
      paths = modules.keys()
    else:
      if self.path not in modules:
        self.fatal('{} is not a Git submodule'.format(self.args.path))
      paths = [self.path]

    refs = {}
    for line in subprocess.check_output(['git', 'submodule']).decode().split('\n'):
      line = line.strip()
      if not line: break
      ref, path = line.split(' ')[:2]
      if path not in modules:
        print('warning: submodule not in .gitmodules:', path)
        continue
      refs[path] = ref.lstrip('-')

    for path in list(paths):
      if path not in refs:
        print('warning: submodule has no ref in this repository:', path)
        paths.remove(path)

    if not paths:
      return 0
    if not self.args.yes:
      print('the following Git submodules will be replaced by sub repositories:')
      for path in paths:
        print('  ', path)
      print()
      reply = input('do you want to continue? [N/y] ').strip().lower()
      if not reply or reply not in 'yes':
        return 0

    for path in paths:
      print()
      cmd = ['git', 'submodule', 'deinit', '-f', '--', path]
      res = subprocess.call(cmd)
      if res != 0:
        print('error: unable to deinit', path)
        continue
      repo_path = os.path.normpath(os.path.join('.git', 'modules', path))
      if os.path.isdir(repo_path):
        try:
          shutil.rmtree(repo_path, onerror=rmtree_onerror_retry_remove)
        except (OSError, IOError) as exc:
          print('warning: unable to remove', repo_path)
      cmd = ['git', 'rm', '-f', path]
      res = subprocess.call(cmd)
      if res != 0:
        print('error: unable to remove', path)
        continue

      self.prefix = ''
      self.args.path = path
      self.args.repository = modules[path]['url']
      self.args.branch = refs[path]
      self.handle_add()


def main(args=None, prog=None):
  """
  Create working trees of other Git repositories and track them in your
  parent repository.
  """

  Subrepo().main(args, prog)


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  sys.exit(main())
