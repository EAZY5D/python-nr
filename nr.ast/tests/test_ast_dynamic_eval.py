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

import textwrap
import sys
from nose.tools import *
from nr.ast import dynamic_exec, dynamic_eval


def test_dynamic_exec():
  assignments = {}
  assignments['assignments'] = lambda: assignments

  def resolve(x):
    try:
      return assignments[x]
    except KeyError:
      raise NameError(x)

  assign = assignments.__setitem__
  delete = assignments.__delitem__

  code = textwrap.dedent('''
    from __future__ import print_function
    from nose.tools import *
    import os
    import os.path
    import sys
    a, b = 0, 0
    def main(param1):
      global a
      a = 42
      b = 99
      class Foo:
        a = 9999
        b = 9999
      alocal = 'ham'
      tbd = 'delete me!'
      del tbd
      with assert_raises(NameError):
        tbd
      print("Hello, World from", os.getcwd(), 'a, b', (a, b))
      assert_equals(a, 42)
      assert_equals(b, 99)
      assert_equals(assignments()['a'], 42)
      assert_equals(assignments()['b'], 0)
      for i in range(10):
        pass
      assert 'i' not in assignments(), 'i in assignments'
      assert_equals(i, 9)
      for j in range(10):
        j = j*2
      assert 'j' not in assignments(), 'j in assignments'
      assert_equals(j, 18)
      class Test:
        def __init__(self):
          queue = [('ham', 'egg')]
          c, b = queue.pop()
          assert_equals((c, b), ('ham', 'egg'))
          assert_equals(alocal, 'ham')
      assert 'Test' not in assignments(), 'Test in assignments'
      assert '__init__' not in assignments(), '__init__ in assignments'
      Test()
      assert_equals((lambda x: x)(42), 42)
      [x for x in range(10)]
      if sys.version_info[0] == 3:
        with assert_raises(NameError):
          x
      else:
        x
      class ContextManager(object):
        def __enter__(self):
          return 'ContextManager!'
        def __exit__(self,*a):
          pass
      with ContextManager() as value:
        assert_equals(value, 'ContextManager!')
      assert_equals(value, 'ContextManager!')
      assert 'value' not in assignments()
    main('hello')
    assert_equals(a, 42)
    assert_equals(b, 0)
    del a
    with assert_raises(NameError):
      a
  ''')

  dynamic_exec(code, resolve, assign, delete)

  for key in ('os', 'b', 'main'):
    assert key in assignments, key

  assert_equals(assignments['b'], 0)


def test_exception_handler():
  code = textwrap.dedent('''
    import sys
    from nose.tools import *
    def main():
      try:
        raise Exception
      except Exception as e:
        assert_is_instance(e, Exception)
    main()
    with assert_raises(NameError):
      e

    try:
      raise Exception
    except Exception as e:
      assert_is_instance(e, Exception)

    if sys.version_info[0] == 3:
      with assert_raises(NameError):
        e
    elif sys.version_info[0] == 2:
      assert_is_instance(e, Exception)
    else:
      assert False, "Oh boy"
  ''')

  scope = {}
  dynamic_exec(code, scope)
  if sys.version_info[0] == 3:
    assert 'e' not in scope
  elif sys.version_info[0] == 2:
    assert 'e' in scope
  else:
    assert False, "Oh boy"


def test_prevent_deletion():
  code = textwrap.dedent('''
    a = 42
    del a
    a
  ''')

  scope = {}
  def resolve(x):
    try:
      return scope[x]
    except KeyError:
      raise NameError(x)
  assign = scope.__setitem__
  delete = lambda k: None

  dynamic_exec(code, resolve, assign, delete)
  assert 'a' in scope


def test_shadowed_deletion():
  code = textwrap.dedent('''
    from nose.tools import assert_raises
    a = 42
    del a
    with assert_raises(NameError):
      a
  ''')

  scope = {}
  def resolve(x):
    try:
      return scope[x]
    except KeyError:
      raise NameError(x)
  assign = scope.__setitem__
  delete = None

  dynamic_exec(code, resolve, assign, delete)
  assert 'a' in scope


def test_recursion():
  code = textwrap.dedent('''
    def main():
      def rec(n):
        if n > 0:
          rec(n-1)
      rec(5)
    main()

    def rec(n):
      if n > 0:
        rec(n-1)
    rec(5)
  ''')

  dynamic_exec(code, {})


def test_super():
  code = textwrap.dedent('''
    def main():
      class Test(object):
        def __init__(self):
          super(Test, self).__init__()
      Test()
    main()

    class Test(object):
      def __init__(self):
        super(Test, self).__init__()
    Test()
  ''')
  dynamic_exec(code, {})

  if sys.version_info[0] >= 3:
    code = textwrap.dedent('''
      from nose.tools import assert_equals

      def main():
        class Test(object):
          def __init__(self):
            assert_equals(__class__, Test)
            super().__init__()
        Test()
      main()

      class Test(object):
        def __init__(self):
          assert_equals(__class__, Test)
          super().__init__()
      Test()
    ''')
    dynamic_exec(code, {})


def test_builtin_members():
  code = textwrap.dedent('''
    from nose.tools import *
    with assert_raises(NameError):
      __class__
  ''')
  dynamic_exec(code, {})


def test_class_members():
  code = textwrap.dedent('''
    from nose.tools import assert_equals
    a = 42
    class Test:
      a = 99
      assert_equals(a, 99)
      def __init__(self):
        assert_equals(a, 42)
        assert_equals(self.a, 99)
    assert_equals(a, 42)
    assert_equals(Test.a, 99)
  ''')
  dynamic_exec(code, {})
