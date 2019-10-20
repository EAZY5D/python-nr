# Copyright (C) 2016  Niklas Rosenstein
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
"""
Tundras is a simple Python library that does object-oriented data validation
and entity encapsulation. In its current state, its main focus is on
tabular data.

# Example

You can try this with the `airports.dat` CSV file from
[openflights.com](http://openflights.org/data.html).

```python
from __future__ import print_function
from tundras import Field, TableEntity, csv
from tundras.pycompat import text_type

class Airport(TableEntity):
  id = Field(int)
  name = Field(text_type)
  city = Field(text_type)
  country = Field(text_type)
  iata_ffa = Field(text_type)
  icao = Field(text_type)
  latitude = Field(float)
  longitude = Field(float)
  altitude = Field(float)
  timezone = Field(float)
  dst = Field(text_type)
  tz_olson = Field(text_type)

with open('airports.dat', 'rb') as fp:
  for row in csv.reader(fp, encoding='latin1'):
    airport = Airport(*row)
    print(airport.id)
```

# Requirements

Tundras is a vanilla Python library without any additional dependencies.
It is developed with CPython 2.7 and 3.4 and will most likely run fine
with other versions as well.
"""

from .field import Field
from .table import TableEntity
from .exceptions import ValidationError, EntityInitializationError
