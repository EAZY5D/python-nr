
import subprocess
import os

# TODO @NiklasRosenstein resolve inter dependencies

dirname = os.path.dirname(__file__)

args = ['pip', 'install']
for name in os.listdir(dirname):
  path = os.path.join(dirname, name)
  if name.startswith('nr.') and os.path.isfile(os.path.join(path, 'setup.py')):
    args.append('-e')
    args.append(path)

exit(subprocess.call(args))
