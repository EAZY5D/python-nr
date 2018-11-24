
import os
import subprocess

from nr.powerline.plugins import Plugin, cached_property


def get_output(command, default=''):
  try:
    data = subprocess.check_output(
      command,
      shell=True,
      stderr=open(os.devnull, 'w'))
    return data.decode().strip()
  except subprocess.CalledProcessError:
    return default


class GitPlugin(Plugin):

  @cached_property
  def user(self):
    return get_output('git config user.email')

  @cached_property
  def project(self):
    return os.path.basename(get_output('git rev-parse --show-toplevel'))

  @cached_property
  def branch(self):
    branches = [x.strip() for x in get_output('git branch').split(' ')]
    index = branches.index('*')
    return branches[index+1]
