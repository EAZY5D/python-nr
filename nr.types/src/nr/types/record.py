# The MIT License (MIT)
#
# Copyright (c) 2019 Niklas Rosenstein
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

from . import abc
from .maps import OrderedDict
from .meta import InlineMetaclassBase
from .notset import NotSet
from six import iteritems, itervalues

import inspect
import six
import types


class Field(object):
  """
  Represents a field of a #Record class. Fields have a name, type and
  a default value. If a field has no name, it is "unbound" and the name
  may be derived from the name the field was assigned to in the #Record
  subclass declaration.
  """

  _global_create_index = 0

  def __init__(self, type, default=NotSet):
    self.name = None
    self.type = type
    self.default = default
    self.create_index = Field._global_create_index
    Field._global_create_index += 1

  def __repr__(self):
    return 'Field(name={!r}, type={!r}, default={!r})'.format(
      self.name, self.type, self.default)

  def get_default(self):
    if self.default is NotSet:
      raise RuntimeError('Field.default is NotSet')
    if isinstance(self.default, types.LambdaType):
      return self.default()
    return self.default

  @classmethod
  def with_name(cls, name, type, default=NotSet):
    obj = cls(type, default)
    obj.name = name
    return obj


def compile_fields(decl):
  """
  Compiles a fields declaration to an #OrderedDict mapping to #Field objects.
  A fields declaration can be a string, list or dictionary.

  For a string: Comma or whitespace separated.

  For a list:

  * Field
  * Tuple[str, Type] (name, type)
  * Tuple[str, Type, Union[LambdaType, Any]] (name, type, default)

  For a dictionary:

  * Field
  * Tuple[Type, Union[LambdaType, Any]] (type, default)
  * Type
  """

  # Split string into list of field names.
  if isinstance(decl, str):
    decl = [x.strip() for x in decl.split(',' if ',' in decl else ' ')]

  # Convert a mapping to the list form.
  elif isinstance(decl, abc.Mapping):
    new_decl = []
    for key, value in iteritems(decl):
      if isinstance(value, tuple):
        value = (key,) + value
      elif isinstance(value, Field):
        value.name = key
      else:
        value = (key, value)
      new_decl.append(value)
    decl = new_decl

  compiled_fields = OrderedDict()
  for item in decl:
    if isinstance(item, str):
      field = Field.with_name(item, None, NotSet)
    elif isinstance(item, Field):
      field = item
    elif isinstance(item, tuple):
      if len(item) == 1:
        name, type_, default = item[0], None, NotSet
      elif len(item) == 2:
        name, type_, default = item[0], item[1], NotSet
      elif len(item) == 3:
        name, type_, default = item
      else:
        raise ValueError('invalid tuple Field declaration: {!r}'.format(item))
      field = Field.with_name(name, type_, default)
    else:
      raise TypeError('unexpected Field declaration: {!r}'.format(item))
    if not field.name:
      raise ValueError('unbound Field found: {!r}'.format(field.name))
    if field.name in compiled_fields:
      raise ValueError('duplicate Field name: {!r}'.format(field.name))
    compiled_fields[field.name] = field

  return compiled_fields


