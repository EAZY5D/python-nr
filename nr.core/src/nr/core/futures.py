# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from __future__ import print_function
from six import reraise

import collections
import functools
import time
import threading
import traceback
import sys


def _get_timeout_begin(timeout):
  if timeout is None:
    return None
  return time.clock()


def _get_timeout_remainder(tbegin, timeout):
  if timeout is None:
    return None
  return timeout - (time.clock() - tbegin)


class Cancelled(Exception):
  " This exception is raised by various #Future methods if it was cancelled ."

class Timeout(Exception):
  " This exception is raised by various #Future methods if a timeout occured. "

class Unavailable(Exception):
  " This exception is raised by #Future.get() if the result is not available. "


class Future(object):
  """
  This class represents a task that can be executed in a separate thread.
  The result can then be obtained via the #result or #get() method.

  The way exceptions are handled inside the future depends on the policy
  the is defined when the future is created. When you never intend to
  explicitly retrieve the result of the future, the exception will be
  immediately printed using #traceback.print_exc(). This is the default
  behaviour.

  If you intend to retrieve the result of the future at some point, the
  exception will be reraised when you call #result. If the future is
  garbage collected before the exception was retrieved and reraised at least
  once, it will be printed before the future gets collected.

  Before you start a future, you must bind a worker function to it either
  by passing a callable as the first argument or using the #bind() method.

  ```python
  f = Future(lambda: worker(arg1, arg2='Foo'))
  f = Future().bind(worker, arg1, arg2='Foo')
  ```

  If you want to pass the future as an argument to the worker function,
  you need to temporarily assign the future to a variable. Passing the
  future to the worker function allows the worker to check the state of
  the future, most notably if it has been #cancelled().

  ```python
  f = Future(lambda: worker(f))
  f.start()
  ```

  Note that the worker function is deleted from the future after it has
  been run or cancelled. Future objects are not supposed to be reused.

  If you expect to collect the result of the future, pass #True
  to the *collect_result* parameter. If you do expect to collect the result
  but never do, the exception will be printed when the future is deleted.

  ```python
  f = Future((lambda: 42 * gimme_that_error), True)
  f.start()
  del f
  # printed to console (not actually raised)
  # NameError: global name 'bar' is not defined
  ```

  # Parameters
  worker (function):
    The worker function to be bound to the future. Can also be set with
    #bind(). If this is a boolean value, the parameter takes on the semantics
    of *collect_result*.
  print_exc (bool):
    Set to #False if you expect to collect the result of this future,
    allowing possible exceptions to be propagated that way. Defaults to
    #True, in which case any exception occuring inside the Future will be
    printed to #sys.stderr or to the specified *logger*.
  logger (logging.Logger):
    A logger instance that will be used to print exceptions to instead of
    #sys.stderr.
  restartable (bool):
    Set this to #True if you want the future to be restartable. The *worker*
    function will not be unset when the future finished running.
  """

  Cancelled = Cancelled
  Timeout = Timeout
  Unavailable = Unavailable

  def __init__(self, worker=None, print_exc=True, logger=None, restartable=False):
    if isinstance(worker, bool):
      worker = None
      print_exc = worker
    if worker is not None and not callable(worker):
      raise TypeError('worker must be callable')
    self._print_exc = print_exc
    self._worker = worker
    self._thread = None
    self._enqueued = False
    self._exc_info = None
    self._lock = threading.Condition()
    self._running = False
    self._completed = False
    self._cancelled = False
    self._result = None
    self._logger = logger
    self._restartable = restartable
    self._done_callbacks = []

  def __repr__(self):
    with self._lock:
      if self._exc_info:
        status = 'error ({})'.format(self._exc_info[1])
      elif self._cancelled:
        status = 'cancelled'
      elif self._completed:
        status = 'completed'
      elif self._running:
        status = 'running'
      elif self._enqueued:
        status = 'enqueued'
      else:
        status = 'idle'
      return '<Future {}>'.format(status)

  def _print_exception(self):
    if self._logger:
      self._logger.exception('Exception in {0}'.format(self))
    else:
      print('Exception in {0}'.format(self), file=sys.stderr)
      traceback.print_exc()
      sys.stderr.flush()

  def bind(self, __fun, *args, **kwargs):
    """
    Bind a worker function to the future. This worker function will be
    executed when the future is executed.
    """

    with self._lock:
      if self._running or self._completed or self._cancelled:
        raise RuntimeError('Future object can not be reused')
      if self._worker:
        raise RuntimeError('Future object is already bound')
      self._worker = functools.partial(__fun, *args, **kwargs)
    return self

  def add_done_callback(self, fun, once=False):
    """
    Adds the callback *fun* to the future so that it be invoked when the
    future completed. The future completes either when it has been completed
    after being started with the #start() method (independent of whether
    an error occurs or not) or when either #set_result() or #set_exception()
    is called.

    If the future is already complete, *fun* will be invoked directly.

    The function *fun* must accept the future as its sole argument.

    # Parameters
    fun (callable): The function to call when the future completed.
        The function must accept the future as its sole argument.
    once (bool): Add this listener to the #Future so that it is invoked
        exactly once. The default is #False. This is only relevant for
        restartable futures.
    """

    with self._lock:
      if self._completed:
        fun(self)
      if not self._completed or (not once and self._restartable):
        self._done_callbacks.append((fun, once))

  def enqueue(self):
    """
    Mark the future as being enqueued in some kind of executor for futures.
    Calling #start() with the *as_thread* parameter as #True will raise a
    #RuntimeError after this method has been called.

    This method will also validate the state of the future.
    """

    with self._lock:
      if self._enqueued:
        raise RuntimeError('Future object is already enqueued')
      if self._running:
        raise RuntimeError('Future object is already running')
      if self._completed:
        raise RuntimeError('Future object can not be restarted')
      if not self._worker:
        raise RuntimeError('Future object is not bound')
      self._enqueued = True

  def start(self, as_thread=True):
    """
    Execute the future in a new thread or in the current thread as specified
    by the *as_thread* parameter.

    # Parameters
    as_thread (bool):
      Execute the future in a new, separate thread. If this is set to #False,
      the future will be executed in the calling thread.
    """

    with self._lock:
      if self._running:
        raise RuntimeError('Future object is already running')
      if self._restartable:
        self._enqueued = False
        self._completed = False
      if as_thread:
        self.enqueue()
      if self._cancelled:
        return

      self._running = True
      if as_thread:
        self._thread = threading.Thread(target=self._run)
        self._thread.start()
        return self

    self._run()

  def _run(self):
    result = None
    exc_info = None
    try:
      result = self._worker()
    except:
      exc_info = sys.exc_info()
      if self._print_exc:
        # The result is not expected to be collected, thus the exception
        # would be swallowed. We print it immediately.
        self._print_exception()
    with self._lock:
      if not self._restartable:
        self._worker = None
      self._result = result
      self._exc_info = exc_info
      self._running = False
      self._completed = True
      self._lock.notify_all()
      callbacks = self._prepare_done_callbacks()
    try:
      callbacks()
    except:
      self._print_exception()

  # @requires_lock
  def _prepare_done_callbacks(self):
    def invoker(future, callbacks):
      for callback in callbacks:
        try:
          callback(future)
        except:
          future._print_exception()
    callbacks = [x for x, once in self._done_callbacks]
    if self._restartable:
      # Keep all callbacks that should not be invoked just once.
      self._done_callbacks = [(x, False) for x, once in self._done_callbacks if not once]
    else:
      self._done_callbacks = []
    return functools.partial(invoker, self, callbacks)

  def pending(self):
    """
    Returns #True if the future is pending, meaning that it has not been
    started yet. This is independent of whether the future has been enqueued
    or not.
    """

    with self._lock:
      if self._running or self._completed or self._cancelled:
        return False
      return True

  def enqueued(self):
    """
    Returns #True if the future is enqueued, meaning that it is about
    to be or already being executed.
    """

    with self._lock:
      return self._enqueued

  def running(self):
    """
    Returns #True if the future is running, #False otherwise.
    """

    with self._lock:
      return self._running

  def done(self):
    """
    Returns #True if the future completed, #False otherwise.
    """

    with self._lock:
      return self._completed

  def cancelled(self):
    """
    Checks if the future has been cancelled.
    """

    with self._lock:
      return self._cancelled

  def get(self, do_raise=True, default=None):
    """
    Retrieve the result of the future, non-blocking. If the result is not
    available because the future has not been finished or resulted in an
    exception, either the exception raised inside the worker or an
    #Unavailable exception is raised.

    # Parameters
    do_raise (bool): Set to #False to prevent #Unavailable exception from
        being raised and *default* to be returned in case the result is not
        available.
    raise (Unavailable): If the result is not available.
    raise (BaseException): The exception that occured in the worker.
    return (any): The result or #None if it is not available and *do_raise*
        was set to #False.
    """

    try:
      return self.result(0)
    except self.Timeout:
      if do_raise:
        raise self.Unavailable
      return default

  def result(self, timeout=None, do_raise=True):
    """
    Retrieve the result of the future, waiting for it to complete or at
    max *timeout* seconds.

    # Parameters
    timeout (None, float): The number of maximum seconds to wait for the result.
    do_raise (bool): Set to #False to prevent #Cancelled or #Timeout to be raised.
    raise (Cancelled): If the future has been cancelled. Can be disabled with *do_raise*.
    raise (Timeout): If the *timeout* has been exceeded. Can be disabled with *do_raise*.
    raise (BaseException): Anything the worker has raised.
    return (any): Whatever the worker bound to the future returned.
    """

    with self._lock:
      self.wait(timeout, do_raise=do_raise)
      if self._exc_info:
        reraise(*self._exc_info)
      if self._cancelled:
        if not do_raise:
          return None
        raise self.Cancelled()
      return self._result

  def exception(self, timeout=None, do_raise=True):
    """
    Returns the exception value by the future's worker or #None.

    # Parameters
    timeout (None, float):
    do_raise (bool):
    raise (Cancelled):
    raise (Timeout)
    """

    with self._lock:
      self.wait(timeout, do_raise=do_raise)
      if not self._exc_info:
        return None
      if self._cancelled:
        raise self.Cancelled()
      return self._exc_info[1]

  def exc_info(self, timeout=None, do_raise=True):
    """
    Returns the exception info tuple raised by the future's worker or #None.

    # Parameters

    timeout (None, float):
    do_raise (bool):
    raise (Cancelled):
    raise (Timeout)
    """

    with self._lock:
      self.wait(timeout, do_raise=do_raise)
      if not self._exc_info:
        return None
      if self._cancelled:
        raise self.Cancelled()
      return self._exc_info

  def cancel(self, mark_completed_as_cancelled=False):
    """
    Cancel the future. If the future has not been started yet, it will never
    start running. If the future is already running, it will run until the
    worker function exists. The worker function can check if the future has
    been cancelled using the #cancelled method.

    If the future has already been completed, it will not be marked as
    cancelled unless you set *mark_completed_as_cancelled* to #True.

    # Parameters
    mark_completed_as_cancelled (bool):
      If this is #True and the future has already completed, it will be marked
      as cancelled anyway.
    """

    with self._lock:
      if not self._completed or mark_completed_as_cancelled:
        self._cancelled = True
      if not self._restartable:
        self._worker = None
      callbacks = self._prepare_done_callbacks()
    callbacks()

  def set_result(self, result):
    """
    Allows you to set the result of the future without requiring the future
    to actually be executed. This can be used if the result is available
    before the future is run, allowing you to keep the future as the interface
    for retrieving the result data.

    # Parameters
    result (any): The result of the future.
    raise (RuntimeError): If the future is already enqueued.
    """

    with self._lock:
      if self._enqueued:
        raise RuntimeError('can not set result of enqueued Future')
      if not self._restartable:
        self._worker = None
      self._result = result
      self._completed = True
      callbacks = self._prepare_done_callbacks()
    callbacks()

  def set_exception(self, exc_info):
    """
    This method allows you to set an exception in the future without requring
    that exception to be raised from the futures worker. This method can be
    called on an unbound future.

    # Parameters
    exc_info (Exception, tuple):
      Either an exception info tuple or an exception value. In the latter
      case, the traceback will be automatically generated from the parent
      frame.
    raise (RuntimeError): If the future is already enqueued.
    """

    if not isinstance(exc_info, tuple):
      if not isinstance(exc_info, BaseException):
        raise TypeError('expected BaseException instance')
      try:
        # TODO: Filld the traceback so it appears as if the exception
        #       was actually raised by the caller? (Not sure if possible)
        raise exc_info
      except:
        exc_info = sys.exc_info()
        exc_info = (exc_info[0], exc_info[1], exc_info[2])

    with self._lock:
      if self._enqueued:
        raise RuntimeError('can not set exception of enqueued Future')
      if not self._restartable:
        self._worker = None
      self._exc_info = exc_info
      self._completed = True
      callbacks = self._prepare_done_callbacks()
    callbacks()

  def wait(self, timeout=None, do_raise=False):
    """
    Wait for the future to complete. If *timeout* is specified, it must be a
    floating point number representing the maximum number of seconds to wait.

    # Parameters
    timeout (None, float): The maximum number of seconds to wait for the future to complete.
    do_raise (bool): Raise #Timeout when a timeout occurred.
    raise (Timeout): If a timeout occurred and *do_raise* was True.
    return (bool): #True if the future completed, #False if a timeout occurred
        and *do_raise* was set to False.
    """

    if timeout is not None:
      timeout = float(timeout)
      start = time.clock()

    with self._lock:
      while not self._completed and not self._cancelled:
        if timeout is not None:
          time_left = timeout - (time.clock() - start)
        else:
          time_left = None
        if time_left is not None and time_left <= 0.0:
          if do_raise:
            raise self.Timeout()
          else:
            return False
        self._lock.wait(time_left)
    return True


