
import setuptools
import io

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.markdown',
  version = '1.0.3',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = 'Enhances the Misaka/Hoedown markdown parser.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.markdown',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  install_requires = ['bs4', 'Misaka', 'pygments']
)
