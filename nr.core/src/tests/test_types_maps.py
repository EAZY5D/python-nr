
from nr.core.types.maps import ChainMap, MapAsObject


def test_ChainDict():
  a = {'foo': 42}
  b = {'bar': 'spam'}
  c = {}
  d = ChainMap({}, a, b, c)

  assert str(d) == 'ChainMap({})'.format({'foo': 42, 'bar': 'spam'})
  assert d['foo'] == a['foo']
  assert d['bar'] == b['bar']
  assert sorted(d.keys()) == ['bar', 'foo']

  d['hello'] = 'World'
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {'foo': 42, 'bar': 'spam', 'hello': 'World'}

  del d['foo']
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {'bar': 'spam', 'hello': 'World'}

  d['foo'] = 99
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {'foo': 99, 'bar': 'spam', 'hello': 'World'}

  d.clear()
  assert a == {'foo': 42}
  assert b == {'bar': 'spam'}
  assert c == {}
  assert d == {}


def test_ObjectFromMapping():
  d = ChainMap({'a': 42, 'b': 'foo'}, {'c': 'egg'})
  o = MapAsObject(d)
  assert o.a == 42
  assert o.b == 'foo'
  assert o.c == 'egg'
  assert dir(o), ['a', 'b', 'c']
