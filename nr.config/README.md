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
assert dump(config) == data
```
