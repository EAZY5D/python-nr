
import setuptools
import io

with io.open('README.md') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.admin',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Cross-platform privilege elevation (including CLI).',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/lib/python/nr.admin',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  entry_points = {
    'console_scripts': {
      'nr-admin = nr.admin:_entry_point'
    }
  }
)
