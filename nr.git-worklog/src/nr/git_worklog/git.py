# Copyright (c) 2017  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from datetime import datetime
import collections
import io
import os
import time
import subprocess
import sys

_OutputTuple = collections.namedtuple('_OutputTuple', 'out err')
_OutputCodeTuple = collections.namedtuple('_OutputTuple', 'out err code')
CalledProcessError = subprocess.CalledProcessError

if sys.version_info[0] == 2:
  _text_type = unicode
  _binary_type = str
elif sys.version_info[0] == 3:
  _text_type = str
  _binary_type = bytes


def enc(text, encoding='utf-8'):
  if isinstance(text, _text_type):
    return text.encode(encoding)
  return text


def dec(text, encoding='utf-8'):
  if isinstance(text, _binary_type):
    return text.decode(encoding)
  return text


def run(cmd, *args, input=None, pipe=True, merge_err=True, check=True, **kwargs):
  """
  Uses #subprocess.Popen() to create a process and wait for its completeion.
  Returns a tuple of (stdout, stderr). If *merge_err* is True and the *stderr*
  keyword argument is not specified, the standard error stream will be directed
  into the standard output stream and the returned *stderr* value will be #None.

  If the process returns a non-zero exit-code, a #CalledProcessError will be
  raised, unless *check* is set to #False. Note that in this case, the returned
  tuple will contain three elements, with the third being the exit-code.

  If *pipe* is set to #False, both returned *stdout* and *stderr* values will
  be #None.
  """

  if input is not None:
    if isinstance(input, type(subprocess.PIPE)):
      stdin = input
      input = b''
    else:
      stdin = subprocess.PIPE
  else:
    stdin = None

  kwargs['stdin'] = stdin
  proc = globals()['pipe'](cmd, *args, pipe=pipe, merge_err=merge_err, **kwargs)
  if input:
    proc.stdin.write(input)

  dout, derr = proc.communicate()
  if check and proc.returncode != 0:
    raise CalledProcessError(proc.returncode, cmd, dout, derr)
  elif check:
    return _OutputTuple(dout, derr)
  else:
    return _OutputCodeTuple(dout, derr, proc.returncode)


def pipe(cmd, *args, pipe=True, pipe_stdin=True, merge_err=True, **kwargs):
  """
  Shorthand to create a #subprocess.Popen object.
  """

  stdout = subprocess.PIPE if pipe else None
  stderr = kwargs.pop('stderr', subprocess.STDOUT if merge_err else stdout)
  return subprocess.Popen(cmd, *args, stdout=stdout, stderr=stderr, **kwargs)


def dir(cwd=None, fatal=False, *, __cache={}):
  """
  Returns the current Git directory. If *fatal* is True, will print an error
  message and exit with 128 if not inside a Git repository directory.
  """

  cwd = cwd or os.getcwd()
  if cwd in __cache:
    return __cache[cwd]

  git_dir = os.getenv('GIT_DIR')
  if git_dir:
    return git_dir

  parent = cwd
  home = os.path.expanduser('~')
  while parent:
    if parent == home: break
    git_dir = os.path.join(parent, '.git')
    if os.path.isdir(git_dir):
      __cache[cwd] = git_dir
      return git_dir
    elif os.path.isfile(git_dir):
      with open(git_dir) as fp:
        line = fp.readline()
      if not line.startswith('gitdir:'):
        raise ValueError('invalid .git file encountered: {!r}'.format(git_dir))
      git_dir = os.path.normpath(os.path.join(parent, line[7:].strip()))
      __cache[cwd] = git_dir
      return git_dir
    new_parent = os.path.dirname(parent)
    if new_parent == parent:
      break
    parent = new_parent

  if fatal:
    print('fatal: Not a git repository (or any of the parent directories): .git', file=sys.stderr)
    sys.exit(128)

  return None


def config(key, value=None, g=False):
  """
  Returns a Git configuration value or writes one.
  """

  cmd = ['git', 'config']
  if g:
    cmd.append('--global')
  cmd.append(key)
  if value is not None:
    cmd.append(value)

  try:
    return dec(run(cmd).out).strip()
  except CalledProcessError as exc:
    if exc.returncode == 1:
      return u''
    raise


