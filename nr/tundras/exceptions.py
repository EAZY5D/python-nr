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


class ValidationError(Exception):
  """
  This exception is thrown when a field's data is invalid, ie. the
  #.field.Field.type function raised either a #ValueError or #TypeError.
  """

  def __init__(self, field, value, error):
    self.field = field
    self.value = value
    self.error = error

  def __str__(self):
    return '{0!r}: {1}'.format(self.field.full_name, self.error)


class EntityInitializationError(TypeError):
  """
  This exception is raised when an entity could not be initialize
  properly due to missing field values or superfluous/duplicate ones.
  """

  def __init__(self, message=None, field=None):
    self.message = message
    self.field = field

  def __str__(self):
    if self.field:
      result = repr(self.field.full_name)
    else:
      result = ''
    if self.message:
      if result:
        result += ': '
      result += str(self.message)
    return result
