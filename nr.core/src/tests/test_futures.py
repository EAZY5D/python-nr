
from nr.core.futures import Future, ThreadPool
import pytest


def test_set_exception():
  f = Future()
  f.set_exception(ValueError())
  with pytest.raises(ValueError):
    f.result()
  assert f.done()


def test_set_result():
  f = Future()
  f.set_result(42)
  assert f.result() == 42
  assert f.done()