class CleanRecord(InlineMetaclassBase):
  """
  A base-class similar to #typing.NamedTuple, but mutable. Fields can be
  specified using Python 3.6 class-member annotations, by setting the
  `__annotations__` or `__fields__` member to a list of annotations or
  by declaring class-members as #Field objects.

  In the following example all four `Person` declarations are identical.

  ```python
  class Person(Record):
    mail: str
    name: str = lambda: random_name()
    age: int = 0

  class Persom(Record):
    __fields__ = [
      ('mail', str),
      ('name', str, lambda: random_name()),
      ('age', int, 0)
    ]

  class Person(Record):
    mail = Field(str)
    name = Field(str, lambda: random_name())
    age = Field(str, 0)

  Person = create_record('Person', [
    ('mail', str),
    Field.with_name('name', str, lambda: random_name()),
    ('age', int, 0)
  ])
  ```
  """

  def __metainit__(self, name, bases, dict):
    """
    Overrides #InlineMetaclassBase.__metainit__(). Converts the fields or
    annotations defined on the class to a common dictionary representation.
    The source of the fields is determined in the following order:

    * Attribute `__fields__`
    * Attribute `__annotations__`
    * Member attributes (only #Field instances)
    """

    # Determine the source for the field declaration.
    if '__fields__' in dict:
      fields = dict['__fields__']
    elif '__annotations__' in dict:
      fields = dict['__annotations__']
      if isinstance(fields, abc.Mapping):
        for key, value in iteritems(fields):
          fields[key] = (value, getattr(self, key, NotSet))
    else:
      fields = []
      for key, value in iteritems(dict):
        if isinstance(value, Field):
          fields.append(key, value)

    # Merge with parent class fields.
    mro_fields = {}
    for base in reversed(bases):
      if hasattr(base, '__fields__'):
        mro_fields.update(base.__fields__)
    mro_fields.update(compile_fields(fields))

    for name, field in iteritems(mro_fields):
      if name != field.name:
        raise ValueError('mismatching Field name: name({!r}) != Field.name({!r})'
          .format(name, field.name))

    self.__fields__ = mro_fields
    self.__ifields__ = sorted(itervalues(mro_fields),
      key=lambda x: x.create_index)

  def __init__(self, *args, **kwargs):
    type_name = type(self).__name__

    # Validate number of arguments.
    nargs = len(args) + len(kwargs)
    if nargs > len(self.__fields__):
      raise TypeError('{}() expected at most {} arguments, got {}'
        .format(type_name, len(self.__fields__), nargs))

    # Raise an exception for any unknown keyword arguments.
    for key in kwargs:
      if key not in self.__fields__:
        raise TypeError('{}() unexpected keyword argument "{}"'
          .format(type_name, key))

    # Map positional arguments to keyword arguments.
    for arg, field in zip(args, self.__ifields__):
      if field.name in kwargs:
        raise TypeError('{}() got duplicate argument "{}"'
          .format(type_name, name))
      kwargs[field.name] = arg

    # Create attributes.
    for key, field in iteritems(self.__fields__):
      value = kwargs.get(key, NotSet)
      if value is NotSet:
        if field.default is NotSet:
          raise TypeError('{}() missing argument "{}"'.format(type_name, key))
        value = field.get_default()
      setattr(self, key, value)

  def __repr__(self):
    values = ((f.name, getattr(self, f.name)) for f in self.__ifields__)
    members = ', '.join('{}={!r}'.format(k, v) for k, v in values)
    return '{}({})'.format(type(self).__name__, members)


class ToJSON(object):
  """
  A mixin for the #CleanRecord class that adds a #to_json() method.
  Different from the #as_dict() method in the #AsDict mixin, #to_json()
  is called recursively on any of the attributes if they have a #to_json()
  method.
  """

  def to_json(self):
    result = {}
    for key in self.__fields__:
      value = getattr(self, key)
      if hasattr(value, 'to_json'):
        value = value.to_json()
      # TODO @NiklasRosenstein handle lists and dictionaries.
      result[key] = value
    return result


class AsDict(object):
  """
  A mixin for the #CleanRecord class that adds an #as_dict() method.
  """

  def as_dict(self):
    return dict((k, getattr(self, k)) for k in self.__fields__)


class Sequence(object):
  """
  A mixin for the #CleanRecord class that implements the mutable sequence
  interface.
  """

  def __iter__(self):
    for key in self.__fields__:
      yield getattr(self, key)

  def __len__(self):
    return len(self.__fields__)

  def __getitem__(self, index):
    if hasattr(index, '__index__'):
      return getattr(self, self.__ifields__[index.__index__()].name)
    elif isinstance(index, str):
      return getattr(self, str)
    else:
      raise TypeError('cannot index with {} object'
        .format(type(index).__name__))

  def __setitem__(self, index, value):
    if hasattr(index, '__index__'):
      setattr(self, self.__ifields__[index.__index__()].name, value)
    elif isinstance(index, str):
      setattr(self, index, value)
    else:
      raise TypeError('cannot index with {} object'
        .format(type(index).__name__))


class Record(CleanRecord, ToJSON, AsDict, Sequence):
  pass


def create_record(name, fields, *mixins):
  """
  Creates a new #Record subclass. If at least one *mixin* is specified, it is
  mixed into the parent class of the created #Record subclass. One of the
  mixins can also be a separate #Record subclass in which case it is used
  as the parent class instead of #Record.
  """

  base = next((x for x in mixins if isinstance(x, CleanRecord)), None)
  if not base:
    mixins = mixins + (Record,)

  module = inspect.currentframe().f_back.f_globals.get('__name__', __name__)
  return type(name, mixins, {'__fields__': fields, '__module__': module})


create = create_record
