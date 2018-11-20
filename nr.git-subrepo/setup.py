
import setuptools
import io

with io.open('README.md') as fp:
  readme = fp.read()

with io.open('requirements.txt') as fp:
  requirements = fp.readlines()

setuptools.setup(
  name = 'nr.git-subrepo',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Create working trees of other Git repositories and track them in your parent repository.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.git-subrepo.git',
  license = 'MIT',
  namespace_packages = ['nr'],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  install_requires = requirements
)
