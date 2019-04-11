
from dateutil.parser import parse as dateutil_parse
from nr.core.date import JAVA_OFFSET_DATETIME

DATES_TO_TEST = [
    '2019-03-12T10:22-0400',
    # TODO @nrosenstein This date format currently fails to be parsed by
    #                   our custom date parser.
    #'2019-03-12T10:22-04:00',
    '2019-03-12T10:22:00Z',
    '2019-03-12T10:22:00.4312Z'
]


def test_parse_date():
  for s in DATES_TO_TEST:
    assert dateutil_parse(s) == JAVA_OFFSET_DATETIME.parse(s)
