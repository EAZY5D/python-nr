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

from .exceptions import ValidationError


class Field(object):
  """
  This class represents a named field in a data record. It is used for
  declaration purposes from Python code. The field name will usually be bound
  at a later point and not at construction time (eg. from a metaclass
  constructor).

  The field class has an internal counter that counts up for each instance that
  is created. This is used by the #tundras.table.TableEntity class to order the
  fields.

  # Parameters

  field_type (type): The type of the field. Must be a type object
    or None to make the field accept any Python object.
  name (str): The name of the field. If omitted, the field is unbound.
  default (field_type): The default value of a field. If this is omitted, it
    will default to #NotImplemented and thus indicate that the field is
    required.
  default_factory (callable): If specified, must be a callable that can
    be called without arguments and return the default value for the
    field. Note that this parameter conflicts with *default* and a
    #ValueError is raised if both are specified.
  null (bool): If this is True, the Field accepts #None as a valid value even
    if the *field_type* would reject it.
  entity (object): The entity that contains the field. Similar to the
    name, this is usually bound automatically at a later point. An
    entity is usually a class object. An entity must have a `__name__`
    attribute.
  adapter (callable): A function that can convert any value to the correct
    *field_type* or raise a #ValueError or #TypeError on failure. If omitted,
    defaults to *field_type*.
  """

  _instance_counter = 0

  def __init__(self, field_type, name=None, default=NotImplemented,
               default_factory=None, null=False, entity=None, adapter=None):
    if field_type is not None and not isinstance(field_type, type):
      raise TypeError("'field_type' must be a type object")
    if default is not NotImplemented and default_factory is not None:
      raise TypeError("'default' and 'default_factory' conflict")
    if default_factory is not None and not callable(default_factory):
      raise TypeError("'default_factory' must be callable")
    self.type = field_type
    self.adapter = adapter
    self.name = name
    self.default = default
    self.default_factory = default_factory
    self.null = null
    self.entity = entity
    self.instance_id = Field._instance_counter
    Field._instance_counter += 1

  def __repr__(self):
    res = '<Field {0!r} of {1}'.format(self.full_name, self.type_name)
    if self.adapter:
      res += ' from {0}()'.format(self.adapter.__name__)
    return res + '>'

  def __call__(self, value):
    """
    Calls the #adapter function of the field. If the adapter is not defined,
    the #type type/function is called instead. If *value* is already an
    instance of the field's #type, *value* is returned as-is.
    """

    if self.type is None:
      return value
    if self.null and value is None:
      return value
    if isinstance(value, self.type):
      return value

    func = self.adapter or self.type
    try:
      return func(value)
    except (ValueError, TypeError) as exc:
      raise ValidationError(self, value, exc)

  def check_type(self, value):
    """
    Raises a #TypeError if *value* is not an instance of the field's #type.
    """

    if self.null and value is None:
      return
    if self.type is not None and not isinstance(value, self.type):
      msg = '{0!r} expected type {1}'
      raise TypeError(msg.format(self.full_name, self.type.__name__))

  def get_default(self):
    """
    Return the default value of the field. Returns either #default, the return
    value of #default_factory or raises a #RuntimeError if the field has no
    default value.
    """

    if self.default is not NotImplemented:
      return self.default
    elif self.default_factory is not None:
      return self.default_factory()
    else:
      raise RuntimeError('{0!r} has no default value'.format(self.full_name))

  @property
  def has_default(self):
    """
    Returns true if this field supplies a default values, false if not.
    """

    return self.default is not NotImplemented or self.default_factory is not None

  @property
  def full_name(self):
    """
    The full name of the field. This is the field's entities name
    concatenated with the field's name. If the field is unnamed or
    not bound to an entity, the result respectively contains None.
    """

    entity = self.entity.__name__ if self.entity is not None else None
    name = self.name if self.name is not None else None
    if entity and name:
      return entity + '.' + name
    elif entity:
      return entity + '.<unnamed>'
    elif name:
      return '<unbound>.' + name
    else:
      return '<unbound>.<unnamed>'

  @property
  def type_name(self):
    """
    Returns the full type identifier of the field.
    """

    res = self.type.__name__
    if self.type.__module__ not in ('__builtin__', 'builtins'):
      res = self.type.__module__ + '.' + res
    return res
