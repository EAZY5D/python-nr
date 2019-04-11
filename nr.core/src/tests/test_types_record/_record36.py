
from nr.core.types.record import Record


class Person(Record):
  name: str = 'John'
  mail: str = 'john@smith.com'
  age: int = 50


class Student(Person):
  school: str


class Change(Record):
  __fields__ = 'type section key value'
