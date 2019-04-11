
from nr.core.types.record import Record
import copy


class Person(Record):
  name: str = 'John'
  mail: str = 'john@smith.com'
  age: int = 50


class Student(Person):
  school: str


class Change(Record):
  __fields__ = 'type section key value'


def test_record():
  s = Student('Peter', mail='peter@mit.com', school='MIT')
  assert s.as_dict() == {'name': 'Peter', 'mail': 'peter@mit.com', 'age': 50, 'school': 'MIT'}

  c = Change('NEW', 'user', 'name', 'John Smith')
  assert c.type == 'NEW'
  assert c.section == 'user'
  assert c.key == 'name'
  assert c.value == 'John Smith'

  assert c == c
  assert copy.copy(c) == c
