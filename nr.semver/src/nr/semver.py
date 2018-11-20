# coding: utf8
# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
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

"""
Semver version and version-specifier types.
"""

import functools
import re


@functools.total_ordering
class Version(object):
  """
  Represents a version number that follows the rules of the semantic
  versioning scheme. The version number can consist of at most the
  following elements: MAJOR . MINOR . PATCH EXTENSION

  The parts of the version number are compared semantically correct
  while the EXTENSION is compared lexically (thus, `1.0-beta10` is
  considered a smaller version number than `1.0-beta2`). Extensions
  are compared case-insensitive. A version number without extension is
  always greater than the respective version number with extension.

  The EXTENSION part must start with a `+`, `-` or `.` character and
  be followed by an alphanumeric letter. Then any number of the former
  plus digits may follow.

  If the extension is preceeded by a `+` or `.`, the version is considered
  higher than a version without the extension, otherwise it is considered
  lower.

  # Attributes
  major (int):
  minor(int):
  path (int):
  extension (str, None): The extension, must be followed by one of
      the characters `+`, `.` or `-`.
  """

  def __init__(self, value):
    if isinstance(value, Version):
      self.parts = value.parts[:]
      self.extension = value.extension
    elif isinstance(value, str):
      match = re.match(r'^(\d+(\.\d+){0,2})([\+\-\.]?[A-z][\w\.\-]*)?$', value)
      if not match:
        raise ValueError("invalid version string: {0!r}".format(value))
      parts = [int(x) for x in match.group(1).split('.')]
      parts.extend(0 for __ in range(3 - len(parts)))
      self.parts = parts
      self.extension = match.group(3) or ''
    else:
      raise TypeError("unexpected type: {0!r}".format(type(value)))

  def __str__(self):
    return '.'.join(map(str, self.parts)) + self.extension

  def __repr__(self):
    return '<Version %r>' % str(self)

  def __lt__(self, other):
    if isinstance(other, Version):
      for a, b in zip(self.parts, other.parts):
        if a < b:
          return True
        elif a > b:
          return False
      assert self.parts == other.parts
      return ({'': 0, '-': -1, '+': 1}[self.norm_ext_prefix], self.norm_ext) <\
        ({'': 0, '-': -1, '+': 1}[other.norm_ext_prefix], other.norm_ext)
    else:
      return NotImplemented

  def __eq__(self, other):
    if isinstance(other, Version):
      if self.parts != other.parts:
        return False
      if self.norm_ext_prefix != other.norm_ext_prefix:
        return False
      if self.norm_ext.lower() != other.norm_ext.lower():
        return False
      return True
    else:
      return NotImplemented

  def __hash__(self):
    return hash(str(self))

  def __getitem__(self, index):
    return self.parts[index]

  def __setitem__(self, index, value):
    self.parts[index] = value

  @property
  def major(self):
    return self.parts[0]

  @major.setter
  def major(self, value):
    self.parts[0] = value

  @property
  def minor(self):
    return self.parts[1]

  @minor.setter
  def minor(self, value):
    self.parts[1] = value

  @property
  def patch(self):
    return self.parts[2]

  @patch.setter
  def patch(self, value):
    self.parts[2] = value

  @property
  def norm_ext_prefix(self):
    if self.extension:
      if self.extension[0] in ('+', '.'): return '+'
      elif self.extension[0] == '-': return '-'
      else: return '+'
    return ''

  @property
  def norm_ext(self):
    if self.extension:
      if self.extension[0] in ('+', '.', '-'): return self.extension[1:]
    return self.extension

  def satisfies(self, spec):
    if isinstance(spec, str):
      spec = Specifier(spec)
    elif not callable(spec):
      raise TypeError("spec: expected str or callable")
    return spec(self)


