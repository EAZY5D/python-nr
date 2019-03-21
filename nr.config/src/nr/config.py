
"""
This module implements a class-oriented API for defining configuration parsers.
"""

from nr.stream import stream
import copy
import six
import weakref

try: import typing
except ImportError: typing = None

try: from collections.abc import Mapping, Sequence
except ImportError: from collections import Mapping, Sequence

PARTIAL_FIELDS = '_fields_'
PARTIAL_FIELDS_DICT = '_fields_dict_'


def _no_default():
  raise NotImplementedError


def render_type_spec(spec):
  if isinstance(spec, tuple):
    return '{' + ', '.join(x.__name__ for x in spec) + '}'
  return spec.__name__


class IgnoreField(Exception):
  pass


class Context(object):
  """
  The context stores information that may be of interest to a #TypeHandler
  object while it is loading or dumping an object. An existing #Context
  object should only be modified if the current branch is already processed
  and no child context objects are still alive (as otherwise their cached
  #path property would become invalid).
  """

  @classmethod
  def mkroot(cls, *args, **kwargs):
    """
    Creates a new #Context object where the *handler_collection*
    parameter defaults to the #root_handler_collection.
    """

    kwargs.setdefault('handler_collection', root_handler_collection)
    return cls(*args, **kwargs)

  def __init__(self, parent, key, filename=None, handler_collection=None,
         avoid_copy=None):
    if parent is None:
      if avoid_copy is None:
        avoid_copy = False
      if handler_collection is None:
        raise ValueError('handler_collection must be set for a root context')
    else:
      if avoid_copy is None:
        avoid_copy = parent.avoid_copy
      if filename is None:
        filename = parent.filename
      if handler_collection is None:
        handler_collection = parent.handler_collection

    self.parent = parent
    self.avoid_copy = parent.avoid_copy if avoid_copy is None else avoid_copy
    self.filename = filename
    self.handler_collection = handler_collection
    self._key = key
    self._children = []
    self._path = None

    if parent is not None:
      parent._children.append(weakref.ref(self))

  def __repr__(self):
    return 'Context(path={!r}, filename={!r})'.format(self.path, self.filename)

  def upiter(self):
    while self:
      yield self
      self = self.parent

  @property
  def path(self):
    if self._path is None:
      result = []
      for ctx in self.upiter():
        result.append(ctx.key)
      if result[-1] is None:
        result.pop()
      result.reverse()
      self._path = result
    return self._path

  @property
  def readable_path(self):
    path = '.'.join(repr(x) if '.' in x else x for x in map(str, self.path))
    if not path:
      path = '<root>'
    return path

  @property
  def key(self):
    return self._key

  @key.setter
  def key(self, value):
    # No children must be still alive.
    if any(x() is not None for x in self._children):
      raise RuntimeError('can not mutate Context.key while there are '
        'children alive.')
    self._children[:] = ()
    self._key = value
    self._path = None

  def type_error(self, got, expected):
    if not isinstance(got, type):
      got = type(got)
    got = render_type_spec(got)
    expected = render_type_spec(expected)
    return TypeError('{}: expected {}, got {}'.format(
      self.readable_path, expected, got))

  def value_error(self, msg):
    raise ValueError('{}: {}'.format(self.readable_path, msg))


class TypeHandler(object):
  """
  A type handler matches a specific type declaration and then implements
  the loading and dumping of this type from and to a plain datatype
  representation (one that can be serialized by eg. JSON or YAML).
  """

  @classmethod
  def match(self, type_decl):  # type: (Any) -> TypeHandler
    raise NotImplementedError

  def load(self, data, context):  # type: (Any, Context) -> Any
    raise NotImplementedError

  def dump(self, obj, context):  # type: (Any, Context) -> Any
    raise NotImplementedError


class BasicTypeHandler(TypeHandler):
  """
  A handler for basic types.
  """

  ACCEPTED_TYPES = (str, int, float, dict, list, tuple)

  def __init__(self, basic_type):
    self.type = basic_type

  @classmethod
  def match(self, type_decl):
    if type_decl in self.ACCEPTED_TYPES:
      return self(type_decl)
    return None

  def load(self, data, context):
    if not isinstance(data, self.type):
      raise context.type_error(type(data), self.type)
    if not context.avoid_copy:
      data = copy.deepcopy(data)
    return data

  def dump(self, obj, context):
    if not isinstance(obj, self.type):
      raise context.type_error(type(obj), self.type)
    if not context.avoid_copy:
      obj = copy.deepcopy(obj)
    return obj


