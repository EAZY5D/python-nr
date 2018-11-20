
import setuptools

setuptools.setup(
  name = 'nr.ast',
  version = '1.1.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Stuff related to the Python AST and code evaluation.',
  url = 'https://github.com/NiklasRosenstein-Python/nr.ast',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = ['six']
)
