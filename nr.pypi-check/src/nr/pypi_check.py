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
import os
import re
import sys
import types


def load_setup_from_string(s, filename):
  """
  Loads the information of a setup script by executing it in an environment
  where the distutils and setuptools modules are hooked.
  """

  import distutils
  import setuptools

  modules = sys.modules.copy()

  setuptools_mock = types.ModuleType('setuptools')
  vars(setuptools_mock).update(vars(setuptools))
  setuptools_vars = {}
  setuptools_mock.setup = lambda **kw: setuptools_vars.update(kw)
  sys.modules['setuptools'] = setuptools_mock

  distutils_mock = types.ModuleType('distutils')
  vars(distutils_mock).update(vars(distutils))
  distutils_vars = {}
  distutils_mock.setup = lambda **kw: distutils_vars.update(kw)
  sys.modules['distutils'] = distutils_mock

  try:
    exec(compile(s, filename, 'exec'), {})
  finally:
    sys.modules.clear()
    sys.modules.update(modules)

  if setuptools_vars:
    return 'setuptools', setuptools_vars
  elif distutils_vars:
    return 'distutils', distutils_vars
  else:
    raise RuntimeError('setup() not called')


class ProjectCheck(object):
  """
  Base class for project checks.
  """

  options = {}

  def do_check(self, options):
    pass


class BasicProjectChecks(ProjectCheck):
  """
  Implements the basic project checks.
  """

  options = {
    "setup": "Warn if there is no setup script (default on).",
    "setup-fields": "Warn if important fields are missing in your setup script. (default on)",
    "setup-setuptools": "Warn if your setup script does not use setuptools, but distutils for example. (default on)",
    "manifest": "Warn if your project should have a MANIFEST.in file or if it misses some files. (default on)",
    "license": "Warn if your project has no license file.",
    "package-meta": "Warn if your package or module is missing meta information. (default on)",
    "version-match": "Warn if your package or module's __version__ is different from the versioin in your setup script. (default on)",
    "changelog": "Warn if there is no changelog file or changelog section in the readme. (default on)",
    "changelog-release-date": "Warn if there is no release date in the changelog for the current version. (default on)"
  }

  def do_check(self, options):
    if os.path.isfile('setup.py'):
      with open('setup.py') as fp:
        setup_contents = fp.read()
    else:
      setup_contents = ''

    if options.get('setup', True) and not setup_contents:
      yield 'setup.py: File is missing'
    if setup_contents:
      # Run the setup script in an environment where we hook the distutils
      # and setuptools module to figure out the parameters it receives.
      setup_lib, setup_data = load_setup_from_string(setup_contents, 'setup.py')
      setup_version = setup_data.get('version')

      if options.get('setup-fields', True):
        if not re.match('^[\d\.]+(.(a|b|rc|post)\d*)?$', setup_data.get('version', '')):
          yield 'setup.py: Invalid or no version.'
        if not setup_data.get('author'):
          yield 'setup.py: No author specified.'
        if not setup_data.get('author_email'):
          yield 'setup.py: No author_email specified.'
        if not setup_data.get('url'):
          yield 'setup.py: No url specified.'
        if not setup_data.get('license'):
          yield 'setup.py: No license specified.'
      if options.get('setup-distutils', True) and setup_lib != 'setuptools':
        yield 'setup.py: Your setup script should use setuptools instead of {}'.format(setup_lib)
    else:
      setup_data = None

    # Check files available in the project.
    files = {'readme': None, 'license': None, 'requirements': None}
    for filename in ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'LICENSE.rst']:
      if os.path.isfile(filename):
        files['license'] = filename
        break
    for filename in ['README', 'README.txt', 'README.md', 'README.rst']:
      if os.path.isfile(filename):
        files['readme'] = filename
        break
    if os.path.isfile('requirements.txt'):
      files['requirements'] = 'requirements.txt'

    if options.get('manifest', True) and files:
      if not os.path.isfile('MANIFEST.in'):
        yield 'MANIFEST.in: File missing.'
        manifest_contents = ''
      else:
        with open('MANIFEST.in') as fp:
          manifest_contents = fp.read()
      includes_files = []
      for line in manifest_contents.split('\n'):
        if line.startswith('include'):
          includes_files.append(line[7:].strip())
      for filename in files.values():
        if filename is not None and filename not in includes_files:
          yield 'MANIFEST.in: {} should be included.'.format(filename)

    if options.get('license', True) and not files['license']:
      yield 'LICENSE: File missing.'

    if options.get('setup', True) and setup_contents:
      if files['readme'] and files['readme'] not in setup_contents:
        yield 'setup.py: It appears you are not reading {} in your setup script.'.format(files['readme'])
      elif setup_data is not None:
        ext = os.path.splitext(files['readme'])[1]
        if not ext or ext == '.txt': ect = 'text/plain'
        elif ext == '.md': ect = 'text/markdown'
        else: ect = 'text/x-rst'
        ct = setup_data.get('long_description_content_type', 'text/x-rst')
        if ct != ect:
          yield 'setup.py: long_description_content_type expected value is {}, got {}'.format(ect, ct)
      if files['requirements'] and files['requirements'] not in setup_contents:
        yield 'setup.py: It appears you are not reading {} in your setup script.'.format(files['requirements'])

    # TODO: package-meta, version-match, changelog, changelog-release-date


def get_all_options():
  options = {}
  for cls in ProjectCheck.__subclasses__():
    options.update(cls.options)
  return options


def get_argument_parser(prog):
  parser = argparse.ArgumentParser(prog, add_help=False)
  parser.add_argument('-h', '--help', action='store_true')
  for key, value in get_all_options().items():
    dest = key.replace('-', '_')
    parser.add_argument('-w' + key, default=None, action='store_true', dest=dest)
    parser.add_argument('-wno-' + key, action='store_false', dest=dest)
  return parser


def main(argv=None, prog=None):
  """
  Check your Python package before submitting it to PyPI.
  """

  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  if args.help:
    print('usage: {} [-h] [OPTIONS ...]'.format(parser.prog))
    print()
    print('  Checks can be turned off with the respective -wno-{option} flag.')
    print()
    print('options:')
    options = get_all_options()
    width = max(map(len, options.keys())) + 3
    for key, value in sorted(options.items(), key=lambda x: x[0]):
      print('  -w{} {}'.format(key.ljust(width), value))
    return 0

  options = {k: v for k, v in vars(args).items() if v is not None}
  for cls in ProjectCheck.__subclasses__():
    for warning in cls().do_check(options):
      print(warning)


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  sys.exit(main())
