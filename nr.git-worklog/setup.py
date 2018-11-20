
import setuptools
import io

with io.open('README.md') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.git-worklog',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Track working hours inside your Git repository.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.git-worklog',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  install_requires = ['nr.cli>=1.0.2'],
  entry_points = {
    'nr.cli:commands': [
      'git-worklog = nr.git_worklog.main:main'
    ]
  }
)
