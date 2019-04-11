# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
This module provides an alternative interface to handling filesystem path and
adds a lot of additional functionality.
"""

__all__ = [
  # from os import
  'sep', 'pathsep', 'curdir', 'pardir', 'cwd', 'listdir',
  # from os.path import
  'expanduser', 'norm', 'isabs', 'isfile', 'isdir', 'exists', 'join', 'split',
  'dir', 'base', 'getatime', 'getmtime', 'splitdrive',
  # local definitions
  'canonical', 'abs', 'rel', 'isfile_cs', 'isrel', 'issub', 'isglob', 'glob', 'addtobase',
  'addprefix', 'addsuffix', 'setsuffix', 'rmvsuffix', 'getsuffix', 'makedirs',
  'chmod_update', 'chmod_repr', 'chmod', 'compare_timestamp',
  'compare_all_timestamps', 'fixcase',
]

import ctypes
import errno
import functools
import operator
import os
import platform
import stat as _stat

from os import (
  sep,
  pathsep,
  curdir,
  pardir,
  getcwd as cwd
)
from os.path import (
  expanduser,
  normpath as norm,
  isabs,
  isfile,
  isdir,
  exists,
  join,
  split,
  dirname as dir,
  basename as base,
  getatime,
  getmtime,
  splitdrive
)

try:
  import glob2
except ImportError as exc:
  glob2 = None
  glob2_exc = exc
  del exc


is_case_sensitive = not (os.name == 'nt' or 'windows' in platform.platform().lower())


def canonical(path, parent=None):
  """
  Returns the canonical version of *path*, that is the common and fully
  normalized representation. On case-sensitive file systems, this will also
  correct the case of the path if the file already exists.
  """

  path = norm(abs(path, parent))
  if not is_case_sensitive:
    path = fixcase(path)
  return path


def abs(path, parent=None):
  if not isabs(path):
    return join(parent or cwd(), path)
  return path


def rel(path, parent=None, par=False):
  """
  Takes *path* and computes the relative path from *parent*. If *parent* is
  omitted, the current working directory is used.

  If *par* is #True, a relative path is always created when possible.
  Otherwise, a relative path is only returned if *path* lives inside the
  *parent* directory.
  """

  try:
    res = os.path.relpath(path, parent)
  except ValueError:
    # Raised eg. on Windows for differing drive letters.
    if not par:
      return abs(path)
    raise
  else:
    if not par and not issub(res):
      return abs(path)
    return res


def isfile_cs(path):
  """
  Checks if *path* points to an existing file. On case-insensitive platforms,
  this is different from the normal #isfile() function as it checks if the
  exact case-sensitive path points to an existing file.
  """

  if not os.path.isfile(path):
    return False
  if os.name == 'nt':
    return os.path.basename(path) == os.path.basename(fixcase(path))
  elif not is_case_sensitive:
    dirname, filename = split(path)
    return filename in os.listdir(dirname)
  return True


def isrel(path):
  return not isabs(path)


def issub(path, at_curr=True):
  """
  Returns #True if *path* is a relative path that does not point outside
  of its parent directory or is equal to the parent directory (ie. is equal
  to the #curdir string) unless *at_curr* is set to False.

  If the *path* is absolute or points upwards (eg. `../foo`) it will
  return False.
  """

  if isabs(path):
    return False
  path = norm(path)
  if path == pardir or path.startswith(pardir + sep):
    return False
  if path == curdir or path == curdir + sep:
    return at_curr
  return True


def isglob(path):
  """
  Checks if *path* is a glob pattern. Returns #True if it is, #False if not.
  """

  return '*' in path or '?' in path


def glob(patterns, parent=None, excludes=None, include_dotfiles=False,
         ignore_false_excludes=False):
  """
  Wrapper for #glob2.glob() that accepts an arbitrary number of
  patterns and matches them. The paths are normalized with #norm().

  Relative patterns are automaticlly joined with *parent*. If the
  parameter is omitted, it defaults to the current working directory.

  If *excludes* is specified, it must be a string or a list of strings
  that is/contains glob patterns or filenames to be removed from the
  result before returning.

  > Every file listed in *excludes* will only remove **one** match from
  > the result list that was generated from *patterns*. Thus, if you
  > want to exclude some files with a pattern except for a specific file
  > that would also match that pattern, simply list that file another
  > time in the *patterns*.

  # Parameters
  patterns (list of str): A list of glob patterns or filenames.
  parent (str): The parent directory for relative paths.
  excludes (list of str): A list of glob patterns or filenames.
  include_dotfiles (bool): If True, `*` and `**` can also capture
    file or directory names starting with a dot.
  ignore_false_excludes (bool): False by default. If True, items listed
    in *excludes* that have not been globbed will raise an exception.

  # Returns
  list of str: A list of filenames.
  """

  if not glob2:
    raise glob2_exc

  if isinstance(patterns, str):
    patterns = [patterns]

  if not parent:
    parent = os.getcwd()

  result = []
  for pattern in patterns:
    if not os.path.isabs(pattern):
      pattern = os.path.join(parent, pattern)
    result += glob2.glob(canonical(pattern))

  for pattern in (excludes or ()):
    if not os.path.isabs(pattern):
      pattern = os.path.join(parent, pattern)
    pattern = canonical(pattern)
    if not isglob(pattern):
      try:
        result.remove(pattern)
      except ValueError as exc:
        if not ignore_false_excludes:
          raise ValueError('{} ({})'.format(exc, pattern))
    else:
      for item in glob2.glob(pattern):
        try:
          result.remove(item)
        except ValueError as exc:
          if not ignore_false_excludes:
            raise ValueError('{} ({})'.format(exc, pattern))

  return result


def addtobase(subject, base_suffix):
  """
  Adds the string *base_suffix* to the basename of *subject*.
  """

  if not base_suffix:
    return subject
  base, ext = os.path.splitext(subject)
  return base + base_suffix + ext


def addprefix(subject, prefix):
  """
  Adds the specified *prefix* to the last path element in *subject*.
  If *prefix* is a callable, it must accept exactly one argument, which
  is the last path element, and return a modified value.
  """

  if not prefix:
    return subject
  dir_, base = split(subject)
  if callable(prefix):
    base = prefix(base)
  else:
    base = prefix + base
  return join(dir_, base)


def addsuffix(subject, suffix, replace=False):
  """
  Adds the specified *suffix* to the *subject*. If *replace* is True, the
  old suffix will be removed first. If *suffix* is callable, it must accept
  exactly one argument and return a modified value.
  """

  if not suffix and not replace:
    return subject
  if replace:
    subject = rmvsuffix(subject)
  if suffix and callable(suffix):
    subject = suffix(subject)
  elif suffix:
    subject += suffix
  return subject


def setsuffix(subject, suffix):
  """
  Synonymous for passing the True for the *replace* parameter in #addsuffix().
  """

  return addsuffix(subject, suffix, replace=True)


def rmvsuffix(subject):
  """
  Remove the suffix from *subject*.
  """

  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    subject = subject[:index]
  return subject


def getsuffix(subject):
  """
  Returns the suffix of a filename. If the file has no suffix, returns None.
  Can return an empty string if the filenam ends with a period.
  """

  index = subject.rfind('.')
  if index > subject.replace('\\', '/').rfind('/'):
    return subject[index+1:]
  return None


def makedirs(path, exist_ok=True):
  """
  Like #os.makedirs(), with *exist_ok* defaulting to #True.
  """

  try:
    os.makedirs(path)
  except OSError as exc:
    if exist_ok and exc.errno == errno.EEXIST:
      return
    raise


def chmod_update(flags, modstring):
  """
  Modifies *flags* according to *modstring*.
  """

  mapping = {
    'r': (_stat.S_IRUSR, _stat.S_IRGRP, _stat.S_IROTH),
    'w': (_stat.S_IWUSR, _stat.S_IWGRP, _stat.S_IWOTH),
    'x': (_stat.S_IXUSR, _stat.S_IXGRP, _stat.S_IXOTH)
  }

  target, direction = 'a', None
  for c in modstring:
    if c in '+-':
      direction = c
      continue
    if c in 'ugoa':
      target = c
      direction = None  # Need a - or + after group specifier.
      continue
    if c in 'rwx' and direction in '+-':
      if target == 'a':
        mask = functools.reduce(operator.or_, mapping[c])
      else:
        mask = mapping[c]['ugo'.index(target)]
      if direction == '-':
        flags &= ~mask
      else:
        flags |= mask
      continue
    raise ValueError('invalid chmod: {!r}'.format(modstring))

  return flags


def chmod_repr(flags):
  """
  Returns a string representation of the access flags *flags*.
  """

  template = 'rwxrwxrwx'
  order = (_stat.S_IRUSR, _stat.S_IWUSR, _stat.S_IXUSR,
           _stat.S_IRGRP, _stat.S_IWGRP, _stat.S_IXGRP,
           _stat.S_IROTH, _stat.S_IWOTH, _stat.S_IXOTH)
  return ''.join(template[i] if flags&x else '-'
                 for i, x in enumerate(order))


def chmod(path, modstring):
  flags = chmod_update(os.stat(path).st_mode, modstring)
  os.chmod(path, flags)


def compare_timestamp(src, dst):
  """
  Compares the timestamps of file *src* and *dst*, returning #True if the
  *dst* is out of date or does not exist. Raises an #OSError if the *src*
  file does not exist.
  """

  try:
    dst_time = os.path.getmtime(dst)
  except OSError as exc:
    if exc.errno == errno.ENOENT:
      return True  # dst does not exist
    raise

  src_time = os.path.getmtime(src)
  return src_time > dst_time


def compare_all_timestamps(srclist, dstlist):
  """
  Compares the timestamps of all files in *srclist* with *dstlist*. If any
  of the files in *dstlist* does not exist or any of the files in *srclist*
  is newer than any of the files in *dstlist*, True will be returned.
  """

  if not dstlist:
    return True  # no output, always dirty

  min_dst = None
  for x in dstlist:
    try:
      time = os.path.getmtime(x)
    except OSError as exc:
      if exc.errno == errno.ENOENT:
        return True  # dst does not exist
      raise
    if min_dst is None or time < min_dst:
      min_dst = time

  if not srclist:
    return False  # dst exists with no sources

  max_src = max(os.path.getmtime(x) for x in srclist)
  return max_src > min_dst


def fixcase(path):
  """
  Fixes the case of all path elements. On Windows, this uses the
  `GetLongPathNameW()` API. On other platforms, it uses #os.listdir
  to determine the proper case of the path elements.
  """

  if os.name == 'nt':
    # Thanks to http://stackoverflow.com/a/3694799/791713
    buf = ctypes.create_unicode_buffer(len(path) + 1)
    GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
    res = GetLongPathNameW(path, buf, len(path) + 1)
    if res == 0 or res > 260:
      return path
    else:
      return buf.value
  elif not is_case_sensitive and os.path.exists(path):
    is_path_abs = isabs(path)
    drive, path = splitdrive(path)
    if is_path_abs and not drive:
      drive = '/'
    elif drive and drive.endswith(':'):
      drive += os.sep
    items = []
    while path and path != '/':
      path, element = split(path)
      if not is_path_abs and not path:
        current = '.'
      else:
        current = join(drive, path)
      element_lc = element.lower()
      for name in os.listdir(current):
        if name.lower() == element_lc:
          element = name
          break
      items.append(element)
    items.reverse()
    path = join(drive, *items)
  return path


def listdir(path, do_raise=True):
  """
  Like #os.listdir(), but if *do_raise* is #False, an empty list will be
  returned if the *path* does not exist.
  """

  if do_raise:
    return os.listdir(path)
  else:
    try:
      return os.listdir(path)
    except (OSError, IOError) as e:
      if e.errno in (errno.ENOENT, errno.EPERM):
        return []
      raise


# Backwards compatibility
__all__ += ['get_long_path_name']
get_long_path_name = fixcase
