
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

with io.open('requirements.txt', encoding='utf8') as fp:
  requirements = fp.readlines()

setuptools.setup(
  name = 'nr.fs',
  version = '1.1.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Filesystem and path manipulation tools.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.fs',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = requirements
)
