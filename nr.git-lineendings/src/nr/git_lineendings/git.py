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

import re
import subprocess


class DoesNotExist(ValueError):
  pass


def parents(rev):
  " Returns a list of the parent commit IDs. "
  rev = rev_parse(rev)
  args = ['git', 'rev-list', '--parents', '-n', '1', rev]
  output = subprocess.check_output(args, stderr=subprocess.PIPE).decode()
  items = output.split()
  return items[1:]


def get_file(rev, file):
  " Returns the a file at the specified revision as binary string. "
  args = ['git', 'show', '{}:{}'.format(rev, file)]
  try:
    return subprocess.check_output(args, stderr=subprocess.PIPE)
  except subprocess.CalledProcessError as e:
    if e.returncode == 128:
      raise DoesNotExist(e.stderr.decode().strip())
    raise


def rev_parse(rev, short=False):
  " Returns the short form of a revisions commit ID. "
  args = ['git', 'rev-parse', rev]
  output = subprocess.check_output(args, stderr=subprocess.PIPE)
  result = output.decode().strip()
  if short:
    result = result[:10]
  return result


def rev_list(rev, *args):
  args = ['git', 'rev-list'] + list(args) + [rev]
  proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
  while True:
    line = proc.stdout.readline().strip()
    if not line: break
    yield line.decode('ascii')
  _, stderr = proc.communicate()
  if proc.returncode != 0:
    raise subprocess.CalledProcessError(proc.returncode, args, _, stderr)


def branches(all=False, merged_into=None):
  " Returns a list of branches in the repository. "
  if merged_into:
    args = ['git', 'branch', '--merged', merged_into]
    output = subprocess.check_output(args, stderr=subprocess.PIPE).decode()
    return output.split()
  else:
    args = ['git', 'branch']
    if all:
      args += ['-a']
    result = []
    output = subprocess.check_output(args, stderr=subprocess.PIPE).decode()
    for line in output.split('\n'):
      parts = line.split()
      if not parts: continue
      if parts[0] == '*': parts.pop(0)
      result.append(parts[0].strip())
    return result


def config(key, value=None, global_=False):
  args = ['git', 'config']
  if global_: args.append('--global')
  args.append(key)
  if value: args.append(value)
  return subprocess.check_output(args, stderr=subprocess.PIPE).decode().strip()
