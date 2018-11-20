
import io
import setuptools

def readme():
  with io.open('README.md', encoding='utf8') as fp:
    return fp.read()

def requirements():
  with io.open('requirements.txt') as fp:
    return fp.readlines()

setuptools.setup(
  name = 'nr.interface',
  version = '1.0.4',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Something like zope.interface, just simpler and a few extras.',
  long_description = readme(),
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein-Python/nr.interface',
  license = 'MIT',
  namespace_packages = ['nr'],
  install_requires = requirements(),
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'}
)
