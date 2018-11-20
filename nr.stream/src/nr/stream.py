# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
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

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.2'


import functools
import itertools

try:
  range = xrange
except NameError:
  pass


class _dualmethod:
  """
  A combination of #classmethod() and instance methods. Methods decorated
  with this class can be called from the class and instance level. The first
  parameter will then refer to the class or the instance, respectively.
  """

  def __init__(self, func):
    self.func = func
    functools.update_wrapper(self, func)

  def __get__(self, instance, owner):
    assert owner is not None
    if instance is not None:
      return functools.partial(self.func, owner, instance)
    return functools.partial(self.func, owner)


class stream:
  """
  A wrapper for iterables that provides the stream processor functions of
  this module in an object-oriented interface.
  """

  def __init__(self, iterable):
    self.iterable = iter(iterable)

  def __iter__(self):
    return iter(self.iterable)

  def __next__(self):
    return next(self.iterable)

  def __getitem__(self, val):
    if isinstance(val, slice):
      return self.slice(val.start, val.stop, val.step)
    else:
      raise TypeError('{} object is only subscriptable with slices'.format(type(self).__name__))

  @_dualmethod
  def call(cls, iterable, *a, **kw):
    """
    Calls every item in *iterable* with the specified arguments.
    """

    return cls(x(*a, **kw) for x in iterable)

  @_dualmethod
  def map(cls, iterable, func, *a, **kw):
    """
    Iterable-first replacement of Python's built-in `map()` function.
    """

    return cls(func(x, *a, **kw) for x in iterable)

  @_dualmethod
  def filter(cls, iterable, cond, *a, **kw):
    """
    Iterable-first replacement of Python's built-in `filter()` function.
    """

    return cls(x for x in iterable if cond(x, *a, **kw))

  @_dualmethod
  def unique(cls, iterable, key=None):
    """
    Yields unique items from *iterable* whilst preserving the original order.
    """

    if key is None:
      key = lambda x: x
    def generator():
      seen = set()
      seen_add = seen.add
      for item in iterable:
        key_val = key(item)
        if key_val not in seen:
          seen_add(key_val)
          yield item
    return cls(generator())

  @_dualmethod
  def chunks(cls, iterable, n, fill=None):
    """
    Collects elements in fixed-length chunks.
    """

    return cls(itertools.zip_longest(*[iter(iterable)] * n, fillvalue=fill))

  @_dualmethod
  def concat(cls, iterables):
    """
    Similar to #itertools.chain.from_iterable().
    """

    def generator():
      for it in iterables:
        for element in it:
          yield element
    return cls(generator())

  @_dualmethod
  def chain(cls, *iterables):
    """
    Similar to #itertools.chain.from_iterable().
    """

    def generator():
      for it in iterables:
        for element in it:
          yield element
    return cls(generator())

  @_dualmethod
  def attr(cls, iterable, attr_name):
    """
    Applies #getattr() on all elements of *iterable*.
    """

    return cls(getattr(x, attr_name) for x in iterable)

  @_dualmethod
  def item(cls, iterable, key):
    """
    Applies `__getitem__` on all elements of *iterable*.
    """

    return cls(x[key] for x in iterable)

  @_dualmethod
  def of_type(cls, iterable, types):
    """
    Filters using #isinstance().
    """

    return cls(x for x in iterable if isinstance(x, types))

  @_dualmethod
  def partition(cls, iterable, pred):
    """
    Use a predicate to partition items into false and true entries.
    """

    t1, t2 = itertools.tee(iterable)
    return cls(itertools.filterfalse(pred, t1), filter(pred, t2))

  @_dualmethod
  def dropwhile(cls, iterable, pred):
    return cls(itertools.dropwhile(pred, iterable))

  @_dualmethod
  def takewhile(cls, iterable, pred):
    return cls(itertools.takewhile(pred, iterable))

  @_dualmethod
  def groupby(cls, iterable, key=None):
    return cls(itertools.groupby(iterable, key))

  @_dualmethod
  def slice(cls, iterable, *args, **kwargs):
    return cls(itertools.islice(iterable, *args, **kwargs))

  def first(self):
    return next(iter(self))

  @_dualmethod
  def count(cls, iterable):
    """
    Returns the number of items in an iterable.
    """

    iterable = iter(iterable)
    count = 0
    while True:
      try:
        next(iterable)
      except StopIteration:
        break
      count += 1
    return count

  @_dualmethod
  def consume(cls, iterable, n=None):
    if n is not None:
      for _ in range(n):
        try:
          next(iterable)
        except StopIteration:
          break
    else:
      while True:
        try:
          next(iterable)
        except StopIteration:
          break
    return iterable
