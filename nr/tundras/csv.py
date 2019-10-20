# Copyright (C) 2016  Niklas Rosenstein
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
"""
This module is a wrapper for the standard library :mod:`csv` module
which does not support unicode in Python 2. Note that the :class:`reader`
and :class:`writer` always expect file-objects that read/write binary
data. This is especially important in Python 3 as :class:`str` is a
new text type that is incompatible with :class:`bytes`.

For convenience, if you pass a :class:`io.TextIOWrapper` in Python 3,
it will automatically be unpacked into the underlying binary stream.
"""

from __future__ import absolute_import
from .pycompat import Py3, binary_type, text_type

import codecs, csv, sys
if Py3:
  import io


def unpack_text_io_wrapper(fp, encoding):
  """
  If *fp* is a #io.TextIOWrapper object, this function returns the underlying
  binary stream and the encoding of the IO-wrapper object. If *encoding* is not
  None and does not match with the encoding specified in the IO-wrapper, a
  #RuntimeError is raised.
  """

  if isinstance(fp, io.TextIOWrapper):
    if fp.writable() and encoding is not None and fp.encoding != encoding:
      msg = 'TextIOWrapper.encoding({0!r}) != {1!r}'
      raise RuntimeError(msg.format(fp.encoding, encoding))
    if encoding is None:
      encoding = fp.encoding
    fp = fp.buffer

  return fp, encoding


class reader(object):
  """
  This is an enhanced implementation of the #csv.reader class that supports an
  *encoding* parameter. Note that the file should be opened in binary mode!
  """

  def __init__(self, fp, dialect=csv.excel, encoding=None, **kw):
    if Py3:
      fp, encoding = unpack_text_io_wrapper(fp, encoding)
      fp = codecs.getreader(encoding or sys.getdefaultencoding())(fp)
    self._reader = csv.reader(fp, dialect, **kw)
    self._encoding = encoding or sys.getdefaultencoding()

  def next(self):
    row = next(self._reader)
    if row and isinstance(row[0], binary_type):
      row = [x.decode(self._encoding) for x in row]
    return row

  __next__ = next

  def __iter__(self):
    return self


class writer(object):
  """
  This is an enhanced implementation of the #csv.writer class that supports an
  *encoding* parameter. Note that the file should be opened in binary mode!

  Note that the writer also supports casting non-string/non-text types to text
  using #pycompat.text_type.
  """

  def __init__(self, fp, dialect=csv.excel, encoding=None, **kw):
    if Py3:
      fp, encoding = unpack_text_io_wrapper(fp, encoding)
      fp = codecs.getwriter(encoding or sys.getdefaultencoding())(fp)
    self._writer = csv.writer(fp, dialect, **kw)
    self._encoding = encoding or sys.getdefaultencoding()

  def writerow(self, row):
    if Py3:
      self._writer.writerow([str(x) for x in row])
    else:
      self._writer.writerow([unicode(x).encode(self._encoding) for x in row])

  def writerows(self, rows):
    [self.writerow(x) for x in rows]
