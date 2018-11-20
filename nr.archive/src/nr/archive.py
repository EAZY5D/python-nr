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

"""
This module provides an abstraction for archive files guides by the #tarfile
interfact. It allows you to access .zip, .tar, .tar.gz, .tar.bz2 and .tar.xz
files using the same interface. It also allows you to register your own opener.
"""

from functools import partial
import datetime
import os
import shutil
import sys
import tarfile
import time
import zipfile

try:
  import builtins
except ImportError:
  import __builtin__ as builtins

openers = {}


def register_opener(suffix, opener=None):
  """
  Register a callback that opens an archive with the specified *suffix*.
  The object returned by the *opener* must implement the #tarfile.Tarfile
  interface, more specifically the following methods:

  - `add(filename, arcname) -> None`
  - `getnames() -> list of str`
  - `getmember(filename) -> TarInfo`
  - `extractfile(filename) -> file obj`

  This function can be used as a decorator when *opener* is not provided.

  The opener must accept the following arguments:

  %%arglist
  file (file-like): A file-like object to read the archive data from.
  mode (str): The mode to open the file in. Valid values are
    `'w'`, `'r'` and `'a'`.
  options (dict): A dictionary with possibly additional arguments.
  """

  if opener is None:
    def decorator(func):
      register_opener(suffix, func)
      return func
    return decorator
  if suffix in openers:
    raise ValueError('opener suffix {0!r} already registered'.format(suffix))
  openers[suffix] = opener


def get_opener(filename):
  """
  Finds a matching opener that is registed with :func:`register_opener`
  and returns a tuple ``(suffix, opener)``. If there is no opener that
  can handle this filename, :class:`UnknownArchive` is raised.
  """

  for suffix, opener in openers.items():
    if filename.endswith(suffix):
      return suffix, opener
  raise UnknownArchive(filename)


def open(filename=None, file=None, mode='r', suffix=None, options=None):
  """
  Opens the archive at the specified *filename* or from the file-like
  object *file* using the appropriate opener. A specific opener can be
  specified by passing the *suffix* argument.

  # Parameters
  filename (str): A filename to open the archive from.
  file (file-like): A file-like object as source/destination.
  mode (str): The mode to open the archive in.
  suffix (str): Possible override for the *filename* suffix. Must be
    specified when *file* is passed instead of *filename*.
  options (dict): A dictionary that will be passed to the opener
    with which additional options can be specified.
  return (archive-like): An object that represents the archive and follows
    the interface of the #tarfile.TarFile class.
  """

  if mode not in ('r', 'w', 'a'):
    raise ValueError("invalid mode: {0!r}".format(mode))

  if suffix is None:
    suffix, opener = get_opener(filename)
    if file is not None:
      filename = None  # We don't need it anymore.
  else:
    if file is not None and filename is not None:
      raise ValueError("filename must not be set with file & suffix specified")
    try:
      opener = openers[suffix]
    except KeyError:
      raise UnknownArchive(suffix)

  if options is None:
    options = {}

  if file is not None:
    if mode in 'wa' and not hasattr(file, 'write'):
      raise TypeError("file.write() does not exist", file)
    if mode == 'r' and not hasattr(file, 'read'):
      raise TypeError("file.read() does not exist", file)

  if [filename, file].count(None) != 1:
    raise ValueError("either filename or file must be specified")
  if filename is not None:
    file = builtins.open(filename, mode + 'b')

  try:
    return opener(file, mode, options)
  except:
    if filename is not None:
      file.close()
    raise


