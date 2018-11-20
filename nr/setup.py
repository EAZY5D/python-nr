
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr',
  version = '3.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'The nr namespace package.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
