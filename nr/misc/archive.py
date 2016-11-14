# Copyright (c) 2016  Niklas Rosenstein
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

import builtins
import os
import shutil
import tarfile
import zipfile
from functools import partial

openers = {}

def register_opener(suffix, opener=None):
  """
  Register a callback that opens an archive with the specified *suffix*.
  The object returned by the *opener* must implement the
  :class:`tarfile.Tarfile` interface.

  This function can be used as a decorator when *opener* is None.

  The opener must accept the following arguments:

  :param file: A file-like object to read the archive data from.
  :param mode: The mode to open the file in. Valid values are `'w'`,
    `'r'` and `'a'`.
  :param options: A dictionary with possibly additional arguments.
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
  object *file* using the appropriate opener. A specific opener can
  be specified by passing the *suffix* argument.

  :param filename: A filename to open the archive from.
  :param file: A file-like object as source/destination.
  :param mode: The mode to open the archive in.
  :param suffix: Possible override for the *filename* suffix. Must be
    specified when *file* is passed instead of *filename*.
  :param options: A dictionary that will be passed to the opener
    with which additional options can be specified.
  :return: An object that represents the archive and follows the
    interface of the :class:`tarfile.TarFile` class.
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

def extract(archive, directory, unpack_single_dir=False):
  """
  Extract the contents of *archive* to the specified *directory*. This
  function ensures that no file is extracted outside of the target directory
  (which can theoretically happen if the arcname is not relative or points
  to a parent directory).

  :param archive: The filename of an archive or an already opened archive.
  :param directory: Path to the directory to unpack the contents to.
  :param unpack_single_dir: If this is True and if the archive contains only
    a single top-level directory, its contents will be placed directly into
    the target *directory*.
  """

  if isinstance(archive, str):
    with open(archive) as archive:
      return extract(archive, directory, unpack_single_dir)

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

  for name in names:
    if name.startswith('..') or name.startswith('/') or os.path.isabs(name):
      continue
    if name.endswith('/'):
      continue
    if stripdir:
      filename = name[len(stripdir):]
      if not filename:
        continue
    else:
      filename = name

    src = archive.extractfile(name)
    if not src:
      continue

    # TODO: Also extract file metadata.

    try:
      filename = os.path.join(directory, filename)
      dirname = os.path.dirname(filename)
      if not os.path.exists(dirname):
        os.makedirs(dirname)
      with builtins.open(filename, 'wb') as dst:
        shutil.copyfileobj(src, dst)
    finally:
      src.close()

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

  obj = zipfile.ZipFile(file, mode, compression)
  obj.add = obj.write
  obj.getnames = obj.namelist
  obj.extractfile = obj.open
  return obj

def _tar_opener(file, mode, options, _tar_mode):
  kwargs = {'bufsize': options['bufsize']} if 'bufsize' in options else {}
  return tarfile.open(fileobj=file, mode='%s:%s' % (mode, _tar_mode), **kwargs)

register_opener('.zip', _zip_opener)
register_opener('.tar', partial(_tar_opener, _tar_mode=''))
register_opener('.tar.gz', partial(_tar_opener, _tar_mode='gz'))
register_opener('.tar.bz2', partial(_tar_opener, _tar_mode='bz2'))
register_opener('.tar.xz', partial(_tar_opener, _tar_mode='xz'))
