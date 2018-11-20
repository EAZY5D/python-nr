
import copy
import pkg_resources
import nr.parse
import nr.types.sumtype as sumtype
import re
import six
import termcolor

PLUGINS_ENTRYPOINT = 'nr.powerline.plugins'
COLORMODE_ASCII = 'ascii'
COLORMODE_TRUECOLOR = 'truecolor'


@six.python_2_unicode_compatible
class PowerLine(object):

  def __init__(self):
    self._parts = []
    self._plugins = {}
    self._colors = {}
    self._color_mode = COLORMODE_ASCII
    self._pen = Pen()
    self._drawops = []

  def __str__(self):
    result = [termcolor.RESET]
    pen = Pen()
    for i, op in enumerate(self._drawops):
      if op.is_set_pen():
        new_pen = op.pen
      elif op.is_propagate_bg():
        # Look ahead for the next foreground color.
        new_pen = pen.copy()
        new_pen.fg = new_pen.bg
        new_pen.attrs = []
        for anop in self._drawops[i:]:
          if anop.is_set_pen():
            new_pen.bg = anop.pen.bg
            break
        else:
          new_pen.bg = None
      elif op.is_blit_text():
        result.append(render_format_string(op.text, _LazyPluginDict(self)))
      else:
        assert False, op
      if pen != new_pen:
        result.append(self.get_color_transition_codes(pen, new_pen))
        pen = new_pen
    result.append(termcolor.RESET)
    return u''.join(result)

  @property
  def color_mode(self):
    return self._color_mode

  @color_mode.setter
  def color_mode(self, value):
    assert value in (COLORMODE_ASCII, COLORMODE_TRUECOLOR), repr(value)
    self._color_mode = value

  @property
  def colors(self):
    return _ColorDict(self._colors)

  def add_color(self, name, value):
    self.colors[name] = value

  def get_plugin(self, name):
    if name not in self._plugins:
      for ep in pkg_resources.iter_entry_points(PLUGINS_ENTRYPOINT, name):
        self._plugins[name] = ep.load()()
        break
      else:
        return None
    return self._plugins[name]

  def set_pen(self, fg=NotImplemented, bg=NotImplemented, *attrs):
    self._pen.update(fg, bg, attrs)
    self._drawops.append(DrawOp.SetPen(self._pen.copy()))

  def clear_pen(self):
    self._pen.clear()

  def add_part(self, part_format):
    scanner = nr.parse.Scanner(part_format)
    start = scanner.index
    while scanner:
      if scanner.char == '!':
        self._drawops.append(DrawOp.BlitText(part_format[start:scanner.index]))
        start = scanner.index + 1
        self._drawops.append(DrawOp.PropagateBg())
      scanner.next()
    self._drawops.append(DrawOp.BlitText(part_format[start:scanner.index]))

  def get_color_code(self, name, foreground=True):
    if self._color_mode == COLORMODE_TRUECOLOR and name in self._colors:
      # TODO @NiklasRosenstein
      return ''
    mapping = termcolor.COLORS if foreground else termcolor.HIGHLIGHTS
    prefix = '' if foreground else 'on_'
    if prefix + name not in mapping:
      return ''
    return '\033[%dm' % mapping.get(prefix + name)

  def get_color_transition_codes(self, curr, pen):
    # TODO @NiklasRosenstein We should be able to compute only the terminal
    #   instructions to change to the new colors instead of re-writing all
    #   color instructions.
    result = termcolor.RESET
    if pen.fg:
      result += self.get_color_code(pen.fg, True)
    if pen.bg:
      result += self.get_color_code(pen.bg, False)
    if pen.attrs:
      for attr in pen.attrs:
        result += '\033[%dm' % termcolor.ATTRIBUTES.get(attr, '')
    return result


class Pen(object):

  def __init__(self, fg=None, bg=None, attrs=None):
    self.fg = fg
    self.bg = bg
    self.attrs = attrs or []

  def __repr__(self):
    return 'Pen(fg={!r}, bg={!r}, attrs={!r})'.format(self.fg, self.bg, self.attrs)

  def __eq__(self, other):
    if type(other) is Pen:
      return (self.fg, self.bg, self.attrs) == (other.fg, other.bg, other.attrs)
    return False

  def __ne__(self, other):
    return not (self == other)

  def update(self, fg=NotImplemented, bg=NotImplemented, attrs=NotImplemented):
    if fg is not NotImplemented:
      self.fg = fg
    if bg is not NotImplemented:
      self.bg = bg
    if attrs is not NotImplemented:
      if attrs is None:
        attrs = []
      elif not isinstance(attrs, (list, tuple)):
        attrs = [attrs]
      self.attrs = attrs

  def clear(self):
    self.fg = None
    self.bg = None
    self.attrs = []

  def copy(self):
    return copy.deepcopy(self)


class TrueColor(object):

  def __init__(self, value):
    if isinstance(value, str):
      if value.startswith('#'):
        v = value[1:]
        if len(v) == 3:
          r, g, b = v
          r *= 2
          g *= 2
          b *= 2
        elif len(v) == 6:
          r, g, b = v[0:2], v[2:4], v[4:6]
        else:
          raise ValueError('invalid RGB color: {!r}'.format(value))
        r, g, b = int(r, 16), int(g, 16), int(b, 16)
      else:
        raise ValueError('invalid RGB color: {!r}'.format(value))
    elif isinstance(value, Color):
      r, g, b = value.r, value.g, value.b
    else:
      raise TypeError('unexpected type {}'.format(type(value).__name__))
    self.r = r
    self.g = g
    self.b = b

  def __repr__(self):
    return 'TrueColor(r={}, g={}, b={})'.format(self.r, self.g, self.b)


class _ColorDict(object):

  def __init__(self, colors):
    self._colors = colors

  def __getitem__(self, name):
    return self._colors[name]

  def __setitem__(self, name, value):
    self._colors[name] = TrueColor(value)

  def __delitem__(self, name):
    del self._colors[name]


class _LazyPluginDict(object):

  def __init__(self, powerline):
    self._powerline = powerline

  def __getitem__(self, key):
    plugin = self._powerline.get_plugin(key)
    if plugin is None:
      raise KeyError(key)
    return plugin


class DrawOp(sumtype.Sumtype):
  PropagateBg = sumtype.Constructor()  # Indicated by the "!" character in a format string
  SetPen = sumtype.Constructor('pen')
  BlitText = sumtype.Constructor('text')


def render_format_string(fmt_string, values):
  """
  Similar to :meth:`str.format`. Can read from arbitrary dictionary-like
  objects. Replaces non-existent values with the same syntax string.
  """

  expr = '\{(.*?)\}'

  def subst_func(m):
    parts = m.group(1).split('.')
    try:
      value = values[parts[0]]
    except KeyError:
      return '{' + m.group(1) + '}'
    for part in parts[1:]:
      try:
        value = getattr(value, part)
      except AttributeError:
        return '{' + m.group(1) + '}'
    return six.text_type(value)

  return re.sub(expr, subst_func, fmt_string)
