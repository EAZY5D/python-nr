# nr.version-upgrade

A command-line tool that allows you to automatically update the version
numbers in your project.

#### Usage

```
usage: nr version-upgrade [-h] [--dry] [--no-commit] version

  A command-line tool that allows you to automatically update the version
  numbers in your project. The configuration must be called either
  ".versionupgrade" or ".config/versionupgrade". Example config:

    tag v{VERSION}
    branch v{VERSION}
    message Prepare {VERSION} release
    upgrade setup.py:  version = '{VERSION}'
    upgrade __init__.py:__version__ = '{VERSION}'
    sub docs/changelog/v{VERSION}.md:# v{VERSION} (unreleased):# v{VERSION} ({DATE})

positional arguments:
  version

optional arguments:
  -h, --help   show this help message and exit
  --dry        Do not modify files.
  --no-commit  Do not create a new Git commit.
```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
