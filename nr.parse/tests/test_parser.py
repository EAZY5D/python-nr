
from nr import parse

def test_seek():
  s = parse.Scanner("foo\nbar")
  assert s.char == 'f'
  assert s.cursor == parse.Cursor(0, 1, 0)

  s.next()
  assert s.char == 'o'
  assert s.cursor == parse.Cursor(1, 1, 1)

  s.seek(5)
  assert s.char == 'a'
  assert s.cursor == parse.Cursor(5, 2, 1)

  s.seek(-1, 'cur')
  assert s.char == 'b'
  assert s.cursor == parse.Cursor(4, 2, 0)

  s.seek(-1, 'cur')
  assert s.char == '\n'
  assert s.cursor == parse.Cursor(3, 1, 3)

  s.seek(-1, 'cur')
  assert s.char == 'o'
  assert s.cursor == parse.Cursor(2, 1, 2)

  s.seek(-1, 'cur')
  assert s.char == 'o'
  assert s.cursor == parse.Cursor(1, 1, 1)

  s.seek(-1, 'cur')
  assert s.char == 'f'
  assert s.cursor == parse.Cursor(0, 1, 0)

  # At the start, seek ingored.
  s.seek(-1, 'cur')
  assert s.char == 'f'
  assert s.cursor == parse.Cursor(0, 1, 0)

  s.seek(0, 'end')
  assert s.char == ''
  assert s.cursor == parse.Cursor(7, 2, 3)

  s.seek(-20, 'cur')
  assert s.char == 'f'
  assert s.cursor == parse.Cursor(0, 1, 0)


def test_match():
  s = parse.Scanner('foobar')
  assert not s.match('bar')
  assert s.index == 0

  m = s.match('.oo')
  assert m is not None
  assert m.start() == 0
  assert m.group(0) == 'foo'

  m = s.match('.*')
  assert m is not None
  assert m.start() == 3
  assert s.index == 6
  assert m.group(0) == 'bar'


def test_search():
  s = parse.Scanner('foobar')
  m = s.search('ba.')
  assert m is not None
  assert m.start() == 3
  assert m.group(0) == 'bar'
  assert s.index == 6
