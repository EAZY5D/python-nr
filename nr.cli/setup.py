
import setuptools
import io

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.cli',
  version = '1.0.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'The "nr" command-line tool handler.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.cli',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  entry_points = {
    'console_scripts': [
      'nr = nr.cli.__main__:_entry_point'
    ]
  }
)
