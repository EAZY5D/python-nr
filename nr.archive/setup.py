
import io
import setuptools

with io.open('README.md') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.archive',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Archive abstraction with implementations for ZIP and TAR files.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/lib/python/nr.archive',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
