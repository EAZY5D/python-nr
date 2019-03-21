# nr.config

The `nr.config` package provides an API to define models to parse
JSON/CSON/YAML configuration files.

```python
from nr.config import Field, Partial, extract, dump

class User(Partial):
  name = Field(str)
  realm = Field(str)

class AuthConfig(Partial):
  authorized_users = Field((list, User), name='authorized-users')

data = {'authorized-users': [{'name': 'me', 'realm': 'sso'}]}
config = extract(AuthConfig, data)
print(config.authorized_users[0].name)
assert dump(AuthConfig, config) == data
```

### Changelog

#### v1.0.2 (2019-03-21)

* Add `nr.types>=1.1.0` dependency
* Use `yaml.safe_load()` in `nr.config.extract()` if possible
* Use `OrderedDict` with `json.load()`

#### v1.0.1 (2019-03-21)

* Fix Python 3 compatibility in GenericTypeHandler

#### v1.0.0 (2019-03-21)

* Initial version