class _SingleSpecifier(object):

  operators = {
    '*':  None,
    '-':  None,
    'x':  None,
    '=':  lambda a, b: a == b,
    '<':  lambda a, b: a <  b,
    '<=': lambda a, b: a <= b,
    '>':  lambda a, b: a >  b,
    '>=': lambda a, b: a >= b,
    '~':  lambda a, b: a.major == b.major and a.minor == b.minor and a >= b,
    '^':  lambda a, b: a.major == b.major and a >= b,
  }

  def __init__(self, value, version=None):
    self.parts = None
    if isinstance(value, _SingleSpecifier):
      self.op = value.op
      self.version = version(value.version)

    elif isinstance(value, str):
      # Split into parts to check if its a range specifier.
      parts = re.sub('\s+', ' ', value).split(' ')
      if len(parts) == 3 and parts[1] == '-':
        assert version is None
        self.op = '-'
        self.version_min = Version(parts[0])
        self.version = Version(parts[2])
      elif value in self.operators:
        self.op = value
        if value == '*':
          assert version is None
          self.version = self.version_min = None
        elif value == '-':
          if isinstance(value, (list, tuple)):
            self.version_min, self.version = map(Version, value)
          else:
            assert version is None
            self.version_min = self.version = None
        elif value == 'x':
          raise TypeError("can not explicitly initialize with 'x' operator")
        else:
          # Unary operator
          self.version = Version(version)
          self.version_min = None
      elif 'x' in value:
        # Placeholder version number.
        parts = value.split('.')
        if len(parts) <= 3 and '-' in parts[-1]:
          parts[-1:] = parts[-1].split('-', 1)
          parts[-1] = '-' + parts[-1]
        elif len(parts) == 4:
          parts[-1] = '.' + parts[-1]
        parts += ['x' for __ in range(3 - len(parts))]
        if len(parts) < 4: parts.append('-x')
        try:
          if len(parts) > 4: raise ValueError
          parts[:-1] = [int(p) if p != 'x' else 'x' for p in parts[:-1]]
        except ValueError:
          raise ValueError("invalid placeholder specifier: {0!r}".format(value))
        self.op = 'x'
        self.parts = parts
        self.version = None
        self.version_min = None
      else:
        # Match unary operators.
        match = re.match(r'^(=|<=?|>=?|\^|~)(.*)$', value)
        if not match:
          raise ValueError("invalid version specifier: {0!r}".format(value))
        if match.group(2):
          assert version is None
          version = match.group(2).strip()
        if version is not None:
          version = Version(version)
        self.op = match.group(1)
        self.version = version
        self.version_min = None

      if self.op not in ('*', 'x') and self.version is None:
        raise ValueError('operator {0!r} requires version argument'.format(self.op))
      elif self.op == '*' and self.version is not None:
        raise ValueError('operator * does not allow version argument')
      elif self.op == '-' and (self.version is None or self.version_min is None):
        raise ValueError('range operator requires left and right version')
      assert self.op in self.operators

    elif isinstance(value, Version):
      if version is None:
        raise TypeError("specifier() range constructor requires version parameter")
      self.op = '-'
      self.version = Version(value)
      self.version_min = Version(version)

    else:
      raise TypeError("value: expected _SingleSpecifier, Version or str")

  def __str__(self):
    if self.op == '*':
      return '*'
    elif self.op == '-':
      return '{0} - {1}'.format(self.version_min, self.version)
    elif self.op == 'x':
      return '.'.join(map(str, self.parts[:3])) + self.parts[3]
    else:
      return '{0}{1}'.format(self.op, self.version)

  def __call__(self, version):
    if not isinstance(version, Version):
      raise TypeError('version: expected Version')
    if self.op == '*':
      return True
    elif self.op == '-':
      return self.version_min <= version and version <= self.version
    elif self.op == 'x':
      for pcmp, vcmp in zip(self.parts, version.parts):
        if pcmp != 'x' and pcmp != vcmp:
          return False
      return True
    else:
      return self.operators[self.op](version, self.version)


class Specifier(object):
  """
  A version specifier is basically any callable object that accepts
  a :class:`Version` and returns True or False. This class provides
  a specifier that allows filtering versions from the following schema:

      *        := Match any version
      =  V     := Matches a specific version
      <  V     := Match a version that is older than V
      <= V     := Match a version that is older than or equal to V
      >  V     := Match a version that is newer than V
      >= V     := Match a version that is newer than or equal to V
      ~  V     := Match a version with the same major and minor release as V
                  that is also equal to or newer than V
      ^  V     := Match a version with the same major release as V that is
                  also equal to or newer than V
      V1 - V2  := Match any version number between (including) V1 and V2
                  (mind the whitespace around the hyphen!)
      x.x.x-x  := Match a version where "x" can be any number. These
                  placeholders can be placed anywhere, like "x.9.1"
                  or "1.x". Any components that are left out will be
                  filled with placeholders.

  For example, to specify a version that will receive all bug fixes
  and patches, you can use `~2.1.3`. Multiple specifiers can be concatened
  using double pipes (`||`) as in `=1.0 || >2.5 || 0.9 - 1.3.0-rc1`.
  """

  def __init__(self, value):
    if isinstance(value, Specifier):
      self.specifiers = [_SingleSpecifier(x) for x in value.specifiers]
    elif isinstance(value, str):
      items = filter(bool, value.split('||'))
      self.specifiers = [_SingleSpecifier(x.strip()) for x in items]
    else:
      raise TypeError('value: expected Specifier or str')
    if not self.specifiers:
      raise ValueError('invalid Specifier: {!r}'.format(value))

  def __str__(self):
    return ' || '.join(map(str, self.specifiers))

  def __repr__(self):
    return '<%s %s>' % (type(self).__name__, str(self))

  def __call__(self, version):
    return any(c(version) for c in self.specifiers)

  def __len__(self):
    return len(self.specifiers)

  def best_of(self, versions, is_sorted=False):
    if not is_sorted:
      versions = sorted(versions, reverse=True)  # Higher versions first
    for version in versions:
      if self(version):
        return version
    return None
