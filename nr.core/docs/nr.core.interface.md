# `nr.interface`

&ndash; Something like `zope.interface`, just simpler and a few extras.

## Example

Here we declare an interface called `ParameterInterface`. All implementors
of this interface will have a `params` member which is created by the
interface `__init__()` method. The `__constructed__()` method is invoked
when the implementation has been fully constructed.

```python
import nr.interface

class ParameterInterface(nr.interface.Interface):

  params = nr.interface.attr(dict)

  def __init__(self):
    self.params = {}

  def __constructed__(self):
    self.declare_parameters()

  def declare_parameters(self):
    pass
```

A possible implementation could look like this:

```python
class MyParameters(nr.interface.Implementation):
  nr.interface.implements(ParameterInterface)

  def declare_parameters(self):
    self.params['depth'] = 32

obj = MyParameters()
assert(obj.params['depth'] == 32)
```

---

## Changes

### 1.0.4 (2018-08-18)

* Add missing `namespace_packages` parameter to `setup.py`

### 1.0.3 (2018-06-03)

* Fix `setup.py` Python 2 compatibility

### 1.0.2 (2018-05-28)

* Add support for properties in interface declarations
* Add `final()` decorator
* Rename `InvalidImplementationError` to `ImplementationError`
* Fix `get_conflicting_members()`

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
