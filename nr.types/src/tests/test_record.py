
from nr.types.record import Record


class Person(Record):
  name: str = 'John'
  mail: str = 'john@smith.com'
  age: int = 50


class Student(Person):
  school: str


def test_record():
  s = Student('Peter', mail='peter@mit.com', school='MIT')
  assert s.as_dict() == {'name': 'Peter', 'mail': 'peter@mit.com', 'age': 50, 'school': 'MIT'}
