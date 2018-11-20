# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function
from . import git, timetable

import argparse
import datetime
import io
import os
import sys


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog, description="""
    Allows you to track working times in a separate `worklog` branch.
  """)
  subparsers = parser.add_subparsers(dest='command')

  abort_parser = subparsers.add_parser('abort', description="""
    Abort the current session.
  """)

  checkin_parser = subparsers.add_parser('checkin', description="""
    Checks you in to start a local time-tracking session.
  """)
  checkin_parser.add_argument('--time', type=timetable.parse_time, help='Override check-in time.')

  checkpoint_parser = subparsers.add_parser('checkpoint', description="""
    Commit a new log from the current session and start a new one.
  """)
  checkpoint_parser.add_argument('-m', '--message', help='A message for the log.')
  checkpoint_parser.add_argument('--time', type=timetable.parse_time,
    help='Override check-out and new check-in time.')

  checkout_parser = subparsers.add_parser('checkout', description="""
    Checks you out an adds an entry to your timetable file in the worklog
    branch.
  """)
  checkout_parser.add_argument('-m', '--message', help='A message for the log.')
  checkout_parser.add_argument('--time', type=timetable.parse_time,
    help='Override check-out time.')

  report_parser = subparsers.add_parser('report', description="""
    Creates a easily readable worklog report. The filter options are similar
    to the `show` command. Currently supported output formats are: {raw,plain}
  """)
  report_parser.add_argument('--user', help='User to create the report for.')
  report_parser.add_argument('--begin', type=timetable.parse_time,
    help='Include only logs after this time.')
  report_parser.add_argument('--end', type=timetable.parse_time,
    help='Include only logs before this time.')
  report_parser.add_argument('--strict', action='store_true',
    help='Exclude logs that did not strictly start, or end respectively, '
      'at the time(s) specified with --begin and --end.')
  report_parser.add_argument('--raw', action='store_true',
    help='Raw output format (like git worklog show).')


  show_parser = subparsers.add_parser('show', description="""
    Prints your timetable (or that of the specified user). The timetable is a
    TSV file with the three columns CHECKINTIME, CHECKOUTTIME and MESSAGE.
    All times have timezone information attached.
  """)
  show_parser.add_argument('--user', help='User to retrieve the timetable for.')

  status_parser = subparsers.add_parser('status', description="""
    Displays your current session, that is the time passed since checkin or
    otherwise that there is no active time-tracking session.
  """)
  status_parser.add_argument('-d', '--detail', action='store_true')

  return parser


def print_err(*message):
  print(*message, file=sys.stderr)


def abort():
  try:
    data = timetable.get_checkin()
  except timetable.NoCheckinAvailable:
    print_err('fatal: not checked-in')
    return 1

  timetable.rem_checkin()
  print('Aborted session for', data.name)
  print('Checked in at', timetable.strftime(data.time))


def checkin(time):
  try:
    data = timetable.get_checkin()
  except timetable.NoCheckinAvailable:
    pass
  else:
    print_err('fatal: already checked in: {} at {}'.format(data.name, timetable.strftime(data.time)))
    print_err('       did you forget to check out, last time? ')
    print_err('       use the --time argument on checkout.')
    return 1

  user_name = git.config('user.name')
  if not user_name:
    print_err('fatal: user.name not configured.')
    return 1

  data = timetable.set_checkin(user_name, time)
  print('checked in: {} at {}'.format(data.name, timetable.strftime(data.time)))


def checkout(message, time):
  try:
    checkin = timetable.get_checkin()
  except timetable.NoCheckinAvailable:
    print_err('fatal: not checked-in')
    return 1

  time = time or timetable.now()
  if time <= checkin.time:
    print_err('fatal: check-out time can not be at a point in time before check-in.')
    return 1

  data = timetable.add_checkout(checkin.name, checkin.time, time, message)
  timetable.rem_checkin()
  print('checked out: {}, interval is {}'.format(checkin.name, str(data.interval)))


def report(args):
  repo, branch = timetable.get_commit_repo_and_branch()
  user = args.user or git.config('user.name')
  try:
    data = git.show('{}:{}.tsv'.format(branch, user), cwd=repo)
  except git.DoesNotExist as exc:
    print_err(exc)
    return 1

  data = timetable.parse_sheet(data)
  if args.begin:
    if args.strict:
      data = [x for x in data if x.end >= args.begin]
    else:
      data = [x for x in data if x.begin >= args.begin]
  if args.end:
    if args.strict:
      data = [x for x in data if x.begin <= args.end]
    else:
      data = [x for x in data if x.begin <= args.end]

  if args.raw:
    for row in data:
      print('{}\t{}\t{}'.format(timetable.strftime(row.begin),
        timetable.strftime(row.end), row.message))
    return 0
  else:
    strftime = lambda x: x.strftime('%a %b %d %H:%M:%S %Y %z')
    tdelta_sum = datetime.timedelta()
    print('Worklog for', user)
    print('From:', strftime(args.begin)) if args.begin else 0
    print('To:  ', strftime(args.end))if args.end else 0
    print()
    for row in data:
      tdelta = row.end - row.begin
      tdelta_sum += tdelta
      print('  * {} ({})'.format(strftime(row.begin), timetable.strftimedelta(tdelta)))
      print('    {}'.format(row.message))
      print()
    print('Total:', timetable.strftimedelta(tdelta_sum))


def show(user):
  repo, branch = timetable.get_commit_repo_and_branch()
  user = user or git.config('user.name')
  try:
    print(git.show('{}:{}.tsv'.format(branch, user), cwd=repo))
  except git.DoesNotExist as exc:
    print_err(exc)
    return 1


def status(detail):
  if detail:
    repo, branch = timetable.get_commit_repo_and_branch()
    if repo:
      print('Worklog repository:', repo)
      print('Worklog branch:    ', branch)
    elif branch != timetable.BRANCH:
      print('Worklog branch:    ', branch)
  try:
    data = timetable.get_checkin()
  except timetable.NoCheckinAvailable:
    print('not checked-in.')
  else:
    info = timetable.strftimedelta(timetable.now() - data.time, 'HMS')
    print('{} checked in at {} (since {})'.format(data.name,
        timetable.strftime(data.time), info))


def main(argv=None, prog=None):
  """
  Track working hours inside your Git repository.
  """

  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)
  if not args.command:
    parser.print_usage()
    return 0
  elif args.command == 'abort':
    return abort()
  elif args.command == 'checkin':
    return checkin(args.time)
  elif args.command == 'checkpoint':
    res = checkout(args.message, args.time)
    if res not in (0, None): return res
    return checkin(args.time)
  elif args.command == 'checkout':
    return checkout(args.message, args.time)
  elif args.command == 'report':
    return report(args)
  elif args.command == 'show':
    return show(args.user)
  elif args.command == 'status':
    return status(args.detail)
  else:
    print('fatal: invalid command {}'.format(args.command), file=sys.stderr)
    return 128


if __name__ == '__main__':
  sys.exit(main())
