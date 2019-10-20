# Copyright (c) 2015-2017  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the follo  wing conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
This module provides a simple interface to creating and managing concurrent
tasks. Note that the module does not primarily focus on performance
multithreading, but to enable writing multitask applications with ease.

Compatible with Python 2 and 3.

# Example
```python
from nr.concurrency import Job, as_completed
from requests import get
urls = ['https://google.com', 'https://github.com', 'https://readthedocs.org']
for job in as_completed(Job((lambda: get(x)), start=True) for x in urls):
  print(job.result)
```

# Members

main_thread (threading._MainThread): The main-thread object.
"""

import collections
import functools
import threading
import time
import traceback
import sys
from threading import current_thread

try:
  import queue
except ImportError:
  import Queue as queue


main_thread = next(t for t in threading.enumerate()
  if isinstance(t, threading._MainThread))

# Synchronizable API
# ============================================================================

class Synchronizable(object):
  """
  Base class that implements the #Synchronizable interface. Classes that
  inherit from this class can automatically be used with the #synchronized(),
  #wait(), #notify() and #notify_all() functions.

  # Attributes

  synchronizable_lock_type[static]: A type or function that returns lock
    object. Defaults to #threading.RLock.

  synchronizable_condition_type[static]: A type or function that accepts
    an instance of `synchronizable_lock_type` as its first argument and
    returns a new condition variable.

  synchronizable_lock: An instance of type `synchronizable_lock_type`.

  synchronizable_condition: An instance of type `synchronizable_condition_type`.
    The `synchronizable_lock` is passed as an argument to the constructor when
    the condition variable is created.
  """

  synchronizable_lock_type = staticmethod(threading.RLock)
  synchronizable_condition_type = staticmethod(threading.Condition)

  def __new__(cls, *args, **kwargs):
    instance = super(Synchronizable, cls).__new__(cls)
    instance.synchronizable_lock = cls.synchronizable_lock_type()
    instance.synchronizable_condition = cls.synchronizable_condition_type(instance.synchronizable_lock)
    return instance


def synchronized(obj):
  """
  This function has two purposes:

  1. Decorate a function that automatically synchronizes access to the object
     passed as the first argument (usually `self`, for member methods)
  2. Synchronize access to the object, used in a `with`-statement.

  Note that you can use #wait(), #notify() and #notify_all() only on
  synchronized objects.

  # Example
  ```python
  class Box(Synchronizable):
    def __init__(self):
      self.value = None
    @synchronized
    def get(self):
      return self.value
    @synchronized
    def set(self, value):
      self.value = value

  box = Box()
  box.set('foobar')
  with synchronized(box):
    box.value = 'taz\'dingo'
  print(box.get())
  ```

  # Arguments
  obj (Synchronizable, function): The object to synchronize access to, or a
    function to decorate.

  # Returns
  1. The decorated function.
  2. The value of `obj.synchronizable_condition`, which should implement the
     context-manager interface (to be used in a `with`-statement).
  """

  if hasattr(obj, 'synchronizable_condition'):
    return obj.synchronizable_condition
  elif callable(obj):
    @functools.wraps(obj)
    def wrapper(self, *args, **kwargs):
      with self.synchronizable_condition:
        return obj(self, *args, **kwargs)
    return wrapper
  else:
    raise TypeError('expected Synchronizable instance or callable to decorate')


def wait(obj, timeout=None):
  """
  Wait until *obj* gets notified with #notify() or #notify_all(). If a timeout
  is specified, the function can return without the object being notified if
  the time runs out.

  Note that you can only use this function on #synchronized() objects.

  # Arguments
  obj (Synchronizable): An object that can be synchronized.
  timeout (number, None): The number of seconds to wait for the object to get
    notified before returning. If not value or the value #None is specified,
    the function will wait indefinetily.
  """

  if timeout is None:
    return obj.synchronizable_condition.wait()
  else:
    return obj.synchronizable_condition.wait(timeout)


def wait_for_condition(obj, cond, timeout=None):
  """
  This is an extended version of #wait() that applies the function *cond* to
  check for a condition to break free from waiting on *obj*. Note that *obj*
  must be notified when its state changes in order to check the condition.
  Note that access to *obj* is synchronized when *cond* is called.

  # Arguments
  obj (Synchronizable): The object to synchronize and wait for *cond*.
  cond (function): A function that accepts *obj* as an argument. Must return
    #True if the condition is met.
  timeout (number, None): The maximum number of seconds to wait.

  # Returns
  bool: #True if the condition was met, #False if not and a timeout ocurred.
  """

  with synchronized(obj):
    if timeout is None:
      while not cond(obj):
        wait(obj)
    else:
      t_start = time.time()
      while not cond(obj):
        t_delta = time.time() - t_start
        if t_delta >= timeout:
          return False
        wait(obj, timeout - t_delta)
  return True


def notify(obj):
  """
  Notify *obj* so that a single thread that is waiting for the object with
  #wait() can continue. Note that you can only use this function on
  #synchronized() objects.

  # Arguments
  obj (Synchronizable): The object to notify.
  """

  return obj.synchronizable_condition.notify()


def notify_all(obj):
  """
  Like #notify(), but allow all waiting threads to continue.
  """

  return obj.synchronizable_condition.notify_all()


# Job API
# ============================================================================

class Timeout(Exception):
  " Raised when a timeout occurred. "


class Job(Synchronizable):
  """
  This class represents a task (Python function) and its result. The result is
  stored in the #Job object and can be retrieved at any time, given that the
  job has finished successfully. Exceptions that ocurr inside the Python
  function that is invoked by the job can propagated to the caller that obtains
  the result of the job.

  # Job States

  A job can only be in one state at a time. Depending on the state, fetching
  the result of the job will either raise an #InvalidState exception, a
  #Cancelled exception, any other exception that ocurred in the Python function
  that was called by the job, or actually return the result.

  Possible states are:

  - `Job.PENDING`: The job is waiting to be started.
  - `Job.RUNNING`: The job is currently running.
  - `Job.ERROR`: The execution of the job resulted in an exception.
  - `Job.SUCCESS`: The job finished successfully and the result can be obtained.
  - `Job.CANCELLED`: The job was cancelled and finished. Note that this state
    entered after the #Job.cancelled flag is set.

  # Events

  For every job, one or more callbacks can be registered which is invoked every
  time the job transitions into a new state. See #Job.add_listener()

  # Parameters

  task (callable): A callable accepting #Job object as argument that actually
    performs the task and returns the result. If you want to pass a callable
    that takes no arguments, pass it via the `target` parameter.
  target (callable): Just as the `task` parameter, but this time the function
    does not accept any arguments. Note that the two parameters can not be
    specified at the same time. Doing so will result in a #TypeError.
  name (any):
  start (bool): #True if the job should be started in a separate thread
    immediately. Defaults to #False.
  data (any):
  print_exc (bool):

  # Attributes

  name (any): An identifier for the Job. Defaults to #None. This member is
    useful for debugging concurrent applications by giving Jobs a unique name.

  data (any): This member can be filled with an arbitrary Python object.
    Useful to store context information that is needed when the Job finished.
    Note that access to this member, if not already garuanteed to be exclusive,
    must be #synchronized().

  print_exc (bool): Whether to print the traceback of exceptions ocurring in
    the #Job.run() or #Job.target or not. Defaults to #True.

  dispose_inputs (bool): Should be used for jobs that have memory intensive
    input data, to eventually allow the input data to be deallocated due to the
    dropped reference count. Settings this to True will cause all input data to
    be disposed after the Job finished executing (the worker function, args,
    kwargs, clearing all listeners and userdata).
  """

  PENDING = 'pending'
  RUNNING = 'running'
  ERROR = 'error'
  SUCCESS = 'success'
  CANCELLED = 'cancelled'

  _Listener = collections.namedtuple('_Listener', 'callback once')
  ExceptionInfo = collections.namedtuple('ExceptionInfo', 'type value tb')
  Timeout = Timeout

  class Cancelled(Exception):
    " Raised when the Job was cancelled in #Job.wait() or #Job.result. "

  class InvalidState(Exception):
    """
    Raised when the Job is in a state that is not supported by the requested
    operation (eg. reading the result while the job is still running).
    """

  def __init__(self, target=None, task=None, name=None, start=False, data=None,
               print_exc=True, args=None, kwargs=None, dispose_inputs=False):
    super(Job, self).__init__()
    if target is not None:
      if task is not None:
        raise TypeError('either task or target parameter must be specified, not both')
      task = lambda job, *args, **kwargs: target(*args, **kwargs)

    self.__target = task
    self.__thread = None
    self.__args = () if args is None else args
    self.__kwargs = {} if kwargs is None else {}
    self.__state = Job.PENDING
    self.__cancelled = False
    self.__result = None
    self.__exception = None
    self.__listeners = {None: [], Job.SUCCESS: [], Job.ERROR: [], Job.CANCELLED: []}
    self.__event_set = set()
    self.__dispose_inputs = dispose_inputs
    self.name = name
    self.data = data
    self.print_exc = print_exc
    if start: self.start()

  def __repr__(self):
    if self.name:
      name = self.name
    elif hasattr(self.__target, '__name__'):
      name = self.__target.__name__
    elif hasattr(self, 'name'):
      name = self.name
      if callable(name):
        name = name()
    else:
      name = None

    with synchronized(self):
      state = self.__state
      cancelled = self.__cancelled

    result = '<cancelled Job' if (cancelled and state != Job.CANCELLED) else '<Job'
    result += ' {0!r} at 0x{1:x}, state: {2}>'.format(name, id(self), state)
    return result

  @property
  @synchronized
  def state(self):
    " The job's state, one of #PENDING, #RUNNING, #ERROR, #SUCCESS or #CANCELLED. "

    return self.__state

  @property
  @synchronized
  def result(self):
    """
    The result of the jobs execution. Accessing this property while the job is
    pending or running will raise #InvalidState. If an exception occured during
    the jobs execution, it will be raised.

    # Raises
    InvalidState: If the job is not in state #FINISHED.
    Cancelled: If the job was cancelled.
    any: If an exception ocurred during the job's execution.
    """

    if self.__cancelled:
      raise Job.Cancelled
    elif self.__state in (Job.PENDING, Job.RUNNING):
      raise Job.InvalidState('job is {0}'.format(self.__state))
    elif self.__state == Job.ERROR:
      reraise(*self.__exception)
    elif self.__state == Job.SUCCESS:
      return self.__result
    else:
      raise RuntimeError('invalid job state {0!r}'.format(self.__state))

  @property
  @synchronized
  def exception(self):
    """
    The exception that occured while the job executed. The value is #None if
    no exception occurred.

    # Raises
    InvalidState: If the job is #PENDING or #RUNNING.
    """

    if self.__state in (Job.PENDING, Job.RUNNING):
      raise self.InvalidState('job is {0}'.format(self.__state))
    elif self.__state == Job.ERROR:
      assert self.__exception is not None
      return self.__exception
    elif self.__state in (Job.RUNNING, Job.SUCCESS, Job.CANCELLED):
      assert self.__exception is None
      return None
    else:
      raise RuntimeError('invalid job state {0!r}'.format(self.__state))

  @property
  @synchronized
  def pending(self):
    " True if the job is #PENDING. "

    return self.__state == Job.PENDING

  @property
  @synchronized
  def running(self):
    " True if the job is #RUNNING. "

    return self.__state == Job.RUNNING

  @property
  @synchronized
  def finished(self):
    """
    True if the job run and finished. There is no difference if the job
    finished successfully or errored.
    """

    return self.__state in (Job.ERROR, Job.SUCCESS, Job.CANCELLED)

  @property
  @synchronized
  def cancelled(self):
    """
    This property indicates if the job was cancelled. Note that with this flag
    set, the job can still be in any state (eg. a pending job can also be
    cancelled, starting it will simply not run the job).
    """

    return self.__cancelled

  @synchronized
  def get(self, default=None):
    """
    Get the result of the Job, or return *default* if the job is not finished
    or errored. This function will never explicitly raise an exception. Note
    that the *default* value is also returned if the job was cancelled.

    # Arguments
    default (any): The value to return when the result can not be obtained.
    """

    if not self.__cancelled and self.__state == Job.SUCCESS:
      return self.__result
    else:
      return default

  def cancel(self):
    """
    Cancels the job. Functions should check the #Job.cancelled flag from time
    to time to be able to abort pre-emptively if the job was cancelled instead
    of running forever.
    """

    with synchronized(self):
      cancelled = self.__cancelled
      if not cancelled:
        self.__cancelled = True
        notify_all(self)

    if not cancelled:
      self._trigger_event(Job.CANCELLED)

  @synchronized
  def _trigger_event(self, event):
    """
    Private. Triggers and event and removes all one-off listeners for that event.
    """

    if event is None or event not in self.__listeners:
      raise ValueError('invalid event type: {0!r}'.format(event))

    # Check the event has not already been triggered, then mark
    # the event as triggered.
    if event in self.__event_set:
      raise RuntimeError('event already triggered: {0!r}'.format(event))
    self.__event_set.add(event)
    listeners = self.__listeners[event] + self.__listeners[None]

    # Remove one-off listeners.
    self.__listeners[event][:] = (l for l in self.__listeners[event] if not l.once)
    self.__listeners[None][:] = (l for l in self.__listeners[None] if not l.once)

    for listener in listeners:
      # XXX: What to do on exceptions? Catch and make sure all listeners
      # run through? What to do with the exception(s) then?
      listener.callback(self, event)

  def add_listener(self, event, callback, once=False):
    """
    Register a *callback* for the specified *event*. The function will be
    called with the #Job as its first argument. If *once* is #True, the
    listener will be removed after it has been invoked once or when the
    job is re-started.

    Note that if the event already ocurred, *callback* will be called
    immediately!

    # Arguments
    event (str, list of str): The name or multiple names of an event, or None
      to register the callback to be called for any event.
    callback (callable): A function.
    once (bool): Whether the callback is valid only once.
    """

    if not callable(callback):
      raise TypeError('callback must be callable')
    if isinstance(event, str):
      event = [event]
    for evn in event:
      if evn not in self.__listeners:
        raise ValueError('invalid event type: {0!r}'.format(evn))
    for evn in event:
      event_passed = False
      with synchronized(self):
        event_passed = (evn in self.__event_set)
        if not (once and event_passed):
          self.__listeners[evn].append(Job._Listener(callback, once))

    # If the event already happened, we'll invoke the callback
    # immediately to make up for what it missed.
    if event_passed:
      callback(self, event)

  def wait(self, timeout=None):
    """
    Waits for the job to finish and returns the result.

    # Arguments
    timeout (number, None): A number of seconds to wait for the result
      before raising a #Timeout exception.

    # Raises
    Timeout: If the timeout limit is exceeded.
    """

    def cond(self):
      return self.__state not in (Job.PENDING, Job.RUNNING) or self.__cancelled
    if not wait_for_condition(self, cond, timeout):
      raise Job.Timeout
    return self.result

  def start(self, as_thread=True, daemon=False, __state_check=True):
    """
    Starts the job. If the job was run once before, resets it completely. Can
    not be used while the job is running (raises #InvalidState).

    # Arguments
    as_thread (bool): Start the job in a separate thread. This is #True by
      default. Classes like the #ThreadPool calls this function from its own
      thread and passes #False for this argument.
    daemon (bool): If a thread is created with *as_thread* set to #True,
      defines whether the thread is started as a daemon or not. Defaults to
      #False.

    # Returns
    Job: The job object itself.
    """

    if __state_check:
      # We need to manually manage the lock to be able to release it
      # pre-emptively when needed.
      with synchronized(self):
        if self.__cancelled and self.__state == Job.PENDING:
          # Cancelled in PENDING state. Do not run the target function at all.
          self.__state = Job.CANCELLED
          assert self.__exception is None
          assert self.__result is None
          self._trigger_event(Job.CANCELLED)
          return None

        if self.__state == Job.RUNNING:
          raise Job.InvalidState('job is already running')
        elif self.__state not in (Job.PENDING, Job.ERROR, Job.SUCCESS, Job.CANCELLED):
          raise RuntimeError('invalid job state {0!r}'.format(self.__state))

        # Reset the Job attributes.
        self.__state = Job.RUNNING
        self.__cancelled = False
        self.__result = None
        self.__exception = None
        self.__event_set.clear()
        self.__thread = None

        # Remove all listeners that have been registered with the "once" flag.
        for listeners in self.__listeners.values():
          listeners[:] = (l for l in listeners if not l.once)

    if as_thread:
      thread = threading.Thread(target=self.start, args=(False, False, False))
      thread.setDaemon(daemon)
      with synchronized(self):
        assert not self.__thread or not self.__thread.running
        self.__thread = thread
      thread.start()
      return self

    try:
      result = None
      exception = None
      try:
        result = self.run()
        state = Job.SUCCESS
      except Exception:  # XXX: Catch BaseException?
        if self.print_exc:
          traceback.print_exc()
        exception = Job.ExceptionInfo(*sys.exc_info())
        state = Job.ERROR

      with synchronized(self):
        cancelled = self.__cancelled
        self.__result = result
        self.__exception = exception
        self.__state = Job.CANCELLED if cancelled else state

      self._trigger_event(state)
    finally:
      with synchronized(self):
        notify_all(self)
      if self.__dispose_inputs:
        self.__target = None
        self.__args = None
        self.__kwargs = None
        self.data = None
        for listeners in self.__listeners.values():
          listeners[:] = []

    return self

  def run(self):
    """
    This method is the actual implementation of the job. By default, it calls
    the target function specified in the #Job constructor.
    """

    if self.__target is not None:
      return self.__target(self, *self.__args, **self.__kwargs)
    raise NotImplementedError

  @staticmethod
  def factory(start_immediately=True):
    """
    This is a decorator function that creates new `Job`s with the wrapped
    function as the target.

    # Example
    ```python
    @Job.factory()
    def some_longish_function(job, seconds):
      time.sleep(seconds)
      return 42

    job = some_longish_function(2)
    print(job.wait())
    ```

    # Arguments
    start_immediately (bool): #True if the factory should call #Job.start()
      immediately, #False if it should return the job in pending state.
    """

    def decorator(func):
      def wrapper(*args, **kwargs):
        job = Job(task=lambda j: func(j, *args, **kwargs))
        if start_immediately:
          job.start()
        return job
      return wrapper
    return decorator


def as_completed(jobs):
  ''' Generator function that yields the jobs in order of their
  completion. Attaches a new listener to each job. '''

  jobs = tuple(jobs)
  event = threading.Event()
  callback = lambda f, ev: event.set()
  [job.add_listener(Job.SUCCESS, callback, once=True) for job in jobs]
  [job.add_listener(Job.ERROR, callback, once=True) for job in jobs]

  while jobs:
    event.wait()
    event.clear()

    jobs, finished = split_list_by(jobs, lambda x: x.finished)
    for job in finished:
      yield job


# ThreadPool API
# ============================================================================

class ThreadPool(object):
  """
  This class represents a pool of threads that can process jobs up to a certain
  number of maximum concurrent workers. Jobs can be submitted directly (from
  a #~Job.PENDING state) or functions can be passed. The worker-threads will be
  started when the ThreadPool is created.

  Make sure to call #ThreadPool.shutdown() at some point. You can also use a
  `with`-statement.

  # Example
  ```python
  from nr.concurrency import ThreadPool, as_completed
  with ThreadPool() as pool:
    jobs = []
    for data in get_data_to_process():
      jobs.append(pool.submit(process_data, data))
    for job in as_completed(jobs):
      print(job.result)
  ```

  # Parameters
  max_workers (int): The number of worker threads to spawn. Defaults to the
    number of cores on the current machines processor (see #cpu_count()).
  print_exc (bool): Forwarded to the #Job objects that are created with
    #ThreadPool.submit().
  """

  class _Worker(Synchronizable, threading.Thread):

    def __init__(self, queue):
      super(ThreadPool._Worker, self).__init__()
      self.__queue = queue
      self.lock = threading.Lock()
      self.current = None

    def run(self):
      while True:
        item = self.__queue.get()
        try:
          if item is None:
            break
          with self.lock:
            self.current = item
          item.start(as_thread=False)
        except:
          # Exception won't make the _Worker shut down.
          traceback.print_exc()
        finally:
          self.__queue.task_done()
          with self.lock:
            self.current = None

  def __init__(self, max_workers, print_exc=True, dispose_inputs=False):
    super(ThreadPool, self).__init__()
    self.__queue = SynchronizedDeque()
    self.__threads = [self._Worker(self.__queue) for i in range(max_workers)]
    self.__running = False
    self.dispose_inputs = dispose_inputs
    self.print_exc = print_exc

  def __enter__(self):
    self.start()
    return self

  def __exit__(self, exc_type, exc_value, exc_tb):
    self.shutdown(wait=True)

  def __len__(self):
    return len(self.__queue)

  def start(self):
    """
    Starts the #ThreadPool. Must be ended with #stop(). Use the context-manager
    interface to ensure starting and the #ThreadPool.
    """

    if self.__running:
      raise RuntimeError('ThreadPool already running')
    [t.start() for t in self.__threads]
    self.__running = True

  def pending_jobs(self):
    """
    Returns a list of all Jobs that are pending and waiting to be processed.
    """

    return self.__queue.snapshot()

  def current_jobs(self):
    """
    Returns a snapshot of the Jobs that are currently being processed by the
    ThreadPool. These jobs can not be found in the #pending_jobs() list.
    """

    jobs = []
    with synchronized(self.__queue):
      for worker in self.__threads:
        with synchronized(worker):
          if worker.current:
            jobs.append(worker.current)
    return jobs

  def clear(self):
    """
    Removes all pending Jobs from the queue and return them in a list. This
    method does **no**t call #Job.cancel() on any of the jobs. If you want
    that, use #cancel_all() or call it manually.
    """

    with synchronized(self.__queue):
      jobs = self.__queue.snapshot()
      self.__queue.clear()
    return jobs

  def cancel_all(self, cancel_current=True):
    """
    Similar to #clear(), but this function also calls #Job.cancel() on all
    jobs. Also, it **includes** all jobs that are currently being executed if
    *cancel_current* is True.

    # Arguments
    cancel_current (bool): Also cancel currently running jobs and include them
      in the returned list of jobs.

    # Returns
    list: A list of the #Job#s that were canceled.
    """

    with synchronized(self.__queue):
      jobs = self.clear()
      if cancel_current:
        jobs.extend(self.current_jobs())

    [j.cancel() for j in jobs]
    return jobs

  def submit(self, target=None, task=None, args=(), kwargs=None, front=False,
             dispose_inputs=None):
    """
    Submit a new #Job to the ThreadPool.

    # Arguments
    task (function, Job): Either a function that accepts a #Job, *args* and
      *kwargs* or a #Job object that is in #~Job.PENDING state.
    target (function): A function object that accepts *args* and *kwargs*.
      Only if *task* is not specified.
    args (list, tuple): A list of arguments to be passed to *job*, if it is
      a function.
    kwargs (dict): A dictionary to be passed as keyword arguments to *job*,
      if it is a function.
    front (bool): If #True, the job will be inserted in the front of the queue.

    # Returns
    Job: The job that was added to the queue.

    # Raises
    TypeError: If a #Job object was passed but *args* or *kwargs* are non-empty.
    RuntimeError: If the ThreadPool is not running (ie. if it was shut down).
    """

    if not self.__running:
      raise RuntimeError("ThreadPool ain't running")
    if dispose_inputs is None:
      dispose_inputs = self.dispose_inputs

    if isinstance(task, Job):
      if args or kwargs:
        raise TypeError('can not provide additional arguments for Job')
      if task.state != Job.PENDING:
        raise RuntimeError('job is not pending')
      job = task
    elif task is not None:
      if kwargs is None:
        kwargs = {}
      job = Job(task=task, args=args, kwargs=kwargs, dispose_inputs=dispose_inputs)
    elif target is not None:
      if kwargs is None:
        kwargs = {}
      job = Job(target=target, args=args, kwargs=kwargs, dispose_inputs=dispose_inputs)
    else:
      raise TypeError('expected Job or callable')

    job.print_exc = self.print_exc
    if front:
      self.__queue.appendleft(job)
    else:
      self.__queue.append(job)
    return job

  def wait(self, timeout=None):
    """
    Block until all jobs in the ThreadPool are finished. Beware that this can
    make the program run into a deadlock if another thread adds new jobs to the
    pool!

    # Raises
    Timeout: If the timeout is exceeded.
    """

    if not self.__running:
      raise RuntimeError("ThreadPool ain't running")
    self.__queue.wait(timeout)

  def shutdown(self, wait=True):
    """
    Shut down the ThreadPool.

    # Arguments
    wait (bool): If #True, wait until all worker threads end. Note that pending
      jobs are still executed. If you want to cancel any pending jobs, use the
      #clear() or #cancel_all() methods.
    """

    if self.__running:
      # Add a Non-entry for every worker thread we have.
      for thread in self.__threads:
        assert thread.isAlive()
        self.__queue.append(None)
      self.__running = False

    if wait:
      self.__queue.wait()
      for thread in self.__threads:
        thread.join()

  def submit_multiple(self, functions, target=False, task=False):
    """
    Submits a #Job for each element in *function* and returns a #JobCollection.
    """

    if target or not task:
      return JobCollection([self.submit(target=func) for func in functions])
    else:
      return JobCollection([self.submit(task=func) for func in functions])


class JobCollection(object):
  """
  A list of #Job objects. Provides useful functions for querying results.
  """

  def __init__(self, jobs):
    self.jobs = jobs

  def __iter__(self):
    return iter(self.jobs)

  def wait(self):
    return [j.wait() for j in self]

  def as_completed(self):
    return as_completed(self)



# EventQueue API
# ============================================================================

class EventQueue(object):
  '''
  This class represents a collection of events that can then be
  fired one or all at a time from a specific thread. This is especially
  useful for threaded GUI applications.

  Every event has an event type which is just a name that identifies
  the kind of the event. There are two kinds of event types: Ones that
  can be queued multiple times and that may carry arbitrary event data
  and ones that can only be queued once, with no data attached.

  In non-strict mode, every event that has not been formerly declared
  is queable multiple times (or: not mergeable). If a mergeable event
  is already queued and another of that type is being queued, that new
  event is just dropped.
  '''

  EventType = collections.namedtuple('EventType', 'name mergeable')
  Event = collections.namedtuple('Event', 'type data timestamp')

  def __init__(self, strict=True, lock=None):
    super(EventQueue, self).__init__()
    self.strict = strict
    self.event_types = {}
    self.events = collections.deque()
    self.lock = lock or threading.Lock()

  def __repr__(self):
    with self.lock:
      return '<EventQueue with {0} queued events>'.format(len(self.events))

  def new_event_type(self, name, mergeable=False):
    ''' Declare a new event. May overwrite an existing entry. '''

    self.event_types[name] = self.EventType(name, mergeable)

  def add_event(self, name, data=None):
    '''
    Add an event of type *name* to the queue. May raise a
    `ValueError` if the event type is mergeable and *data* is not None
    or if *name* is not a declared event type (in strict mode).
    '''

    try:
      mergeable = self.event_types[name].mergeable
    except KeyError:
      if self.strict:
        raise ValueError('unknown event type {0!r}'.format(name))
      mergeable = False

    if mergeable and data is not None:
      raise ValueError('mergable event can not have data attached')

    with self.lock:
      if mergeable:
        # Check if such an event already exists.
        for ev in self.events:
          if ev.type == name:
            return

      self.events.append(self.Event(name, data, time.clock()))

  def pop_event(self):
    '''
    Pop the next queued event from the queue.

    :raise ValueError: If there is no event queued.
    '''

    with self.lock:
      if not self.events:
        raise ValueError('no events queued')
      return self.events.popleft()

  def pop_events(self):
    '''
    Pop all events and return a `collections.deque` object. The
    returned container can be empty. This method is preferred over
    `pop_event()` as it is much faster as the lock has to be acquired
    only once and also avoids running into an infinite loop during
    event processing.
    '''

    with self.lock:
      events = self.events
      self.events = collections.deque()
      return events


# SynchronizedDeque API
# ============================================================================

class SynchronizedDeque(Synchronizable):
  """
  Thread-safe wrapper for the `collections.deque`. Behaves similar to a
  #queue.Queue object. If used as a data- or task-queue, #task_done() must
  be called after an item has been processed!
  """

  Timeout = Timeout

  class Empty(Exception):
    " Raised when the #SynchronizedDeque is empty. "

  def __init__(self, iterable=()):
    super(SynchronizedDeque, self).__init__()
    self._deque = collections.deque(iterable)
    self._tasks = len(self._deque)

  def __iter__(self):
    raise RuntimeError('SynchronizedDeque does not support iteration')

  @synchronized
  def snapshot(self):
    return list(self._deque)

  @synchronized
  def __bool__(self):
    return bool(self._deque)

  @synchronized
  def __len__(self):
    return len(self._deque)

  @synchronized
  def clear(self):
    """
    Clears the queue. Note that calling #wait*( immediately after clear can
    still block when tasks are currently being processed since this method can
    only clear queued items.
    """

    self._tasks -= len(self._deque)
    self._deque.clear()
    notify_all(self)

  @synchronized
  def append(self, x):
    try:
      return self._deque.append(x)
    finally:
      self._tasks += 1
      notify_all(self)

  @synchronized
  def appendleft(self, x):
    try:
      return self._deque.appendleft(x)
    finally:
      self._tasks += 1
      notify_all(self)

  @synchronized
  def extend(self, iterable):
    count = len(self._deque)
    try:
      return self._deque.extend(iterable)
    finally:
      self._tasks += len(self._deque) - count
      notify_all(self)

  @synchronized
  def extendleft(self, iterable):
    count = len(self._deque)
    try:
      return self._deque.extendleft(iterable)
    finally:
      self._tasks += len(self._deque) - count
      notify_all(self)

  @synchronized
  def pop(self):
    try:
      return self._deque.pop()
    finally:
      notify_all(self)

  @synchronized
  def popleft(self):
    try:
      return self._deque.popleft()
    finally:
      notify_all(self)

  @synchronized
  def rotate(self, n):
    return self._deque.rotate(n)

  @synchronized
  def task_done(self):
    if self._tasks == 0:
      raise RuntimeError('task_done() called too often')
    assert self._tasks > 0
    self._tasks -= 1
    notify_all(self)

  @synchronized
  def get(self, block=True, timeout=None, method='pop'):
    """
    If *block* is True, this method blocks until an element can be removed from
    the deque with the specified *method*. If *block* is False, the function
    will raise #Empty if no elements are available.

    # Arguments
    block (bool): #True to block and wait until an element becomes available,
      #False otherwise.
    timeout (number, None): The timeout in seconds to use when waiting for
      an element (only with `block=True`).
    method (str): The name of the method to use to remove an element from the
      queue. Must be either `'pop'` or `'popleft'`.

    # Raises
    ValueError: If *method* has an invalid value.
    Timeout: If the *timeout* is exceeded.
    """

    if method not in ('pop', 'popleft'):
      raise ValueError('method must be "pop" or "popleft": {0!r}'.format(method))

    t_start = time.clock()
    while not self:
      if not block:
        raise self.Empty

      if timeout is None:
        wait(self)
      else:
        t_delta = time.clock() - t_start
        if t_delta > timeout:
          raise Timeout
        wait(self, timeout - t_delta)

    return getattr(self, method)()

  @synchronized
  def wait(self, timeout=None):
    """
    Waits until all tasks completed or *timeout* seconds passed.

    # Raises
    Timeout: If the *timeout* is exceeded.
    """

    t_start = time.clock()
    if not wait_for_condition(self, lambda s: s._tasks == 0, timeout):
      raise Timeout


# Utils
# ============================================================================

class Clock(object):
  """
  This class is a utility to partition a main loop into chunks at a fixed
  framerate. This is useful for Game/UI main loops.

  # Parameters
  seconds (number): The number of seconds to wait for each pass. Can be omitted
    if *fps* is specified instead.
  fps (number): The frame rate for the clock. Can be omitted if *seconds*
    is specified instead.
  """

  def __init__(self, seconds=None, fps=None):
    if seconds is not None:
      seconds = float(seconds)
    elif fps is not None:
      seconds = 1.0 / float(fps)
    else:
      raise ValueError('seconds or fps must be specified')
    self.seconds = seconds
    self.last = -1

  def sleep(self):
    """
    Sleeps until the interval has passed since the last time this function was
    called. This is a synonym for #__call__(). The first time the function is
    called will return immediately and not block. Therefore, it is important to
    put the call at the beginning of the timed block, like this:

    # Example
    ```python
    clock = Clock(fps=50)
    while True:
      clock.sleep()
      # Processing ...
    ```
    """

    current = time.time()
    if self.last < 0:
      self.last = current
      return

    delta = current - self.last
    if delta < self.seconds:
      time.sleep(self.seconds - delta)
      self.last = time.time()

  __call__ = sleep


def split_list_by(lst, key):
  """
  Splits a list by the callable *key* where a negative result will cause the
  item to be put in the first list and a positive into the second list.
  """

  first, second = [], []
  for item in lst:
    if key(item):
      second.append(item)
    else:
      first.append(item)
  return (first, second)


def reraise(tpe, value, tb=None):
  " Reraise an exception from an exception info tuple. "

  Py3 = (sys.version_info[0] == 3)
  if value is None:
    value = tpe()
  if Py3:
    if value.__traceback__ is not tb:
      raise value.with_traceback(tb)
    raise value
  else:
      exec('raise tpe, value, tb')