class GenericTypeHandler(TypeHandler):
  """
  A handler for list, tuple and dict generics, either declared via the the
  #typing.List, #typing.Tuple or #typing.Dict generics or using tuples (for
  Python 2 where the #typing module does not exist), eg in the form of
  `(dict, str, MyPartial)` which is equal to `Dict[str, MyPartial]`.

  The `dict` will actually represent an arbitrary mapping object
  (#Mapping) and list and `tuple` will both map to arbitrary sequences
  (#Sequence).
  """

  def __init__(self, base_type, arg1, arg2):
    assert base_type in (list, tuple, dict), base_type
    assert isinstance(arg1, type)
    if base_type is dict:
      assert isinstance(arg2, type)
    else:
      assert arg2 is None
    self.base_type = base_type
    self.arg1 = arg1
    self.arg2 = arg2
    self.validation_type = {list: Sequence, tuple: Sequence, dict: Mapping}[base_type]

  @classmethod
  def match(self, type_decl):
    if typing is not None:
      origin = getattr(type_decl, '__origin__', type_decl)
      mapping = {typing.List: list, typing.Tuple: tuple, typing.Dict: dict}
      if origin not in origin:
        return None
      base_type = mapping[origin]
      arg1, arg2 = (tuple(type_decl.__args__) + (None,))[:2]
    elif isinstance(type_decl, (list, tuple)):
      if not type_decl or len(type_decl) > 3:
        return None
      base_type, arg1 = type_decl[:2]
      arg2 = type_decl[2] if len(type_decl) == 3 else None
    else:
      return None
    return self(base_type, arg1, arg2)

  def load(self, data, context, _op='load'):
    if not isinstance(data, self.validation_type):
      raise context.type_error(data, self.validation_type)
    if self.validation_type == Sequence:
      result = []
      handler = context.handler_collection.resolve(self.arg1)
      operation = getattr(handler, _op)
      for index, item in enumerate(data):
        try:
          result.append(operation(item, Context(context, index)))
        except IgnoreField:
          pass
      return result
    elif self.validation_type == Mapping:
      result = {}
      key_handler = context.handler_collection.resolve(self.arg1)
      key_operation = getattr(key_handler, _op)
      value_handler = context.handler_collection.resolve(self.arg2)
      value_operation = getattr(value_handler, _op)
      for key, value in six.iteritems(data):
        try:
          key = key_operation(key, Context(context, key))
          value = value_operation(value, Context(context, key))
        except IgnoreField:
          pass
        else:
          result[key] = value
      return result
    else:
      raise RuntimeError

  def dump(self, obj, context):
    return self.load(obj, context, _op='dump')


class InheritKeyTypeHandler(TypeHandler):

  def match(self, type_decl):
    if isinstance(type_decl, InheritKeyTypeHandler):
      return type_decl
    return None

  def load(self, data, context):
    return context.key

  def dump(self, obj, context):
    raise IgnoreField()


class WildcardTypeHandler(GenericTypeHandler):

  def __init__(self, key_type_decl, value_type_decl):
    super(WildcardTypeHandler, self).__init__(dict, key_type_decl, value_type_decl)

  @classmethod
  def match(self, type_decl):
    if isinstance(type_decl, WildcardTypeHandler):
      return type_decl
    return None


class TypeHandlerCollection(object):
  """
  Represents a collection of #TypeHandler subclasses.
  """

  def __init__(self):
    self.handlers = []

  def register(self, handler):
    assert issubclass(handler, TypeHandler)
    if handler in self.handlers:
      raise ValueError('{} is already registered'.format(handler))
    self.handlers.append(handler)

  def resolve(self, type_decl):
    if isinstance(type_decl, TypeHandler):
      return type_decl
    for handler in self.handlers:
      instance = handler.match(type_decl)
      if instance is not None:
        return instance
    raise ValueError('no TypeHandler available for type_decl={!r}'
      .format(type_decl))

  def load(self, type_decl, data, context=None):
    if context is None:
      context = Context(None, None, handler_collection=self)
    else:
      assert context.handler_collection
      self = context.handler_collection
    handler = self.resolve(type_decl)
    return handler.load(data, context)

  def dump(self, type_decl, obj, context=None):
    if context is None:
      context = Context(None, None, handler_collection=self)
    else:
      assert context.handler_collection
      self = context.handler_collection
    handler = self.resolve(type_decl)
    return handler.dump(obj, context)


