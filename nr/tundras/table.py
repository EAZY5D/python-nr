# Copyright (C) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from .field import Field
from .exceptions import EntityInitializationError
from .tools import InlineMetaclassBase
from .pycompat import iteritems

import copy


class TableEntity(InlineMetaclassBase):
  """
  This is the base for classes that represent a record in a table. An instance
  of this class represents a row in that table. The columns of that table, aka.
  the fields of a record, are defined by creating #Field objects on class-level.
  Whent the class is constructed, the field-names are bound and the #__fields__
  list is created.

  ```python
  class Contact(TableEntity):
    name = Field(str)
    address = Field(str)
    phone = Field(str)

  peter = Contact("Peter", "Main Street 42", "+1 49 42 42")
  ```
  """

  __fields__ = []
  __fields_set__ = frozenset()

  def __metanew__(meta, name, bases, dict):
    # Grab the existing fields and copy them so they can be rebound
    # to this new entity, then append the new field names.
    fields = []
    for base in bases:
      for key in getattr(base, '__fields__', []):
        field = copy.copy(getattr(base, key))
        fields.append(field)

    # Collect all fields that this new class introduces and bind
    # their field name.
    for key, value in iteritems(dict):
      if isinstance(value, Field):
        value.name = key
        fields.append(value)

    # Sort the fields by their instance ID (this number is incremented
    # each time the Field constructor is called, thus giving us the
    # correct order for the fields).
    fields.sort(key=lambda f: f.instance_id)

    # Compute the field names.
    dict['__fields__'] = [f.name for f in fields]
    dict['__fields_set__'] = frozenset(dict['__fields__'])

    entity = type.__new__(meta, name, bases, dict)
    for field in fields:
      field.entity = entity
    return entity

  def __init__(self, *args, **kwargs):
    # Translate the arguments into an attributes dictionary (without
    # validation/conversion).
    cls = type(self)
    attrs = {}
    for index, value in enumerate(args):
      if index >= len(cls.__fields__):
        msg = '{0}() takes at most {1} arguments ({2} given)'.format(
          cls.__name__, len(cls.__fields__), len(args))
        raise EntityInitializationError(msg)
      attrs[cls.__fields__[index]] = value
    for key, value in iteritems(kwargs):
      if key not in cls.__fields_set__:
        msg = '__init__() got unexpected keyword argument {0!r}'
        raise EntityInitializationError(msg.format(key))
      elif key in attrs:
        msg = '__init__() got multiple values for keyword argument {0!r}'
        raise EntityInitializationError(msg.format(key), getattr(cls, key))
      attrs[key] = value

    # Make sure all required fields are specified or fallback on
    # the default values specified in the field.
    for index, key in enumerate(cls.__fields__):
      if key not in attrs:
        field = getattr(cls, key)
        if field.has_default:
          attrs[key] = field.get_default()
        else:
          msg = '__init__() missing required argument: {0!r} (position {1})'
          raise EntityInitializationError(msg.format(key, index), getattr(cls, key))

    # Validate/convert the attributes and assign them to self.
    for key, value in iteritems(attrs):
      field = getattr(cls, key)
      value = field(value)
      setattr(self, key, value)

  def __repr__(self):
    result = '<' + type(self).__name__
    parts = []
    for key in type(self).__fields__:
      parts.append('{0}={1!r}'.format(key, getattr(self, key)))
    if parts:
      result += ' ' + ' '.join(parts)
    return result + '>'

  def __iter__(self):
    for key in type(self).__fields__:
      yield getattr(self, key)

  def __getitem__(self, index_or_key):
    if isinstance(index_or_key, int):
      key = type(self).__fields__[index_or_key]
    else:
      key = index_or_key
      if key not in type(self).__fields_set__:
        raise KeyError(key)
    return getattr(self, key)

  def __setitem__(self, index_or_key, value):
    if isinstance(index_or_key, int):
      key = type(self).__fields__[index_or_key]
    else:
      key = index_or_key
      if key not in type(self).__fields_set__:
        raise KeyError(key)
    field = getattr(type(self), key)
    field.check_type(value)
    super(TableEntity, self).__setattr__(key, value)

  def __setattr__(self, key, value):
    if key not in type(self).__fields_set__:
      raise AttributeError(key)
    field = getattr(type(self), key)
    field.check_type(value)
    super(TableEntity, self).__setattr__(key, value)

  def __len__(self):
    return len(type(self).__fields__)
