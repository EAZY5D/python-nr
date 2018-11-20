
import os
from nose.tools import *
from nr.gitignore import Pattern, IgnoreList, IgnoreListCollection, MATCH_IGNORE


def test_pattern():
  p = Pattern('__pycache__')
  assert_true(p.match('__pycache__'))
  assert_true(p.match('__PycaCHE__') or os.name != 'nt')
  assert_true(p.match('foo/bar/__pycache__'))
  assert_true(p.match('foo/bar/__pycache__/bar'))
  assert_false(p.match('foo'))
  assert_false(p.match('bar/__pycache'))

  p = Pattern('/__pycache__')
  assert_false(p.match('__pycache__'))  # TODO: Do we really don't want that to match?
  assert_true(p.match('/__pycache__'))
  assert_false(p.match('/foo/__pycache__'))


def test_ignore_list():
  ignore = IgnoreList()
  ignore.parse(['__pycache__', 'dist'])
  assert ignore.match('./dist/module-1.0.0.tar.gz') == MATCH_IGNORE
