
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.semver',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Semver version and version-specifier types.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://gitlab.niklasrosenstein.com/NiklasRosenstein/lib/python/nr.semver',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
