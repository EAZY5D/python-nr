
import setuptools
import io

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.stream',
  version = '1.0.2',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Streaming iterators made easy in Python.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.stream',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