class ThreadPool(object):
  """
  Represents a pool of threads that can process futures.

  :param max_workers: The number of parallel workers.
  :param daemon: Whether the workers are daemon threads.
  :param bounded: Enable to make :meth:`submit` block if the queue is full.
  :param bounded_allowance: The number of futures to submit beyond the
    maximum queue size (= maximum number of workers) before :meth:`submit`
    blocks (only if *bounded* is enabled).
  """

  def __init__(self, max_workers, daemon=True, bounded=False,
               bounded_allowance=0):
    self._workers = []
    self._daemon = daemon
    self._max_workers = max_workers
    self._queue = collections.deque()
    self._running = collections.deque()
    self._lock = threading.Condition()
    self._bounded = bounded
    self._bounded_allowance = bounded_allowance
    self._shutdown = False

  def __enter__(self):
    return self

  def __exit__(self, *a):
    self.shutdown()

  def enqueue(self, future):
    """
    Enqueue a future to be processed by one of the threads in the pool.
    The future must be bound to a worker and not have been started yet.
    """

    future.enqueue()
    with self._lock:
      if self._shutdown:
        raise RuntimeError('ThreadPool has been shut down and can no '
          'longer accept futures.')
      if self._bounded:
        while len(self._queue) >= (self._max_workers + self._bounded_allowance):
          self._lock.wait()
      self._queue.append(future)
      if len(self._running) == len(self._workers):
        self._new_worker()
      self._lock.notify_all()

  def submit(self, __fun, *args, **kwargs):
    """
    Creates a new future and enqueues it. Returns the future.
    """

    future = Future().bind(__fun, *args, **kwargs)
    self.enqueue(future)
    return future

  def cancel(self, cancel_running=True, mark_completed_as_cancelled=False):
    """
    Cancel all futures queued in the pool. If *cancel_running* is True,
    futures that are currently running in the pool are cancelled as well.
    """

    with self._lock:
      for future in self._queue:
        future.cancel(mark_completed_as_cancelled)
      if cancel_running:
        for future in self._running:
          future.cancel(mark_completed_as_cancelled)
      self._queue.clear()

  def shutdown(self, wait=True):
    """
    Shut down the pool. If *wait* is True, it will wait until all futures
    are completed. Alternatively, you can use the #wait() method to wait
    with timeout supported.
    """

    with self._lock:
      self._shutdown = True
      self._lock.notify_all()
    if wait:
      self.wait()

  def wait(self, timeout=None):
    """
    Wait until all futures are completed. You should call this method only
    after calling #shutdown(). Returns #False if all futures are complete,
    #False if there are still some running.
    """

    tbegin = _get_timeout_begin(timeout)
    with self._lock:
      while self._queue or self._running:
        remainder = _get_timeout_remainder(tbegin, timeout)
        if remainder is not None and remainder <= 0.0:
          return False  # timeout
        self._lock.wait(remainder)
      if self._shutdown:
        for worker in self._workers:
          worker.join()
    return True

  def _new_worker(self):
    with self._lock:
      if len(self._workers) < self._max_workers:
        worker = self._Worker(self)
        worker.daemon = self._daemon
        self._workers.append(worker)
        worker.start()

  class _Worker(threading.Thread):

    def __init__(self, master):
      threading.Thread.__init__(self)
      self._master = master

    def run(self):
      while True:
        with self._master._lock:
          while not self._master._queue:
            if self._master._shutdown:
              return
            self._master._lock.wait()
          future = self._master._queue.popleft()
          self._master._running.append(future)
          self._master._lock.notify_all()
        try:
          future.start(as_thread=False)
        finally:
          with self._master._lock:
            self._master._running.remove(future)
            self._master._lock.notify_all()
