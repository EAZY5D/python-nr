
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.config',
  version = '1.0.2',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Model-orientated configuration extractor.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr',
  license = 'MIT',
  install_requires = ['nr.stream>=1.0.3', 'nr.types>=1.1.0'],
  packages = setuptools.find_packages('src', exclude=['test', 'docs']),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
)
