# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
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

from datetime import datetime, timezone, timedelta
from collections import namedtuple
from . import git

import errno
import os
import time
import sys

BRANCH = 'worklog'
now = datetime.now
time_fmt = '%d/%b/%Y:%H:%M:%S %z'
CheckinData = namedtuple('CheckinData', 'name time')
CheckoutData = namedtuple('CheckoutData', 'name begin end interval message')
Log = namedtuple('Log', 'begin end message')


def makedirs(path):
  if not os.path.isdir(path):
    os.makedirs(path)


def now():
  tz = timezone(timedelta(hours=-time.timezone/3600))
  return datetime.now().replace(tzinfo=tz)


def strftime(time, fmt=None):
  return time.strftime(fmt or time_fmt)


def strptime(value, fmt=None):
  return datetime.strptime(value, fmt or time_fmt)


def splittimedelta(tdelta, components='DHMS'):
  l = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
  r = []
  rem = int(tdelta.total_seconds())
  for k in components:
    d, rem = divmod(rem, l[k])
    r.append(d)
  return r


def strftimedelta(tdelta, components='DHMS'):
  parts = []
  for i, val in enumerate(splittimedelta(tdelta, components)):
    if val > 0:
      parts.append('{}{}'.format(val, components[i].lower()))
  return ', '.join(parts)


def parse_time(value, dt=None):
  """
  Parses a time string in multiple possible variants and otherwise applies
  the defaults from *dt*. If *dt* is not specified, the result of #now() is
  used.
  """

  # Intentionally leaving out microseconds.
  fields = ['year', 'month', 'day', 'hour', 'minute', 'second', 'tzinfo']
  formats = [
    (time_fmt, []),
    ('%H:%M', ['hour', 'minute']),
    ('%H:%M:%S', ['hour', 'minute', 'second']),
    ('%H-%M', ['hour', 'minute']),
    ('%H-%M-%S', ['hour', 'minute', 'second']),
    ('%d/%H:%M', ['day', 'hour', 'minute']),
    ('%d/%H:%M:%S', ['day', 'hour', 'minute', 'second']),
    ('%d', ['day', '#0daytime']),
    ('%d/%b', ['day', 'month', '#0daytime']),
    ('%m/%d/%H:%M', ['month', 'day', 'hour', 'minute']),
    ('%m/%d/%H:%M:%S', ['month', 'day', 'hour', 'minute', 'second']),
  ]
  for fmt, filled_fields in formats:
    try:
      result = datetime.strptime(value, fmt)
      break
    except ValueError:
      pass
  else:
    raise ValueError('invalid time string: {!r}'.format(value))

  # Update the values that haven't been parsed.
  if dt is None:
    dt = now()

  kwargs = {k: getattr(dt, k) for k in fields if k not in filled_fields}
  if '#0daytime' in filled_fields:
    kwargs['hour'] = 0
    kwargs['minute'] = 0
    kwargs['second'] = 0

  return result.replace(**kwargs)


def parse_sheet(data):
  """
  Parses a timetable sheet and returns a list of #Log entries.
  """

  result = []
  for line in data.split('\n'):
    cols = line.split('\t', 3)
    cols[0] = strptime(cols[0])
    cols[1] = strptime(cols[1])
    result.append(Log(*cols))
  return result


class NoCheckinAvailable(Exception):
  pass


def get_checkin_file(fatal=True):
  return os.path.join(git.dir(fatal=fatal), 'worklog', 'checkin')


def get_commit_repo_and_branch():
  # Check if we should check-in to a different repository.
  target_repo = git.config('worklog.repository')
  if target_repo:
    if not os.path.isdir(target_repo):
      print('fatal: worklog.repository={}'.format(target_repo), file=sys.stderr)
      print('       the specified directory does not exist.')
      sys.exit(128)
    target_branch = git.config('worklog.project')
    if not target_branch:
      print('fatal: worklog.repository is set but worklog.project is not', file=sys.stderr)
      print('       please do `git config worklog.project <projectname>` first', file=sys.stderr)
      sys.exit(128)
  else:
    target_branch = git.config('worklog.branch') or BRANCH
  return target_repo or None, target_branch


def set_checkin(name, time=None):
  time = time or now()
  filename = get_checkin_file()
  makedirs(os.path.dirname(filename))
  with open(filename, 'w') as fp:
    fp.write('{}\n{}\n'.format(name, strftime(time)))
  return CheckinData(name, time)


def get_checkin():
  filename = get_checkin_file()
  if not os.path.isfile(filename):
    raise NoCheckinAvailable(filename)
  with open(filename) as fp:
    name = fp.readline().rstrip()
    time = fp.readline().rstrip()
    time = strptime(time)
    if not name or fp.read().strip():
      raise ValueError('invalid check-in file at {!r}'.format(filename))
  return CheckinData(name, time)


def rem_checkin():
  filename = get_checkin_file()
  try:
    os.remove(filename)
  except OSError as exc:
    if exc.errno != errno.ENOENT:
      raise


def add_checkout(name, begin, end, message=None):
  interval = end - begin
  if not message:
    message = 'Checkout ' + str(interval)

  repo, branch = get_commit_repo_and_branch()

  # Read the contents of the timetable file for this user.
  filename = name + '.tsv'
  try:
    contents = git.show('{}:{}'.format(branch, filename), cwd=repo)
  except git.DoesNotExist:
    contents = ''

  # Add an entry to the file.
  if not contents.endswith('\n'):
    contents += '\n'
  contents += '{}\t{}\t{}\n'.format(strftime(begin), strftime(end), message or '')

  # Create a commit to add the line to the timetable.
  commit = git.Commit()
  commit.head(branch, message)
  commit.add_file_contents(contents, filename)

  git.fast_import(commit.getvalue(), date_format='raw', quiet=True, cwd=repo)
  return CheckoutData(name, begin, end, interval, message)