class Field(object):

  @staticmethod
  def __new_creation_index():
    idx = getattr(Field, '_Field__creation_index', 0)
    try:
      return idx
    finally:
      setattr(Field, '_Field__creation_index', idx + 1)

  def __init__(self, type_decl, default=_no_default, nullable=None, name=None):
    self.type_decl = type_decl
    self.default = default
    self.nullable = (True if default is None else (nullable or False))
    self._name = name  # type: str
    self.dest = None  # type: str
    self._owner = None  # type: weakref.ref[Type[Partial]]
    self._creation_index = self.__new_creation_index()

  def __repr__(self):
    tname = str(self.type_decl)  # TODO @nrosenstein Nice repr of Field type
    oname = self.owner.__name__ if self.owner else None
    return 'Field({!r}, type={}, required={}, owner={})'.format(
      self.name, tname, self.required, oname)

  def with_default(self, default=NotImplemented):
    if default is NotImplemented:
      assert callable(self.type_decl)
      default = self.type_decl
    self.default = default
    return self

  def get_default(self):
    if callable(self.default):
      return self.default()
    return self.default

  def duplicate(self):
    obj = copy.copy(self)
    obj._owner = None
    return obj

  @property
  def required(self):
    return self.default is _no_default

  @property
  def name(self):
    return self._name or self.dest

  @property
  def owner(self):
    return None if self._owner is None else self._owner()

  @owner.setter
  def owner(self, value):
    assert isinstance(value, type) and issubclass(value, Partial)
    self._owner = weakref.ref(value)

  @classmethod
  def inherit_key(cls, name=None):
    return cls(InheritKeyTypeHandler(), name=name)

  @classmethod
  def wildcard(cls, key_type_decl, value_type_decl):
    return cls(WildcardTypeHandler(key_type_decl, value_type_decl), default=dict)


class _PartialMeta(type):

  def __new__(self, name, bases, dict_):
    fields = []
    # Merge all fields from parent partials and the current classes'
    # fields into one list.
    for base in bases:
      fields.extend(getattr(base, PARTIAL_FIELDS, []))
    for key, value in six.iteritems(dict_):
      if isinstance(value, Field):
        value.dest = key
        fields.append(value)
    # Collapse fields from the right to remove duplicate fields in case
    # a field is overwritten.
    fields[:] = reversed(list(stream.unique(reversed(fields), key=lambda x: x.name)))
    # Duplicate fields if they are inherited from a parent partial.
    fields = [x if x.owner is None else x.duplicate() for x in fields]
    # Ensure the fields all propagated to the current class dict.
    for f in fields:
      dict_[f.name] = f
    fields.sort(key=lambda x: x._creation_index)
    dict_[PARTIAL_FIELDS] = fields
    dict_[PARTIAL_FIELDS_DICT] = {x.dest: x for x in fields}
    return super(_PartialMeta, self).__new__(self, name, bases, dict_)

  def __init__(self, name, bases, dict_):
    # Initialize Field owner.
    for field in getattr(self, PARTIAL_FIELDS):
      assert field.owner is None
      field.owner = self


class Partial(six.with_metaclass(_PartialMeta)):

  __load_context__ = None

  def __init__(self, *args, **kwargs):
    fields = getattr(type(self), PARTIAL_FIELDS)
    fields_dict = getattr(type(self), PARTIAL_FIELDS_DICT)
    argcount = len(args) + len(kwargs)
    if argcount > len(fields):
      raise TypeError('expected at max {} arguments, got {}'.format(
        len(fields), argcount))
    for field, arg in zip(fields, args):
      if field.dest in kwargs:
        raise TypeError('duplicate argument {} provided'.format(field.dest))
      kwargs[field.dest] = arg
    for field in fields:
      if field.dest not in kwargs:
        if field.required:
          raise TypeError('missing required argument {}'.format(field.dest))
        kwargs[field.dest] = field.get_default()
    for key in kwargs:
      if key not in fields_dict:
        raise TypeError('unexpected keyword argument {}'.format(key))
    vars(self).update(kwargs)

  def __repr__(self):
    fields = getattr(type(self), PARTIAL_FIELDS)
    d = {f.dest: getattr(self, f.dest) for f in fields}
    return '{}({})'.format(type(self).__name__, d)


