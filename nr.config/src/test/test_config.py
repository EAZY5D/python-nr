
from nr import config
from pytest import raises


def test_context_mutation():
    Context = config.Context
    c1 = Context.mkroot(None, None, filename='foobar.yml')
    c2 = Context(c1, 'host')
    c3 = Context(c1, 'token')
    c4 = Context(c3, 'name')
    c5 = Context(c3, 'value')
    assert c1.path == []
    assert c2.path == ['host']
    assert c3.path == ['token']
    assert c4.path == ['token', 'name']
    assert c5.path == ['token', 'value']
    assert c5.filename == 'foobar.yml'

    # Mutating the "host" key works because no children are alive.
    c2.key = 'host_new_name'

    # Mutating the "token" key does not work because children are alive.
    with raises(RuntimeError):
        c3.key = 'token_new_name'
    del c4, c5
    c3.key = 'token_new_name'
    assert c3.path == ['token_new_name']


def test_extract():
    class ItemData(config.Partial):
        uri = config.Field(str)
    class Item(config.Partial):
        name = config.Field(str)
        data = config.Field(ItemData, default=None)
    class Config(config.Partial):
        args = config.Field((list, str), default=lambda: ['foo', 'bar'])
        stuff = config.Field(dict, default=None)
        items = config.Field((list, Item))

    test_data = {
        'items': [
            {'name': 'A'},
            {'name': 'B', 'data': {'uri': 'https://uri-here'}}
        ],
        'stuff': {
            'arbitrary': object()
        }
    }

    data = config.extract(Config, test_data)
    assert data.args == ['foo', 'bar']
    assert data.items[0].name == 'A'
    assert data.items[0].data is None
    assert data.items[1].name == 'B'
    assert data.items[1].data.uri == 'https://uri-here'

    dumped_data = config.dump(Config, data)

    # Not testing 'args' because that key is filled with a default value.
    assert test_data['items'] == dumped_data['items']


def test_override():
    class A(config.Partial):
        value = config.Field(str)
    class B(config.Partial):
        value = config.Field(A)
    fields = getattr(B, config.PARTIAL_FIELDS)
    assert len(fields) == 1
    assert fields[0].name == 'value'
    assert fields[0].type_decl is A
    x = config.extract(B, {'value': {'value': 'foo'}})
    assert isinstance(x, B)
    assert isinstance(x.value, A)
    assert isinstance(x.value.value, str)
    assert x.value.value == 'foo'
