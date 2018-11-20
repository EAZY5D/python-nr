# nr.git-worklog

Git-worklog is a minimal, multi-user & Git-based timetracking command-line
tool. All logs are stored as one file per per user in the `worklog` branch
of your project.

#### Features

* Easy to use command-line interface
* Simple data-format allows you to easily parse and process work logs
* Comes with a plain-text reporting tool with filter options
* Configurable branch name or even target Git repository

#### Configuration

`worklog.branch` &ndash; The name of the branch that the work logs will be
saved to. The default value for this option is `worklog`.

`worklog.repository` &ndash; The path to a repository that the work logs
will be commited to. The `worklog.project` option is used as the branch-name
for this repository instead of `worklog.branch`.

`worklog.project` &ndash; The name of the branch that the work logs will be
commited to when an alternative repository is configured.

#### Worklog Format

Work logs are stored per-user in a `.tsv` file. The user's name is derived
from the Git `user.name` option. Work log files always have three columns:

1. Checkin time
2. Checkout time
3. Log message

> Note that the Log message *may* contain additional tabs, so you should stop
> splitting a row into parts after the first two columns. 

Times are always stored in the format `%d/%b/%Y:%H:%M:%S %z`. In order to
read the full work log of a user, you can use the `git-worklog show` command,
or the functional equivalent using `git show`:

    $ git show worklog:"$(git config user.name).tsv"

#### Installation

    $ pip install git+https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.git-worklog
    $ git config --global alias.worklog '!nr git-worklog'

### CLI Documentation

#### `git worklog abort`

Aborts the current session. A session can be started with `git worklog checkin`.

#### `git worklog checkin`

Starts a new session. The `--user` option can be used to start a session as
another user. With the `--time` option, you can specify a start time for the
session that is not the current time.

See also: **Time Formats**

#### `git worklog checkout`

Ends the current session and commits a work log. An alternative checkout time
can be specified with the `--time` option. A message for the log can be
defined with the `-m` option. If not message is defined, a default message
will be generated that says "Checkout &lt;interval&gt;".

See also: **Time Formats**

#### `git worklog checkpoint`

A combination of `git worklog checkout` and `git worklog checkin`. The options
are the same as for the `git worklog checkout` command.

#### `git worklog status`

Displays the current session's user and checkin time, as well as the time
passed since checkin.

#### `git worklog show`

Shows the full work log for the current user or the user specified with the
`--user` option. Besides the the default value for the `worklog.branch`
option and the option to override the user, this is equivalent to the Git
command

    $ git show "$(git config worklog.branch):$(git config user.name).tsv"

#### `git worklog report`

Generate a report from a user's work log. This command gives you the option
to filter by a log's checkin and checkout time using the `--begin` and `--end`
options. With the `--strict` flag, these filters can be narrowed to exclude
logs that overlap with the specified checkin or checkout time.

By default, a plain-text and human readable summary of the work logs will
be printed to the console. If the `--raw` flag is specified, the output format
will match that of `git worklog show` (but it will allow you to apply the
filters supported by this command).

### Time Formats

Typing the full-fletched time format that is used by git-worklog when
specifying a time value to one of the commands is usually undesirable, thus
the CLI supports various other time formats and will fill missing information
with the current day and time information where appropriate.

See also: `git_worklog/timetable.py:parse_time()`

__Supported Time Formats__

* `%H:%M`
* `%H:%M:%S`
* `%H-%M`
* `%H-%M-%S`
* `%d/%H:%M`
* `%d/%H:%M:%S`
* `%d` <sup>(1)</sup>
* `%d/%b` <sup>(1)</sup>
* `%m/%d/%H:%M`
* `%m/%d/%H:%M:%S`

<sup>(1)</sup> When using this time format, the daytime information will be
zeroed. Eg. `25/Nov` specifies the 25th of November in the current year at
0am.
