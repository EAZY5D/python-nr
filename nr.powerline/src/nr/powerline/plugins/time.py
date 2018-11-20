
import datetime

from nr.powerline.plugins import Plugin, cached_property


class TimePlugin(Plugin):

  @cached_property
  def now(self):
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
