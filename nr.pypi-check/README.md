# nr.pypi-check

Allows you to check and validate your package configuration so you can spot
errors before you publish on [PyPI].

  [PyPI]: https://pypi.org

### Usage

```
usage: nr pypi-check [-h] [OPTIONS ...]

  Checks can be turned off with the respective -wno-{option} flag.

options:
  -wchangelog                 Warn if there is no changelog file or changelog section in the readme. (default on)
  -wchangelog-release-date    Warn if there is no release date in the changelog for the current version. (default on)
  -wlicense                   Warn if your project has no license file.
  -wmanifest                  Warn if your project should have a MANIFEST.in file or if it misses some files. (default on)
  -wpackage-meta              Warn if your package or module is missing meta information. (default on)
  -wsetup                     Warn if there is no setup script (default on).
  -wsetup-fields              Warn if important fields are missing in your setup script. (default on)
  -wsetup-setuptools          Warn if your setup script does not use setuptools, but distutils for example. (default on)
  -wversion-match             Warn if your package or module's __version__ is different from the versioin in your setup script. (default on)
```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
