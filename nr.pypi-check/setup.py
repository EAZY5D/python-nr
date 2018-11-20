
import setuptools
import io

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.pypi-check',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Check your Python package before submitting it to PyPI.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.pypi-check',
  license = 'MIT',
  install_requires = ['nr.cli>=1.0.2'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  entry_points = {
    'nr.cli.commands': [
      'pypi-check = nr.pypi_check:main'
    ]
  }
)