class PartialTypeHandler(TypeHandler):

  def __init__(self, partial):
    assert issubclass(partial, Partial)
    self.partial = partial

  @classmethod
  def match(self, type_decl):
    if issubclass(type_decl, Partial):
      return self(type_decl)
    return None

  def load(self, data, context):
    if not isinstance(data, (Mapping, self.partial)):
      raise context.type_error(data, (Mapping, self.partial))
    if isinstance(data, self.partial):
      return data  # TODO @nrosenstein Should we copy it?

    # Collect the parameters for the partial constructor here.
    kwargs = {}
    # TODO @nrosenstein Can we implements wildcards by extending the
    #       TypeHandler and Context APIs instead of handling them
    #       special here?
    #       Same goes for inherit key fields.
    wildcards = []
    for field in getattr(self.partial, PARTIAL_FIELDS):
      if isinstance(field.type_decl, WildcardTypeHandler):
        wildcards.append(field)
      elif isinstance(field.type_decl, InheritKeyTypeHandler):
        value = field.type_decl.load(None, context)
      elif field.name in data:
        if data[field.name] is None and field.nullable:
          value = None
        else:
          handler = context.handler_collection.resolve(field.type_decl)
          value = handler.load(data[field.name], Context(context, field.name))
      elif not field.required:
        try:
          value = field.get_default()
        except (TypeError, ValueError) as exc:
          raise type(exc)('{}: {}'.format(context.readable_path, exc))
      else:
        raise context.value_error('missing required field {}'.format(field.name))
      kwargs[field.dest] = value
    if len(wildcards) > 1:
      raise RuntimeError('{} has multiple wildcard fields'.format(self.partial))
    if wildcards:
      data = {k: v for k, v in data.items() if k not in kwargs}
      field = wildcards[0]
      kwargs[field.dest] = field.type_decl.load(data, context)
    obj = self.partial(**kwargs)
    obj.__load_context__ = context
    return obj

  def dump(self, obj, context):
    assert isinstance(obj, self.partial)
    data = {}
    for field in getattr(self.partial, PARTIAL_FIELDS):
      value = getattr(obj, field.dest)
      if value is not None:
        handler = context.handler_collection.resolve(field.type_decl)
        try:
          data[field.name] = handler.dump(value, Context(context, field.name))
        except IgnoreField:
          pass
    return data

# Global state.

root_handler_collection = TypeHandlerCollection()


def register_type_handler(handler):
  """
  Registers a #TypeHandler to the #root_handler_collection.
  """

  return root_handler_collection.register(handler)


def resolve_type_decl(type_decl):
  """
  Resolves a type declaration to a #TypeHandler instances from the
  #root_handler_collection or raises a #ValueError.
  """

  return root_handler_collection.resolve(type_decl)


register_type_handler(BasicTypeHandler)
register_type_handler(GenericTypeHandler)
register_type_handler(PartialTypeHandler)


def extract(type_decl, arg, filename=None, data=None, handler_collection=None):
  """
  A convenient function that loads a JSON, CSON or YAML configuration file
  (based on the file suffix, falling back to JSON) and loads it using
  the specified *type_decl* and *handler_collection*.

  The *arg* will be treated as the *filename* if it is a string or
  otherwise as the *data* parameter.
  """

  if arg is not None:
    if isinstance(arg, str):
      filename = arg
    else:
      data = arg

  if data is None:
    if filename is None:
      raise ValueError('no data to load')
    with open(filename) as fp:
      # TODO @nrosenstein Load objects into ordered dicts.
      if filename.endswith('.yml') or filename.endswith('.yaml'):
        import yaml
        data = yaml.load(fp)
      elif filename.endswith('.cson'):
        import cson
        data = cson.load(fp)
      else:
        import json
        data = json.load(fp)

  if handler_collection is None:
    handler_collection = root_handler_collection

  context = Context(None, None, filename=filename,
    handler_collection=handler_collection)
  return handler_collection.load(type_decl, data, context)


def dump(type_decl, obj, filename=None):
  context = Context(None, None, filename=filename,
    handler_collection=root_handler_collection)
  return root_handler_collection.dump(type_decl, obj, context)
