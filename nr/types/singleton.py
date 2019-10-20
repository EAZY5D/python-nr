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
"""
This module provides a simple facility to create singleton objects.

# members

Default (singleton): A singleton that is intended to represent a default value
  where #None is an accepted, non-default value.
"""

def make_singleton(name, type_name=None, as_bool=True):
  """
  Create a single type and return its only instance with the
  specified #name. If #type_name is not specified, it is automatically
  derived from the singleton #name.
  """

  class singleton_class(object):
    __instance = None
    def __new__(cls):
      if cls.__instance is None:
        cls.__instance = super(singleton_class, cls).__new__(cls)
      return cls.__instance
    def __str__(self):
      return name
    def __repr__(self):
      return name
    def __bool__(self):
      return as_bool
    __nonzero__ = __bool__

  if type_name is None:
    type_name = name + 'Type'
  singleton_class.__name__ = type_name
  return singleton_class()

#: A singleton object like :const:`None`, :const:`True` or :const:`False`.
#: Can be used to denote the default value of an argument when :const:`None`
#: is an accepted non-default value.
Default = make_singleton('Default')
