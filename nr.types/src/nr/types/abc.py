
"""
Proxy for `collections.abc` or `collections` depending on which is available.
Proxies only a subset of the members though. Six does not provide a "moves"
module for `collections.abc`.
"""

__all__ = ['Mapping', 'MutableMapping', 'Set', 'MutableSet', 'Sequence', 'MutableSequence']

try:
  import collections.abc as _abc
except ImportError:
  import collections as _abc


for _key in __all__:
  globals()[_key] = getattr(_abc, _key)

del _abc, _key
