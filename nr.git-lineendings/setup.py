
import setuptools
import io

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.git-lineendings',
  version = '1.0.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Find issues with line-endings in your repository.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.git-lineendings',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  install_requires = ['nr.cli>=1.0.2'],
  entry_points = {
    'nr.cli.commands': [
      'git-lineendings = nr.git_lineendings.main:main'
    ]
  }
)