def extract(archive, directory, suffix=None, unpack_single_dir=False,
    check_extract_file=None, progress_callback=None, default_mode='755'):
  """
  Extract the contents of *archive* to the specified *directory*. This
  function ensures that no file is extracted outside of the target directory
  (which can theoretically happen if the arcname is not relative or points
  to a parent directory).

  # Parameters
  archive (str, archive-like): The filename of an archive or an already
    opened archive.
  directory (str): Path to the directory to unpack the contents to.
  unpack_single_dir (bool): If this is True and if the archive contains only
    a single top-level directory, its contents will be placed directly into
    the target *directory*.
  """

  if isinstance(archive, str):
    with open(archive, suffix=suffix) as archive:
      return extract(archive, directory, None, unpack_single_dir,
          check_extract_file, progress_callback, default_mode)

  if isinstance(default_mode, str):
    default_mode = int(default_mode, 8)

  if progress_callback:
    progress_callback(-1, 0, None)
  names = archive.getnames()

  # Find out if we have only one top-level directory.
  toplevel_dirs = set()
  for name in names:
    parts = name.split('/')
    if len(parts) > 1:
      toplevel_dirs.add(parts[0])
  if unpack_single_dir and len(toplevel_dirs) == 1:
    stripdir = next(iter(toplevel_dirs)) + '/'
  else:
    stripdir = None

  for index, name in enumerate(names):
    if progress_callback:
      progress_callback(index + 1, len(names), name)
    if name.startswith('..') or name.startswith('/') or os.path.isabs(name):
      continue
    if check_extract_file and not check_extract_file(name):
      continue
    if name.endswith('/'):
      continue
    if stripdir:
      filename = name[len(stripdir):]
      if not filename:
        continue
    else:
      filename = name

    info = archive.getmember(name)
    src = archive.extractfile(name)
    if not src:
      continue

    try:
      filename = os.path.join(directory, filename)
      dirname = os.path.dirname(filename)
      if not os.path.exists(dirname):
        os.makedirs(dirname)
      with builtins.open(filename, 'wb') as dst:
        shutil.copyfileobj(src, dst)
      os.chmod(filename, info.mode or default_mode)
      os.utime(filename, (-1, info.mtime))
    finally:
      src.close()

  if progress_callback:
    progress_callback(len(names), len(names), None)


class Error(Exception):
  pass


class UnknownArchive(Exception):
  pass


def _zip_opener(file, mode, options):
  compression = options.get('compression', zipfile.ZIP_DEFLATED)
  if compression == 'deflated':
    compression = zipfile.ZIP_DEFLATED
  elif compression == 'stored':
    compression = zipfile.ZIP_STORED
  elif compression == 'bzip2':
    compression = zipfile.ZIP_BZIP2
  elif compression == 'lzma':
    compression = zipfile.ZIP_LZMA

  def _getmember(name):
    zinfo = obj.getinfo(name)
    tinfo = tarfile.TarInfo(name)
    tinfo.mode = zinfo.external_attr >> 16 & 511  # http://stackoverflow.com/a/434689/791713
    tinfo.mtime = time.mktime(datetime.datetime(*zinfo.date_time).timetuple())
    return tinfo

  obj = zipfile.ZipFile(file, mode, compression)
  obj.add = obj.write
  obj.getnames = obj.namelist
  obj.extractfile = obj.open
  obj.getmember = _getmember
  return obj


def _tar_opener(file, mode, options, _tar_mode):
  kwargs = {'bufsize': options['bufsize']} if 'bufsize' in options else {}
  return tarfile.open(fileobj=file, mode='%s:%s' % (mode, _tar_mode), **kwargs)


register_opener('.zip', _zip_opener)
register_opener('.tar', partial(_tar_opener, _tar_mode=''))
register_opener('.tar.gz', partial(_tar_opener, _tar_mode='gz'))
register_opener('.tar.bz2', partial(_tar_opener, _tar_mode='bz2'))
register_opener('.tar.xz', partial(_tar_opener, _tar_mode='xz'))


def main(argv=None, prog=None):
  """
  Archive abstraction with implementations for ZIP and TAR files.
  """

  import argparse
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('filename', help='Name of the archive.')
  parser.add_argument('-e', '--extract', help='Extract the archive to the '
    'specified directory.')
  parser.add_argument('-s', '--single-unpack', action='store_true',
    help='Skip over the top directory in the archive if it is the only '
      'member in the archive root directory.')
  args = parser.parse_args(argv)

  if args.extract:
    extract(args.filename, args.extract, unpack_single_dir=args.single_unpack)
    return 0
  else:
    parser.error('no operation specified')


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  sys.exit(main())
