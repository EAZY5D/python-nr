# nr.stream

Streaming iterators in Python.

### Changes

#### v1.0.2 (2018-08-18)

* Add `stream.__next__()`
* Fix `stream.__getitem__()` error message when a non-slice argument
  was passed.

#### v1.0.1 (2018-07-07)

* Add `stream.consume(iterable, n=None)`
