# nr.date

This package provides a fast parser for fixed format date strings with 
support for timezone offsets. The goal of this package is to

1. bring support for timezone offsets to Python 2.7
2. be faster than `dateutil.parser.parse()`

You can control the regex backend with the `PYTHON_NR_DATE_REGEX_BACKEND`
environment variable. The default is `re`. You can use this variable to 
make it use the `regex` module instead.

Currently supported format options are:

- `%Y` &ndash; 4 digit year
- `%m` &ndash; 2 digit month
- `%d` &ndash; 2 digit day
- `%H` &ndash; 2 digit hour
- `%M` &ndash; 2 digit minute
- `%S` &ndash; 2 digit second
- `%f` &ndash; arbitrary precision milliseconds
- `%z` &ndash; timezone offset (`[+-]\d\d:?\d\d` offset or `Z` for UTC)

The date formats are extensible by using the `register_format_option()`
function or creating a new `FormatOptionSet`.

## API

### `BaseFormatOption()`

Base class for format options.

### `FormatOption(char, dest, regex, parser, render)`

Useful class for creating a new format options.

### `TimezoneFormatOption()`

Special format option implementation for matching timezone offset.

### `FormatOptionSet()`

Represents a set of `BaseFormatOption` objects. Use the `create_date_format()`
method to create a `DateFormat` object from this set and a format string.

### `DateFormat(string, option_set=None)`

Creates a new parser and formatter for dates from a template string. It is
recommendable to use `FormatOptionSet.create_date_format()` instead to make
use of caching.

### `DateFormatSet(name, formats)`

A collection of `DateFormat` objects that can be parsed successively until a
first match is found. The `format()` method will use the first format in the
set.

### `root_option_set`

A global `FormatOptionSet`.

### `register_format_option()`

Add a new format option to the `root_option_set`. This is the same as calling
`root_option_set.add()`.

### `parse_date(string, fmt)`

Parses the date *string* using the specified *fmt* into a `datetime.datetime`
object.

### `format_date(date, fmt)`

Formats the *date* using the specified *fmt* into a string.

### `create_format_set(name, formats)`

Creates a new `DateFormatSet` with the specified *formats*.

### `ISO_8601`

### `JAVA_OFFSET_DATETIME`

## Benchmarks

TODO

## Future

* Vendor `dateutil.tz` module?
