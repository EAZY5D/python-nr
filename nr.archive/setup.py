
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.archive',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Archive abstraction layer for ZIP and TAR files.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.archive',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  entry_points = {
    'nr.cli.commands': [
      'archive = nr.archive:main'
    ]
  }
)
