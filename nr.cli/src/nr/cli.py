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

import argparse
import pkg_resources
import sys

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.2'

ENTRYPOINT_GROUP = 'nr.cli:commands'


def main(argv=None, prog=None):
  parser = argparse.ArgumentParser()
  parser.add_argument('command', nargs='?')
  args, argv = parser.parse_known_args()

  if not args.command:
    for ep in pkg_resources.iter_entry_points(ENTRYPOINT_GROUP):
      print(ep.name)
    sys.exit(0)

  ep = next(pkg_resources.iter_entry_points(ENTRYPOINT_GROUP, args.command), None)
  if not ep:
    parser.error('unknown command "{}"'.format(args.command))

  function = ep.load()
  sys.exit(function(argv, '{} {}'.format(prog, argv[0])))
