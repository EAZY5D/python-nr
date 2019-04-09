
try:
  import collections.abc as _abc
except ImportError:
  import collections as _abc

import sys
sys.modules[__name__] = _abc
