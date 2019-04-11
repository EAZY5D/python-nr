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

from nr.core.ast.dynamic import dynamic_exec, dynamic_eval, DynamicMapping


def test_dynamic_exec():
  assignments = {}
  assignments['assignments'] = lambda: assignments

  code = textwrap.dedent('''
    from __future__ import print_function
    import os
    import os.path
    import sys
    import pytest
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
      with pytest.raises(NameError):
        tbd
      print("Hello, World from", os.getcwd(), 'a, b', (a, b))
      assert a == 42
      assert b == 99
      assert assignments()['a'] == 42
      assert assignments()['b'] == 0
      for i in range(10):
        pass
      assert 'i' not in assignments(), 'i in assignments'
      assert i == 9
      for j in range(10):
        j = j*2
      assert 'j' not in assignments(), 'j in assignments'
      assert j == 18
      class Test:
        def __init__(self):
          queue = [('ham', 'egg')]
          c, b = queue.pop()
          assert (c, b) == ('ham', 'egg')
          assert alocal == 'ham'
      assert 'Test' not in assignments(), 'Test in assignments'
      assert '__init__' not in assignments(), '__init__ in assignments'
      Test()
      assert (lambda x: x)(42) == 42
      [x for x in range(10)]
      if sys.version_info[0] == 3:
        with pytest.raises(NameError):
          x
      else:
        x
      class ContextManager(object):
        def __enter__(self):
          return 'ContextManager!'
        def __exit__(self,*a):
          pass
      with ContextManager() as value:
        assert value == 'ContextManager!'
      assert value == 'ContextManager!'
      assert 'value' not in assignments()
    main('hello')
    assert a == 42
    assert b == 0
    del a
    with pytest.raises(NameError):
      a
  ''')

  dynamic_exec(code, DynamicMapping(assignments))

  for key in ('os', 'b', 'main'):
    assert key in assignments, key

  assert assignments['b'] == 0


def test_exception_handler():
  code = textwrap.dedent('''
    import sys, pytest
    def main():
      try:
        raise Exception
      except Exception as e:
        assert isinstance(e, Exception)
    main()
    with pytest.raises(NameError):
      e

    try:
      raise Exception
    except Exception as e:
      assert isinstance(e, Exception)

    if sys.version_info[0] == 3:
      with pytest.raises(NameError):
        e
    elif sys.version_info[0] == 2:
      assert isinstance(e, Exception)
    else:
      assert False, "Oh boy"
  ''')

  scope = {}
  dynamic_exec(code, DynamicMapping(scope))
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

  class Mapping(DynamicMapping):
    def __delitem__(self, key):
      pass

  scope = Mapping({})
  dynamic_exec(code, scope)
  assert 'a' in scope


def test_shadowed_deletion():
  code = textwrap.dedent('''
    import pytest
    a = 42
    del a
    with pytest.raises(NameError):
      a
  ''')

  class Mapping(DynamicMapping):
    def __delitem__(self, key):
      self._deleted.add(key)

  scope = {}
  dynamic_exec(code, Mapping(scope))
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

  dynamic_exec(code, DynamicMapping({}))


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
  dynamic_exec(code, DynamicMapping({}))

  if sys.version_info[0] >= 3:
    code = textwrap.dedent('''
      def main():
        class Test(object):
          def __init__(self):
            assert __class__ == Test
            super().__init__()
        Test()
      main()

      class Test(object):
        def __init__(self):
          assert __class__ == Test
          super().__init__()
      Test()
    ''')
  dynamic_exec(code, DynamicMapping({}))


def test_builtin_members():
  code = textwrap.dedent('''
    import pytest
    with pytest.raises(NameError):
      __class__
  ''')
  dynamic_exec(code, DynamicMapping({}))

  code = textwrap.dedent('''
    sys = __import__('sys')
    import sys as _sys
    assert sys is _sys
  ''')
  dynamic_exec(code, DynamicMapping({}))


def test_class_members():
  code = textwrap.dedent('''
    a = 42
    class Test:
      a = 99
      assert a == 99
      def __init__(self):
        assert a == 42
        assert self ==a, 99
    assert a == 42
    assert Test.a == 99
  ''')
  dynamic_exec(code, DynamicMapping({}))
