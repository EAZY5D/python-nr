
import io
import setuptools

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

setuptools.setup(
  name = 'nr.powerline',
  version = '1.0.0.dev0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Simple powerline module.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/python-nr/tree/master/nr.powerline',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  namespace_packages = ['nr'],
  install_requires = [
    'nr.parse>=1.0.1',
    'nr.types>=1.1.1',
    'six',
    'termcolor',
  ],
  entry_points = {
    'nr.powerline.plugins': [
      'c = nr.powerline.plugins.characters:CharactersPlugin',
      'git = nr.powerline.plugins.git:GitPlugin',
      'session = nr.powerline.plugins.session:SessionPlugin',
      'time = nr.powerline.plugins.time:TimePlugin',
    ],
    'nr.cli.commands': [
      'powerline = nr.powerline.main:main'
    ]
  }
)
