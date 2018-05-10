
import setuptools

setuptools.setup(
  name = 'nr',
  version = '3.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'The nr namespace package',
  long_description = '''
    This is the `nr` Python namespace package. It is empty.
  ''',
  url = 'https://github.com/NiklasRosenstein-Python/nr',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
