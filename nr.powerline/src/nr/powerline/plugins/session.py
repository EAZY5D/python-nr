
import os
import platform

from nr.powerline.plugins import Plugin, cached_property


class SessionPlugin(Plugin):

  @cached_property
  def hostname(self):
    return platform.node()

  @cached_property
  def cwd(self):
    user_home = os.path.expanduser('~')
    cwd = os.getcwd()
    try:
      relpath = os.path.relpath(cwd, user_home)
      if relpath.startswith(os.pardir):
        raise ValueError
      return '~/' + relpath
    except ValueError:
      return cwd
    assert False
