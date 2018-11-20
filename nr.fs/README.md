# `nr.fs`

&ndash; Filesystem and path manipulation tools.

> Note: To use the `nr.fs.glob()` function, you need the [glob2] module
> installed. It is not listed an install requirement to this module.

  [glob2]: https://pypi.org/project/glob2/

### Changes

#### v1.1.1 (2018-08-21)

* Fix `issub()` and add `at_curr=True` parameter

#### v1.1.0 (2018-08-18)

* Add `compare_all_timestamps()` function
* Add `mtime_consistent_file` class

#### v1.0.3 (2018-08-06)

* Fix `NameError` on platforms where `os.name != 'nt'`

#### v1.0.2 (2018-07-14)

* Changed `get_long_path_name()` is now an alias for `fixcase()`
  (backwards compatibility until 1.1.0)
* Changed `canonical()` so that it invokes `fixcase()` on case-insensitive
  filesystems
* When `tempfile(encoding)` parameter was not specified, its `encoding`
  property will still return the applied text file encoding after it
  has been opened
* Add `fixcase()` as replacement for `get_long_path_name()`
* Add `tempfile.encoding` property
* Add `listdir()`

#### v1.0.1 (2018-07-05)

* Add `nr.fs.isfile_cs()`
* Add `nr.fs.get_long_path_name()`
* Add `namespace_packages` parameter in `setup.py`
