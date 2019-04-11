# nr.core.types

A collection of useful Python datatypes, including enumerations, generics,
enhanced mappings, meta-programming tools and sumtypes.

* `nr.core.types.abc` &ndash; Alias for `collections.abc` or `collections`
* `nr.core.types.function` &ndash; Helpers for working with function types (such
  as copying a function, replacing various members in the process)
* `nr.core.types.generic` &ndash; Create generic classes that can be instantiated
  with the bracket syntax (eg. `HashDict[my_hash_func]`)
* `nr.core.types.maps` &ndash; Various `abc.Mapping` implementations
* `nr.core.types.meta` &ndash; Various metaclasses (most notably `InlineMetaclass`)
* `nr.core.types.notset` &ndash; Provides a `NotSet` singleton that can be used
  to describe an unset variable or attribute if `None` is an acceptable value.
* `nr.core.types.record` &ndash; Mutable `namedtuple`s with more features.
* `nr.core.types.sets` &ndash; Various `abc.Set` implementations.
* `nr.core.types.sumtype` &ndash; Provides a `Sumtype` base class.

## Changes

### 2.0.0

* Moved into `nr.core` package
* Removed `nr.core.types.named` module
* Updated `nr.core.types.record` module (combines both features of the old
  `named` and `record` modules and more)
* Rename `nr.core.types.map` to `nr.core.types.maps`
* Rename `nr.core.types.set` to `nr.core.types.sets`
* Rename `nr.core.types.function.replace()` to `~.copy_function()`
* Add `nr.core.types.abc` as alias for `collections.abc` or `collections` (depending
  on availability)
* Add `nr.core.types.notset`

### 1.1.1 (2018-09-14)

* Fix ValueIterableMap.__len__() and rename iterable argument to map

### 1.1.0 (2018-08-18)

* Add missing `namespace_packages` paramater to setup
* Add `nr.types.set` module with `OrderedSet` class
* Add `ValueIterableMap` to `nr.types.map`
* Add `Sumtype.__eq__()` and `Sumtype.__ne__()`
* Add `ChainMap.get()`
* Make maps inherit from `collections.MutableMapping`

### 1.0.6 (2018-07-14)

* Default values in annotated fields specified in subclasses of the
  `nr.types.named.Named` class can now be functions in which case they
  behave the same as passing that function to a `Named.Initializer`
* Add `HashDict` class to `nr.types.map`

### 1.0.5 (2018-07-05)

* Add missing requirement `six` to `setup.py` and `requirements.txt`

### 1.0.4 (2018-06-29)

* Add `nr.types.function` module
* Add `nr.types.generic` module
* Make `nr.types.named` module Python 2.6 compatible
* Fix `ObjectAsMap.__new__` and `MapAsObject.__new__`

### 1.0.3 (2018-06-03)

* Hotfix for the `__version__` member in the `nr.types` module

### 1.0.2 (2018-06-03)

* Setup script Python 2 compatibility
