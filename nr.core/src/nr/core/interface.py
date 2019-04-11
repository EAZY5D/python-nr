# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
This module allows you to declare and implement interfaces similar to
#zope.interface, but with some extras.
"""

from __future__ import absolute_import
import itertools
import nr.core.types.meta as _meta
import sys
import types


class _Member(object):

  def __init__(self, interface, name, hidden=False):
    self.interface = interface
    self.name = name
    self.hidden = hidden

  def __repr__(self):
    result = '<{} {!r}'.format(type(self).__name__, self.name)
    if self.interface:
      result += ' of interface {!r}'.format(self.interface.__name__)
    return result + '>'

  @property
  def is_bound(self):
    if self.interface and self.name:
      return True
    return False


class Method(_Member):

  def __init__(self, interface, name, impl=None, final=False, hidden=False):
    super(Method, self).__init__(interface, name)
    self.impl = impl
    self.final = final
    self.hidden = hidden

  def __call__(self, *a, **kw):
    if self.impl:
      return self.impl(*a, **kw)
    return None

  @classmethod
  def is_candidate(cls, name, value):
    if name.startswith('_') and not name.endswith('_'):  # Private function
      return False
    return isinstance(value, types.FunctionType)

  @classmethod
  def wrap_candidate(cls, interface, name, value):
    if cls.is_candidate(name, value):
      # We don't want these functions to be an actual "member" of the interface
      # API as they can be implemented for every interface and not collide.
      hidden = name in ('__new__', '__init__', '__constructed__')
      # If it's one of the hidden methods, they also act as the "default"
      # implementation because we actually want to call them independently
      # of potential overrides by the implementation.
      impl = value if getattr(value, '__is_default__', hidden) else None
      final = getattr(value, '__is_final__', False)
      return Method(interface, name, impl, final, hidden)
    return None


class Attribute(_Member):
  """
  Represents an attribute on an interface. Note that attributes on interface
  can conflict the same way methods can do. Usually, attribute declaratons
  are only used if the interface adds the respective member in `__init__()`.

  Inside an interface declaration, use the #attr() function to create an
  attribute that will be bound automatically when the interface class is
  constructed.
  """

  def __init__(self, interface, name, type=None):
    super(Attribute, self).__init__(interface, name)
    self.type = type


class Property(_Member):
  """
  Represents a property in an interface. A property can have default
  implementations for the getter, setter and deleter independently.
  """

  def __init__(self, interface, name, getter_impl=None, setter_impl=NotImplemented,
               deleter_impl=NotImplemented, getter_final=False, setter_final=False,
               deleter_final=False):
    super(Property, self).__init__(interface, name)
    self.getter_impl = getter_impl
    self.setter_impl = setter_impl
    self.deleter_impl = deleter_impl
    self.getter_final = getter_final
    self.setter_final = setter_final
    self.deleter_final = deleter_final

  def is_pure_default(self):
    return all(x is not None for x in [self.getter_impl, self.setter_impl, self.deleter_impl])

  def satisfy(self, value):
    assert isinstance(value, property), type(value)
    if value.fget and self.getter_final:
      raise ValueError('propery {}: getter must not be implemented'.format(self.name))
    if value.fset and self.setter_final:
      raise ValueError('propery {}: setter must not be implemented'.format(self.name))
    if value.fdel and self.deleter_final:
      raise ValueError('propery {}: deleter must not be implemented'.format(self.name))
    if self.getter_impl is None and not value.fget:
      raise ValueError('property {}: missing getter'.format(self.name))
    if self.setter_impl is None and not value.fset:
      raise ValueError('property {}: missing setter'.format(self.name))
    if self.deleter_impl is None and not value.fdel:
      raise ValueError('property {}: missing deleter'.format(self.name))

    getter, setter, deleter = value.fget, value.fset, value.fdel
    if not getter and self.getter_impl not in (None, NotImplemented):
      getter = self.getter_impl
    if not setter and self.setter_impl not in (None, NotImplemented):
      setter = self.setter_impl
    if not deleter and self.deleter_impl not in (None, NotImplemented):
      deleter = self.deleter_impl

    return property(getter, setter, deleter)

  @property
  def getter(self):
    return property().getter

  @property
  def setter(self):
    return property().setter

  @property
  def deleter(self):
    return property().deleter

  @classmethod
  def is_candidate(cls, name, value):
    return isinstance(value, property)

  @classmethod
  def wrap_candidate(cls, interface, name, value):
    if cls.is_candidate(name, value):
      return Property.from_python_property(interface, name, value)
    return None

  @classmethod
  def from_python_property(cls, interface, name, value):
    assert isinstance(value, property), type(value)
    if value.fget and getattr(value.fget, '__is_default__', False):
      getter = value.fget
    else:
      getter = None
    if value.fset and getattr(value.fset, '__is_default__', False):
      setter = value.fset
    elif value.fset:
      setter = None
    else:
      setter = NotImplemented
    if value.fdel and getattr(value.fdel, '__is_default__', False):
      deleter = value.fdel
    elif value.fdel:
      deleter = None
    else:
      deleter = NotImplemented
    getter_final = getattr(value.fget, '__is_final__', False)
    setter_final = getattr(value.fset, '__is_final__', False)
    deleter_final = getattr(value.fdel, '__is_final__', False)
    return cls(interface, name, getter, setter, deleter, getter_final,
      setter_final, deleter_final)


class Interface(_meta.InlineMetaclassBase):
  """
  Base class for interfaces. Interfaces can not be instantiated. They are
  not supposed to be inherited by for implementations.
  """

  def __metanew__(cls, name, bases, attrs):
    self = type.__new__(cls, name, bases, attrs)
    self.implementations = set()

    # Convert function declarations in the class to Method objects and
    # bind Attribute objects to the new interface class.
    for key, value in vars(self).items():
      if isinstance(value, _Member) and not value.is_bound:
        value.interface = self
        value.name = key
        continue
      member = Method.wrap_candidate(self, key, value)
      if member is None:
        member = Property.wrap_candidate(self, key, value)
      if member is not None:
        setattr(self, key, member)

    return self

  def __new__(cls):
    msg = 'interface {} can not be instantiated'.format(cls.__name__)
    raise RuntimeError(msg)

  @classmethod
  def implemented_by(cls, instance):
    if not isinstance(instance, Implementation):
      return False
    return instance.implements(cls)


def is_interface(obj):
  return isinstance(obj, type) and issubclass(obj, Interface)


def members_of(interface, include_hidden=False):
  """
  Returns a generator that yields all members of the specified interface.
  Basically, that is all member functions of the interface.
  """

  if not is_interface(interface):
    raise TypeError('expected Interface subclass')

  for name in dir(interface):
    value = getattr(interface, name)
    if isinstance(value, _Member) and (include_hidden or not value.hidden):
      yield value


def has_member(interface, member):
  if (member.startswith('_') and not member.endswith('_')) or \
      member in ('__new__', '__init__'):
    return False
  try:
    value = getattr(interface, member)
  except AttributeError:
    return False
  return isinstance(value, (Method, Attribute))


def get_conflicting_members(a, b):
  """
  Returns a set of members that are conflicting between the two interfaces
  *a* and *b*. If the interfaces have no incompatible members, an empty set
  is returned and both interfaces can be implemented in the same
  implementation.
  """

  if not is_interface(a) or not is_interface(b):
    raise TypeError('expected Interface subclass')
  if issubclass(a, b) or issubclass(b, a):
    return set()

  conflicts = []
  for am in members_of(a):
    try:
      bm = getattr(b, am.name)
    except AttributeError:
      continue
    if am is not bm:
      conflicts.append(am.name)

  return conflicts


def implements(*interfaces):
  """
  This function must be called from the class-level of an implementation. It
  will add the specified interfaces to the implementation.
  """

  class_locals = sys._getframe(1).f_locals
  implements = class_locals.setdefault('__implements__', [])
  for x in interfaces:
    for y in implements:
      if get_conflicting_members(x, y):
        raise ConflictingInterfacesError(x, y)
    if x not in implements:
      implements.append(x)


def attr(type=None):
  """
  Declare an unnamed attribute that will be bound when the interface is
  constructed. The result of this function must be assigned to a member
  on the class-level of an #Interface declaration.
  """

  return Attribute(None, None, type)


def reduce_interfaces(interfaces):
  """
  Reduces a list of interfaces eliminating classes that are parents of
  other classes in the list.
  """

  result = []
  for interface in interfaces:
    skip = False

    for i in range(len(result)):
      if issubclass(interface, result[i]):
        result[i] = interface
        skip = True
        break
      if issubclass(result[i], interface):
        skip = True
        break

    if not skip:
      result.append(interface)

  return result


def default(func):
  """
  Decorator for interface methods to mark them as a default implementation.
  """

  func.__is_default__ = True
  return func


def final(func):
  """
  Decorator for an interface method or property component to mark it as a
  default implementation and that it may not actually be implemented.
  """

  func.__is_default__ = True
  func.__is_final__ = True
  return func


def override(func):
  """
  Marks a function as expecting to be an override for a method in an
  interface. If the function does not override a method in an implemented
  interface, a #RuntimeError will be raised when the #Implementation subclass
  is created.
  """

  func.__is_override__ = True
  return func


class Implementation(_meta.InlineMetaclassBase):
  """
  Parent for classes that implement one or more interfaces.
  """

  def __metanew__(cls, name, bases, attrs):
    implements = attrs.setdefault('__implements__', [])
    implements = reduce_interfaces(implements)

    # Assign default implementations.
    for interface in implements:
      for member in members_of(interface):
        if isinstance(member, Method) and member.name not in attrs and member.impl:
          attrs[member.name] = member.impl

    self = type.__new__(cls, name, bases, attrs)

    # Ensure all interface members are satisfied.
    for interface in implements:
      errors = []
      for member in members_of(interface):
        if isinstance(member, Method):
          if member.final and member.name in attrs and member.impl != attrs[member.name]:
            errors.append('implemented final method: {}()'.format(member.name))
            continue
          if member.name not in attrs:
            errors.append('missing method: {}()'.format(member.name))
          elif not isinstance(attrs[member.name], types.FunctionType):
            errors.append('expected method, got {}: {}()'.format(
              type(attrs[member.name]).__name__, member.name))
        elif isinstance(member, Property):
          if member.name not in attrs:
            if not member.is_pure_default():
              errors.append('missing property: {}'.format(member.name))
          elif not isinstance(attrs[member.name], property):
            errors.append('expected property, got {}: {}'.format(
              type(attrs[member.name]).__name__, member.name))
          else:
            try:
              value = member.satisfy(attrs[member.name])
            except ValueError as exc:
              errors.append(str(exc))
            else:
              setattr(self, member.name, value)
      if errors:
        raise ImplementationError(self, interface, errors)

    # Check member functions for whether they have been marked with
    # the @override decorator.
    for key, value in vars(self).items():
      if not isinstance(value, types.FunctionType):
        continue
      if not getattr(value, '__is_override__', False):
        continue
      for interface in implements:
        if has_member(interface, key):
          break
      else:
        raise RuntimeError("'{}' does not override a method of any of the "
          "implemented interfaces.".format(key))

    # The implementation is created successfully, add it to the
    # implementations set of all interfaces and their parents.
    for interface in implements:
      bases = [interface]
      while bases:
        new_bases = []
        for x in bases:
          if issubclass(x, Interface):
            x.implementations.add(self)
          new_bases += x.__bases__
        bases = new_bases

    return self

  def __init__(self):
    for interface in self.__implements__:
      if hasattr(interface, '__init__'):
        interface.__init__(self)
    for interface in self.__implements__:
      if hasattr(interface, '__constructed__'):
        interface.__constructed__(self)

  @classmethod
  def implements(cls, interface):
    for other in cls.__implements__:
      if issubclass(other, interface):
        return True
    return False


class ImplementationError(RuntimeError):

  def __init__(self, impl, interface, errors):
    self.impl = impl
    self.interface = interface
    self.errors = errors

  def __str__(self):
    lines = []
    lines.append("'{}' does not meet requirements "
                "of interface '{}'".format(self.impl.__name__, self.interface.__name__))
    lines += ['  - {}'.format(x) for x in self.errors]
    return '\n'.join(lines)


class ConflictingInterfacesError(RuntimeError):

  def __init__(self, a, b):
    self.a = a
    self.b = b

  def __str__(self):
    lines = ["'{}' conflicts with '{}'".format(self.a.__name__, self.b.__name__)]
    for member in get_conflicting_members(self.a, self.b):
      lines.append('  - {}'.format(member))
    return '\n'.join(lines)
