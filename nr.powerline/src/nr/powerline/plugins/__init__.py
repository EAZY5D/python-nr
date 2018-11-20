
class Plugin(object):
  pass


def cached_property(func):
  cache_name = '_cached_' + func.__name__
  def cacher(self):
    try:
      return getattr(self, cache_name)
    except AttributeError:
      value = func(self)
      setattr(self, cache_name, value)
      return value
  return property(cacher)
