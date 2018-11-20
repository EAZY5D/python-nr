
import setuptools
import io

with io.open('README.md') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.git-subrepo',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Create working trees of other Git repositories and track them in your parent repository.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.git-subrepo',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  install_requires = ['nr.cli>=1.0.2'],
  entry_points = {
    'nr.cli:commands': [
      'git-subrepo = nr.git_subrepo:main'
    ]
  }
)
