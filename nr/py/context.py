# Copyright (c) 2017  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the follo  wing conditions:
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

import sys
import inspect


class ContextSkipped(Exception):
  pass


class SkippableContextManager(object):
  """
  This class implements a skippable context manager. When you create a subclass
  and implement `__enter__()`, you can use the #skip() function from within to
  skip the with context entirely.

  Thanks to http://stackoverflow.com/a/12594789/791713.

  # Example

  ```python
  class IfContext(context.SkippableContextManager):
    def __init__(self, cond):
      self.cond = cond
    def __enter__(self):
      if not self.cond:
        context.skip()
      return self

  with IfContext(False):
    FooLalala.ThisIsNotBeingExecuted
  ```
  """

  def __exit__(self, type, value, traceback):
    if type is ContextSkipped:
      return True
    return False


def skip(stackframe=1):
  """
  Must be called from within `__enter__()`. Performs some magic to have a
  #ContextSkipped exception be raised the moment the with context is entered.
  The #ContextSkipped must then be handled in `__exit__()` to suppress the
  propagation of the exception.

  > Important: This function does not raise an exception by itself, thus
  > the `__enter__()` method will continue to execute after using this function.
  """

  def trace(frame, event, args):
    raise ContextSkipped

  sys.settrace(lambda *args, **kwargs: None)
  frame = sys._getframe(stackframe + 1)
  frame.f_trace = trace
