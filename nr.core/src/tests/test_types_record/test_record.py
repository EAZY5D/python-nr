
import copy
import os
import pytest
import sys

sys.path.append(os.path.dirname(__file__))


def _test_record(m):
  s = m.Student('Peter', mail='peter@mit.com', school='MIT')
  assert s.as_dict() == {'name': 'Peter', 'mail': 'peter@mit.com', 'age': 50, 'school': 'MIT'}

  c = m.Change('NEW', 'user', 'name', 'John Smith')
  assert c.type == 'NEW'
  assert c.section == 'user'
  assert c.key == 'name'
  assert c.value == 'John Smith'

  assert c == c
  assert copy.copy(c) == c


@pytest.mark.skipif(sys.version_info < (3,6),
                    reason="requires python3.6 or higher")
def test_record_36():
  import _record36
  _test_record(_record36)


def test_record():
  import _record
  _test_record(_record)
