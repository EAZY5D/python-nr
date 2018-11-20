
import setuptools

setuptools.setup(
  name = 'nr.futures',
  version = '1.0.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'A convenient threading based future implementation compatible with Python 2 and 3.',
  url = 'https://github.com/NiklasRosenstein-Python/nr.futures',
  license = 'MIT',
  install_requires = ['six>=1.11.0'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
