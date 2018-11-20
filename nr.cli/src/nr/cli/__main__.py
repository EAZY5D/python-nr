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
__version__ = '1.0.1'

import argparse
import nr
import os
import pkgutil
import sys
import textwrap


def import_module(name):
  module = __import__(name)
  for part in name.split('.')[1:]:
    module = getattr(module, part)
  return module


def prepare_docstring(s, width, init_indent, indent):
  s = textwrap.dedent(s).strip()
  lines = []
  for line in s.split('\n'):
    if not line and lines: break
    lines.append(line)
  lines = textwrap.wrap(' '.join(lines), width)
  for i, line in enumerate(lines):
    lines[i] = (' ' * (init_indent if i == 0 else indent)) + line
  return '\n'.join(lines)


def main(argv=None, prog=None):
  commands = {}
  for info in pkgutil.walk_packages(nr.__path__, 'nr.'):
    if info.name == 'nr.cli.__main__': continue
    try:
      module = import_module(info.name + '.main')
    except ImportError:
      module = import_module(info.name)
    if hasattr(module, 'main'):
      parts = info.name.split('.')[1:]
      if parts[-1] == 'main':
        parts.pop()
      name = '-'.join(parts).replace('_', '-')
      commands[name] = module.main

  if argv is None:
    argv = sys.argv[1:]
  if prog is None:
    prog = os.path.basename(os.path.splitext(sys.argv[0])[0])

  do_help = argv and argv[0] in ('-h', '--help')
  do_usage = do_help or not argv
  do_list_packages = argv and argv[0] in ('-l' ,'--list-packages')

  if do_usage:
    print('usage: nr [-h] [-l] [COMMAND [ARGS...]')
    print()
  if do_help:
    print('options:')
    print('  -h, --help   display this help message')
    print('  -l, --list-packages')
    print('               display a list of packages that may contain additional')
    print('               command-line tools and can be installed via Pip.')
    if commands:
      print()
      print('commands:')
      maxlength = max(map(len, commands.keys()))
    for command, fun in sorted(commands.items(), key=lambda x: x[0]):
      line = command + ' ' * (maxlength - len(command))
      if fun.__doc__:
        line += '  ' + prepare_docstring(fun.__doc__, 79-len(command), 0, maxlength+4)
      print('  {}'.format(line))
    print()
  if do_help or do_usage:
    return 0

  if do_list_packages:
    from xml.dom import minidom
    try: from urllib import request as urllib
    except ImportError: import urllib2 as urllib
    doc = minidom.parse(urllib.urlopen('https://pypi.org/simple'))
    results = doc.getElementsByTagName('a')
    for a in results:
      name = a.firstChild.nodeValue
      if name.startswith('nr.'):
        print(name)
    if not results:
      print('no packages matching nr.* found on PyPI.', file=sys.stderr)
    return

  if argv[0] not in commands:
    print('fatal: unknown command "{}"'.format(argv[0]), file=sys.stderr)
    return 1

  return commands[argv[0]](argv[1:], '{} {}'.format(prog, argv[0]))


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  _entry_point()
