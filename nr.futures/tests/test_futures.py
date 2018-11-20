
from nose.tools import *
from nr.futures import Future, ThreadPool


def test_set_exception():
  f = Future()
  f.set_exception(ValueError())
  with assert_raises(ValueError):
    f.result()
  assert f.done()


def test_set_result():
  f = Future()
  f.set_result(42)
  assert_equals(f.result(), 42)
  assert f.done()
