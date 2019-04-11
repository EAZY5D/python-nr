# `nr.futures`

&ndash; A convenient threading based future implementation compatible
with Python 2 and 3.

## Changelog

### v1.0.1 (2018-11-16)

* Add `ThreadPool(bounded, bounded_allowance)` parameters
* Remove `requirements.txt`

### v1.0.0 (2018-05-10)

* Initial release

## API Documentation

Generated with [pydoc-markdown](https://github.com/NiklasRosenstein/pydoc-markdown).


<h2 id="nr.futures.Future">Future objects</h2>

```python
Future(self, worker=None, print_exc=True, logger=None)
```

This class represents a task that can be executed in a separate thread.
The result can then be obtained via the `result` or `get()` method.

The way exceptions are handled inside the future depends on the policy
the is defined when the future is created. When you never intend to
explicitly retrieve the result of the future, the exception will be
immediately printed using `traceback.print_exc()`. This is the default
behaviour.

If you intend to retrieve the result of the future at some point, the
exception will be reraised when you call `result`. If the future is
garbage collected before the exception was retrieved and reraised at least
once, it will be printed before the future gets collected.

Before you start a future, you must bind a worker function to it either
by passing a callable as the first argument or using the `bind()` method.

```python
f = Future(lambda: worker(arg1, arg2='Foo'))
f = Future().bind(worker, arg1, arg2='Foo')
```

If you want to pass the future as an argument to the worker function,
you need to temporarily assign the future to a variable. Passing the
future to the worker function allows the worker to check the state of
the future, most notably if it has been `cancelled()`.

```python
f = Future(lambda: worker(f))
f.start()
```

Note that the worker function is deleted from the future after it has
been run or cancelled. Future objects are not supposed to be reused.

If you expect to collect the result of the future, pass `True`
to the *collect_result* parameter. If you do expect to collect the result
but never do, the exception will be printed when the future is deleted.

```python
f = Future((lambda: 42 * gimme_that_error), True)
f.start()
del f
# printed to console (not actually raised)
# NameError: global name 'bar' is not defined
```

__Parameters__

- __worker (function)__:
  The worker function to be bound to the future. Can also be set with
  `bind()`. If this is a boolean value, the parameter takes on the semantics
  of *collect_result*.
- __print_exc (bool)__:
  Set to `False` if you expect to collect the result of this future,
  allowing possible exceptions to be propagated that way. Defaults to
  `True`, in which case any exception occuring inside the Future will be
  printed to `sys.stderr` or to the specified *logger*.
- __logger (logging.Logger)__:
  A logger instance that will be used to print exceptions to instead of
  `sys.stderr`.

<h3 id="nr.futures.Future.bind">bind()</h3>

```python
Future.bind(self, _Future__fun, *args, **kwargs)
```

Bind a worker function to the future. This worker function will be
executed when the future is executed.

<h3 id="nr.futures.Future.add_done_callback">add_done_callback()</h3>

```python
Future.add_done_callback(self, fun)
```

Adds the callback *fun* to the future so that it be invoked when the
future completed. The future completes either when it has been completed
after being started with the `start()` method (independent of whether
an error occurs or not) or when either `set_result()` or `set_exception()`
is called.

If the future is already complete, *fun* will be invoked directly.

The function *fun* must accept the future as its sole argument.

<h3 id="nr.futures.Future.enqueue">enqueue()</h3>

```python
Future.enqueue(self)
```

Mark the future as being enqueued in some kind of executor for futures.
Calling `start()` with the *as_thread* parameter as `True` will raise a
`RuntimeError` after this method has been called.

This method will also validate the state of the future.

<h3 id="nr.futures.Future.start">start()</h3>

```python
Future.start(self, as_thread=True)
```

Execute the future in a new thread or in the current thread as specified
by the *as_thread* parameter.

__Parameters__

- __as_thread (bool)__:
  Execute the future in a new, separate thread. If this is set to `False`,
  the future will be executed in the calling thread.

<h3 id="nr.futures.Future.enqueued">enqueued()</h3>

```python
Future.enqueued(self)
```

Returns `True` if the future is enqueued, meaning that it is about
  to be or already being executed.

<h3 id="nr.futures.Future.running">running()</h3>

```python
Future.running(self)
```

Returns `True` if the future is running, `False` otherwise.

<h3 id="nr.futures.Future.done">done()</h3>

```python
Future.done(self)
```

Returns `True` if the future completed, `False` otherwise.

<h3 id="nr.futures.Future.cancelled">cancelled()</h3>

```python
Future.cancelled(self)
```

Checks if the future has been cancelled.

<h3 id="nr.futures.Future.result">result()</h3>

```python
Future.result(self, timeout=None, do_raise=True)
```

Retrieve the result of the future, waiting for it to complete or at
max *timeout* seconds.

__Parameters__

- __timeout (None, float)__:
  The number of maximum seconds to wait for the result.
- __do_raise (bool)__:
  Set to `False` to prevent any of the exceptions below to be raised and
  return `None` instead.
- __raise (Cancelled)__: If the future has been cancelled.
- __raise (Timeout)__: If the *timeout* has been exceeded.
- __raise (BaseException)__: Anything the worker has raised.
- __return (any)__: Whatever the worker bound to the future returned.

<h3 id="nr.futures.Future.exception">exception()</h3>

```python
Future.exception(self, timeout=None, do_raise=True)
```

Returns the exception value by the future's worker or `None`.

__Parameters__

- __timeout (None, float)__:
- __do_raise (bool)__:
- __raise (Cancelled)__:
raise (Timeout)

<h3 id="nr.futures.Future.exc_info">exc_info()</h3>

```python
Future.exc_info(self, timeout=None, do_raise=True)
```

Returns the exception info tuple raised by the future's worker or `None`.

__Parameters__


- __timeout (None, float)__:
- __do_raise (bool)__:
- __raise (Cancelled)__:
raise (Timeout)

<h3 id="nr.futures.Future.cancel">cancel()</h3>

```python
Future.cancel(self, mark_completed_as_cancelled=False)
```

Cancel the future. If the future has not been started yet, it will never
start running. If the future is already running, it will run until the
worker function exists. The worker function can check if the future has
been cancelled using the `cancelled` method.

If the future has already been completed, it will not be marked as
cancelled unless you set *mark_completed_as_cancelled* to `True`.

__Parameters__

- __mark_completed_as_cancelled (bool)__:
  If this is `True` and the future has already completed, it will be marked
  as cancelled anyway.

<h3 id="nr.futures.Future.set_result">set_result()</h3>

```python
Future.set_result(self, result)
```

Allows you to set the result of the future without requiring the future
to actually be executed. This can be used if the result is available
before the future is run, allowing you to keep the future as the interface
for retrieving the result data.

__Parameters__

- __result (any)__: The result of the future.
- __raise (RuntimeError)__: If the future is already enqueued.

<h3 id="nr.futures.Future.set_exception">set_exception()</h3>

```python
Future.set_exception(self, exc_info)
```

This method allows you to set an exception in the future without requring
that exception to be raised from the futures worker. This method can be
called on an unbound future.

__Parameters__

- __exc_info (Exception, tuple)__:
  Either an exception info tuple or an exception value. In the latter
  case, the traceback will be automatically generated from the parent
  frame.
- __raise (RuntimeError)__: If the future is already enqueued.

<h3 id="nr.futures.Future.wait">wait()</h3>

```python
Future.wait(self, timeout=None, do_raise=False)
```

Wait for the future to complete. If *timeout* is specified, it must be a
floating point number representing the maximum number of seconds to wait.

__Parameters__

- __timeout (None, float)__:
  The maximum number of seconds to wait for the future to complete.
- __do_raise (bool)__:
  Raise `Timeout` when a timeout occurred.
- __return (bool)__:
  `True` if the future completed, `False` if a timeout occurred and
  *do_raise* was set to False.
- __raise (Timeout)__:
  If a timeout occurred and *do_raise* was True.

<h2 id="nr.futures.ThreadPool">ThreadPool objects</h2>

```python
ThreadPool(self, max_workers, daemon=True, bounded=False, bounded_allowance=0)
```

Represents a pool of threads that can process futures.

<h3 id="nr.futures.ThreadPool.enqueue">enqueue()</h3>

```python
ThreadPool.enqueue(self, future)
```

Enqueue a future to be processed by one of the threads in the pool.
The future must be bound to a worker and not have been started yet.

<h3 id="nr.futures.ThreadPool.submit">submit()</h3>

```python
ThreadPool.submit(self, _ThreadPool__fun, *args, **kwargs)
```

Creates a new future and enqueues it. Returns the future.

<h3 id="nr.futures.ThreadPool.cancel">cancel()</h3>

```python
ThreadPool.cancel(self, cancel_running=True, mark_completed_as_cancelled=False)
```

Cancel all futures queued in the pool. If *cancel_running* is True,
futures that are currently running in the pool are cancelled as well.

<h3 id="nr.futures.ThreadPool.shutdown">shutdown()</h3>

```python
ThreadPool.shutdown(self, wait=True)
```

Shut down the pool. If *wait* is True, it will wait until all futures
are completed. Alternatively, you can use the `wait()` method to wait
with timeout supported.

<h3 id="nr.futures.ThreadPool.wait">wait()</h3>

```python
ThreadPool.wait(self, timeout=None)
```

Wait until all futures are completed. You should call this method only
after calling `shutdown()`. Returns `False` if all futures are complete,
`False` if there are still some running.