def show(*args, cwd=None):
  try:
    return dec(run(['git', 'show'] + list(args), cwd=cwd).out).strip()
  except CalledProcessError as exc:
    if exc.returncode == 128:
      raise DoesNotExist(dec(exc.output))
    raise


def rev_parse(*args):
  """
  Wrapper for `git rev-parse`. Returns #None when "needed a single revision"
  error would be returned by Git.
  """

  # TODO: Of course, this only works with an English Git version.

  try:
    return dec(run(['git', 'rev-parse'] + list(args)).out).strip()
  except CalledProcessError as exc:
    if u'needed a single revision' in dec(exc.output).lower():
      return None
    elif u'bad revision' in dec(exc.output).lower():
      return None
    raise


def fast_import(commit, date_format=None, quiet=False, cwd=None):
  cmd = ['git', 'fast-import']
  if date_format:
    cmd.append('--date-format=' + date_format)
  if quiet:
    cmd.append('--quiet')
  try:
    return run(cmd, input=commit, cwd=cwd)
  except CalledProcessError as exc:
    raise


def current_ref():
  """
  Returns the current Git ref.
  """

  output = dec(run(['git', 'show-ref', '--heads', '--abbrev']).out)
  return output.strip().split()[-1]


def has_branch(branch):
  """
  Returns #True if the current repository has a local branch *branch*.
  """

  cmd = ['git', 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch]
  return run(cmd, check=False).code == 0


def is_inside_work_tree(directory=None):
  """
  Returns #True if *directory* is inside a Git repository.
  """

  if directory is None:
    directory = os.getcwd()
  cmd = ['git', 'rev-parse', '--is-inside-work-tree']
  return run(cmd, cwd=directory, check=False).code == 0


class DoesNotExist(Exception):
  pass


class Commit(object):
  """
  Helper class to format a Git commit to a binary file-like object.

  !!!note
      A lot of this code has been taken from the [MkDocs] source.

  [MkDocs]: https://github.com/mkdocs/mkdocs/blob/master/mkdocs/utils/ghp_import.py
  """

  def __init__(self, fp=None):
    self.fp = fp or io.BytesIO()

  def head(self, branch, message, uname=None, email=None, time=None):
    if time is None: time = datetime.now()
    if uname is None: uname = config('user.name')
    if email is None: email = config('user.email')

    self.fp.write(enc('commit refs/heads/{}\n'.format(branch)))
    self.fp.write(enc('committer {} <{}> {}\n'.format(uname, email, mk_when(time))))
    self.fp.write(enc('data {}\n{}\n'.format(len(message), message)))
    head = rev_parse(branch, '--')
    if head:
      head = head.split()[0]
      self.fp.write(enc('from {}\n'.format(head)))
    self.fp.write(enc('deleteall\n'))

  def add_file(self, srcpath, dstpath, mode=None):
    if mode is None:
      mode = '100755' if os.access(srcpath, os.X_OK) else '100644'
    else:
      mode = str(mode)
      if len(mode) != 6:
        raise ValueError('invalid mode {!r}'.format(mode))
    with open(srcpath, 'rb') as fp:
      return self.add_file_contents(fp.read(), dstpath, mode)

  def add_file_contents(self, data, dstpath, mode='100644'):
    self.fp.write(enc('M {} inline {}\n'.format(mode, dstpath)))
    self.fp.write(enc('data {}\n'.format(len(data))))  # TODO: Length of the encoded data, rather?
    self.fp.write(enc(data))
    self.fp.write(enc('\n'))

  def getvalue(self):
    return self.fp.getvalue()


def mk_when(timestamp=None):
  if timestamp is None:
    timestamp = int(time.time())
  elif not isinstance(timestamp, (int, float)):
    timestamp = int((timestamp - datetime(1970, 1, 1)).total_seconds())
  else:
    timestamp = int(timestamp)
  currtz = "%+05d" % (-1 * time.timezone / 36)  # / 3600 * 100
  return "%s %s" % (timestamp, currtz)

