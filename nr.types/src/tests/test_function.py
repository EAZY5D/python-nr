
from nr.types.function import replace
import pytest


class ClosureNotReplaced(Exception):
  pass


def create_function_with_closure(value, expected_value):
  def check():
    if value != expected_value:
      raise ClosureNotReplaced
  return check


def test_has_closure():
  func = create_function_with_closure('bar', 'foo')
  assert len(func.__closure__) == 2
  with pytest.raises(ClosureNotReplaced):
    func()

  func = replace(func, closure={'value': 'foo'})
  func()
