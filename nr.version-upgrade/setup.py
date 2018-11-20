
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  readme = fp.read()

setuptools.setup(
  name = 'nr.version-upgrade',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'A command-line tool that allows you to automatically update the version numbers in your project.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.version-upgrade',
  license = 'MIT',
  install_requires = [
    'nr.cli>=1.0.2',
    'nr.semver>=1.0.0,<2.0.0'
  ],
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  entry_points = {
    'nr.cli:commands': [
      'version-upgrade = nr.version_upgrade:main'
    ]
  }
)
