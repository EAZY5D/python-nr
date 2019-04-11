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
This module provides an AST rewriter that takes and Read/Write operations on
global variables and rewrites them to retrieve the variable by a function
instead. Non-global variables are left untouched.

Example:

    import os
    from os import path

    parent_dir = path.dirname(__file__)

    def main():
      filename = path.join(parent_dir, 'foo.py')
      print(filename)

Will be converted to:

    import os; __dict__['os'] = os
    from os import path; __dict__['path'] = path

    __dict__['parent_dir'] = __dict__['path'].dirname(__dict__['__file__'])

    def main():
      filename = __dict__['path'].join(__dict__['parent_dir'], 'foo.py')
      __dict__['print'](filename)
"""

__all__ = ['dynamic_exec', 'dynamic_eval', 'transform']

import ast
import collections
import textwrap
import sys

from six import exec_, string_types
from six.moves import builtins


def get_argname(arg):
  if isinstance(arg, ast.Name):
    return arg.id
  elif isinstance(arg, str):
    return arg
  elif isinstance(arg, ast.arg):
    # Python 3 where annotations are supported
    return arg.arg
  else:
    raise RuntimeError(ast.dump(arg))


class NameRewriter(ast.NodeTransformer):

  # This code snippet is inserted when using the `from X import *` syntax.
  IMPORT_FROM_ALL_ASSIGN = textwrap.dedent('''
    # We can not use __import__(module, fromlist=[None]) as some modules seem
    # to break with it (see for example nose-devs/nose#1075).
    import importlib as __importlib
    __module = __importlib.import_module({module!r})
    try:
      __vars = __module.__all__
    except AttributeError:
      __vars = [x for x in dir(__module) if not x.startswith('_')]
    for __key in __vars:
      {data_var}[__key] = getattr(__module, __key)
    del __importlib, __module, __vars, __key
  ''')

  def __init__(self, data_var):
    self.data_var = data_var
    self.stack = []

  def __push_stack(self):
    self.stack.append({'external': set(), 'vars': set()})

  def __pop_stack(self):
    self.stack.pop()

  def __is_local(self, name):
    if not self.stack:
      return False
    for frame in reversed(self.stack):
      if name in frame['external']:
        return False
      if name in frame['vars']:
        return True
    return False

  def __add_variable(self, name):
    assert isinstance(name, string_types), name
    if self.stack and name not in self.stack[-1]['external']:
      self.stack[-1]['vars'].add(name)

  def __add_external(self, name):
    if self.stack:
      self.stack[-1]['external'].add(name)

  def __get_subscript(self, name, ctx=None):
    """
    Returns `<data_var>["<name>"]`
    """

    assert isinstance(name, string_types), name
    return ast.Subscript(
      value=ast.Name(id=self.data_var, ctx=ast.Load()),
      slice=ast.Index(value=ast.Str(s=name)),
      ctx=ctx)

  def __get_subscript_assign(self, name):
    """
    Returns `<data_var>["<name>"] = <name>`.
    """

    return ast.Assign(
      targets=[self.__get_subscript(name, ast.Store())],
      value=ast.Name(id=name, ctx=ast.Load()))

  def __get_subscript_delete(self, name):
    """
    Returns `del <data_var>["<name>"]`.
    """

    return ast.Delete(targets=[self.__get_subscript(name, ast.Del())])

  def __visit_target(self, node):
    """
    Call this method to visit assignment targets and to add local variables
    to the current stack frame. Used in #visit_Assign() and
    #__visit_comprehension().
    """

    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
      self.__add_variable(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
      [self.__visit_target(x) for x in node.elts]

  def __visit_suite(self, node):
    result = node
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
      self.__add_variable(node.name)
      if not self.__is_local(node.name):
        assign = self.__get_subscript_assign(node.name)
        result = [node, ast.copy_location(assign, node)]

    self.__push_stack()

    if sys.version_info[0] > 2 and isinstance(node, ast.ClassDef):
      # TODO: This is a bit of a dirty hack to make sure that super and
      #       __class__ are considered as local variables in functions.
      self.__add_variable('super')
      self.__add_variable('__class__')

    if isinstance(node, (ast.FunctionDef, ast.Lambda)):  # Also used for ClassDef
      for arg in node.args.args + getattr(node.args, 'kwonlyargs', []):  # Python 2
        self.__add_variable(get_argname(arg))
      if node.args.vararg:
        self.__add_variable(get_argname(node.args.vararg))
      if node.args.kwarg:
        self.__add_variable(get_argname(node.args.kwarg.arg))

    self.generic_visit(node)
    self.__pop_stack()
    return result

  def __visit_comprehension(self, node):
    # In Python 3, comprehensions have their own scope.
    has_own_scope = (sys.version_info[0] > 2)

    if has_own_scope:
      self.__push_stack()
    for comp in node.generators:
      self.__visit_target(comp.target)
    self.generic_visit(node)
    if has_own_scope:
      self.__pop_stack()
    return node

  def visit_Name(self, node):
    if not self.__is_local(node.id):
      node = ast.copy_location(self.__get_subscript(node.id, node.ctx), node)
    return node

  def visit_Assign(self, node):
    for target in node.targets:
      self.__visit_target(target)
    self.generic_visit(node)
    return node

  def visit_Import(self, node):
    assignments = []
    for alias in node.names:
      name = (alias.asname or alias.name).split('.')[0]
      assignments.append(self.__get_subscript_assign(name))
    return [node] + [ast.copy_location(x, node) for x in assignments]

  def visit_ImportFrom(self, node):
    assignments = []
    for alias in node.names:
      name = alias.asname or alias.name
      if name == '*':
        code = self.IMPORT_FROM_ALL_ASSIGN.format(module=node.module, data_var=self.data_var)
        module = ast.parse(code)
        assignments += module.body
      else:
        assignments.append(self.__get_subscript_assign(name))
    return [node] + [ast.copy_location(x, node) for x in assignments]

  def visit_ExceptHandler(self, node):
    if node.name:
      self.__add_variable(get_argname(node.name))  # Python 2 has an ast.Name here, Python 3 just a string
    self.generic_visit(node)
    if not self.stack and node.name and sys.version_info[0] > 2:
      # In Python 2, the node.name will already be replaced with a subscript
      # by #visit_Name().
      node.body.insert(0, ast.copy_location(self.__get_subscript_assign(node.name), node))
      if sys.version_info[0] == 3:
        node.body.append(ast.copy_location(self.__get_subscript_delete(node.name), node))
    return node

  def visit_With(self, node):
    if hasattr(node, 'items'):
      optional_vars = [x.optional_vars for x in node.items]
    else:
      # Python 2
      optional_vars = [node.optional_vars]
    [self.__visit_target(x) for x in optional_vars if x]
    self.generic_visit(node)
    return node

  def visit_For(self, node):
    self.__visit_target(node.target)
    self.generic_visit(node)
    return node

  visit_FunctionDef = __visit_suite
  visit_Lambda = __visit_suite
  visit_ClassDef = __visit_suite

  visit_ListComp = __visit_comprehension
  visit_SetComp = __visit_comprehension
  visit_GeneratorExp = __visit_comprehension
  visit_DictComp = __visit_comprehension

  def visit_Global(self, node):
    for name in node.names:
      self.__add_external(name)


def transform(ast_node, data_var='__dict__'):
  ast_node = NameRewriter(data_var).visit(ast_node)
  ast_node = ast.fix_missing_locations(ast_node)
  return ast_node


def dynamic_exec(code, mapping, automatic_builtins=True,
                 filename=None, module_name=None, _type='exec'):
  """
  Transforms the Python source code *code* and evaluates it so that the
  all global variables are accessed through the specified *mapping*.

  It is recommended to use the #DynamicMapping class.
  """

  parse_filename = filename or '<string>'
  ast_node = transform(ast.parse(code, parse_filename, mode=_type))
  code = compile(ast_node, parse_filename, _type)

  globals_ = {'__dict__': mapping}

  if filename:
    mapping['__file__'] = filename
    globals_['__file__'] = filename

  if module_name:
    mapping['__name__'] = module_name
    globals_['__name__'] = module_name

  return (exec_ if _type == 'exec' else eval)(code, globals_)


def dynamic_eval(*args, **kwargs):
  return dynamic_exec(*args, _type='eval', **kwargs)


class DynamicMapping(object):
  """
  This dictionary can be used as the global `__dict__` for code that has
  been transformed with #transform(). It will translate failed lookups into
  #NameError#s and properly fall back to the Python builtins.
  """

  # Members of the builtins module that should not be exposed with the
  # automatic_builtins feature.
  _PRIVATE_BUILTINS_MEMBERS = [
    '__build_class__', '__doc__', '__loader__', '__name__',
    '__package__', '__spec__', '__class__'
  ]

  def __init__(self, target=None, automatic_builtins=True):
    if target is None:
      target = {}
    self._data = target
    self._deleted = set()
    self._automatic_builtins = automatic_builtins

  def __repr__(self):
    return 'DynamicMapping({!r})'.format(self._data)

  def __contains__(self, key):
    if key in self._deleted:
      return False
    if key in self._data:
      return True
    if self._automatic_builtins and not is_private_member(key):
      return hasattr(builtins, key)
    return False

  def __getitem__(self, key):
    if key in self._deleted:
      raise NameError(key)
    try:
      return self._data[key]
    except KeyError:
      pass
    if self._automatic_builtins \
        and key not in self._PRIVATE_BUILTINS_MEMBERS\
        and not is_private_member(key):
      try:
        return getattr(builtins, key)
      except AttributeError:
        pass
    raise NameError(key)

  def __setitem__(self, key, value):
    self._deleted.discard(key)
    self._data[key] = value

  def __delitem__(self, key):
    try:
      self._data.pop(key)
    except KeyError:
      raise UnboundLocalError("local variable '{}' referenced before assignment".format(key))
    self._deleted.add(key)

  def get(self, key, default=None):
    try:
      return self[key]
    except NameError:
      return default


def is_private_member(name):
  return name.startswith('_') and not (name.startswith('__') and name.endswith('__'))
