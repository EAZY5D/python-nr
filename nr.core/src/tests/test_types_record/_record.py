
from nr.core.types.record import Record


class Person(Record):
  __annotations__ = [
    ('name', str, 'John'),
    ('mail', str, 'john@smith.com'),
    ('age', int, 50)
  ]


class Student(Person):
  __annotations__ = {
    'school': str
  }


class Change(Record):
  __fields__ = 'type section key value'
