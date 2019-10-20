# Copyright (c) 2014-2016  Niklas Rosenstein
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

__all__   = ['Cli', 'Response']
__version__ = '0.1.3'
__author__  = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'

import os
import sys
import time
import threading
import subprocess

if sys.version_info[0] < 3:
  text_type = unicode
  try: from cStringIO import StringIO as BytesIO
  except ImportError: from StringIO import StringIO as BytesIO
else:
  text_type = str
  from io import BytesIO


class Cli(object):
  ''' This class represents an interface for command-line
  applications. It manages invokation, timeouts and extracting
  the contents of the standard output.

  :param prog:
    The programs name that can be found via the ``PATH``
    environment variable or an absolute path to the program.
  :param args:
    A sequence of strings representing additional command-line
    arguments for the program which will be passed on each request.
  :param timeout:
    The number of seconds allowed for a request to be executed or
    None if no timeout should be set. A :class:`TimeoutError` will
    be raised if a process exceeds the timeout.
  :param shell:
    True if shell evaluation is desired, False if not.
  :param merge_err:
    True if stdout should be merged with stderr, False if not.
  '''

  def __init__(self, prog, args=(), timeout=None,
         shell=False, merge_err=False):
    super(Cli, self).__init__()
    self.prog = prog
    self.args = list(args)
    self.timeout = timeout
    self.interval = 0.05
    self.shell = shell
    self.merge_err = merge_err

  def request(self, *args, **kwargs):
    ''' Invoke the program with the arguments that are saved
    in the :class:`Cli` object and the additional supplied
    *\*args*.

    :param cwd: see :class:`subprocess.Popen`
    :param env: see :class:`subprocess.Popen`
    :param bufsize: see :class:`subprocess.Popen`
    :return: :class:`Response` '''

    # Extract keyword aguments for the process creation.
    cwd = kwargs.pop('cwd', None)
    env = kwargs.pop('env', None)
    bufsize = kwargs.pop('bufsize', -1)
    for key in kwargs:
      raise TypeError('unexpected keyword argument {0}'.format(key))

    # Determine if the standard output should recieve its
    # own pipe or be merged into the standard output.
    stderr = subprocess.STDOUT if self.merge_err else subprocess.PIPE

    # On Windows, we need to explicitly tell the subprocess
    # module that no console windows should be opened.
    startupinfo = None
    creationflags = 0
    if hasattr(subprocess, 'STARTUPINFO'):
      creationflags = subprocess.SW_HIDE
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    args = [self.prog] + self.args + list(args)
    process = subprocess.Popen(args, shell=self.shell,
      stdout=subprocess.PIPE, stderr=stderr,
      stdin=subprocess.PIPE, cwd=cwd, env=env,
      bufsize=bufsize, startupinfo=startupinfo,
      creationflags=creationflags)

    return self.make_response(process)

  def make_response(self, process):
    ''' This method is called after the process was spawned to
    create a response object. By default, this method will wait
    for the process to terminate and read its contents. If a
    timeout is set and the process exceeds it, a *TimeoutError*
    is raised. '''

    timeout = self.timeout
    tstart = time.time()
    if timeout is not None and timeout > 0:
      interval = self.interval
      while process.poll() is None:
        if time.time() - tstart > timeout:
          process.terminate()
          raise TimeoutError(self.timeout)
        time.sleep(interval)

    return Response(process)


class Response(object):
  ''' This class represents a spawned process. '''

  def __init__(self, process):
    super(Response, self).__init__()
    self.process = process
    self.stdout, self.stderr = process.communicate()
    self.returncode = process.returncode

  def __repr__(self):
    return '<nr.utils.cli.Response: [{0}]>'.format(self.returncode)


class TimeoutError(Exception):
  ''' Raised when the process timeout is exceeded. '''
